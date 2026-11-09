"""세이브 파일 선택 화면. 타이틀에서 '시작하기'를 누르면 타이틀 위에 겹쳐 뜬다 (push_mode / pop_mode).

- 슬롯 카드 3장: 빈 슬롯을 누르면 새 게임, 저장된 슬롯을 누르면 이어하기 → 준비 화면
- 저장된 슬롯의 '지우기' → '정말 지울까요?' 를 한 번 더 누르면 지운다 (다른 곳을 누르면 취소)
- 1·2·3 키로도 고를 수 있다. 닫기 / ESC: 타이틀로
"""
from pico2d import (clear_canvas, update_canvas, get_events,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE, SDLK_1, SDLK_2, SDLK_3)

import game_framework
import save_data
import text
import title_mode
from assets import image
from ui_button import Button

CX, CY = 640, 360
SLOT_Y = (480, 365, 250)  # 슬롯 1·2·3 카드 높이 (tools/gen_save_select.py 의 창 배치와 맞춘다)
CLOSE_Y = 130
DELETE_RIGHT = 948         # 지우기 버튼 오른쪽 끝 x (카드 안쪽)
TEXT_X = 340               # 슬롯 글씨 왼쪽 x
OPEN_TIME = 0.25
INK = (86, 68, 106)
SOFT = (130, 112, 150)

panel = dim = None
cards = []
delete_buttons = []
close_button = None
summaries = []
confirm = None   # 지우기 확인 중인 슬롯 (없으면 None)
t = 0.0


def refresh():
    """슬롯 요약을 다시 읽는다 (새로 만들거나 지운 뒤)."""
    global summaries
    summaries = [save_data.summary(slot) for slot in range(1, save_data.SLOTS + 1)]


def choose(slot):
    """빈 슬롯이면 새 게임, 있으면 이어하기. 그다음 준비 화면으로."""
    if save_data.exists(slot):
        save_data.continue_game(slot)
    else:
        save_data.new_game(slot)
    game_framework.pop_mode()     # 이 창을 닫고
    title_mode.enter_game()       # 타이틀 → 준비 화면


def ask_delete(slot):
    global confirm
    if confirm == slot:
        save_data.delete(slot)
        confirm = None
        refresh()
    else:
        confirm = slot


def close():
    game_framework.pop_mode()


def _delete_button(slot, kind):
    w = 210 if kind == 'confirm' else 150
    name = 'button_delete_confirm' if kind == 'confirm' else 'button_delete'
    return Button(DELETE_RIGHT - w / 2, SLOT_Y[slot - 1], f'{name}.png', f'{name}_hover.png',
                  lambda: ask_delete(slot), 0.3 * slot, 'save')


def init():
    global panel, dim, cards, delete_buttons, close_button, confirm, t
    panel = image('save', 'panel.png')
    dim = image('settings', 'dim.png')
    cards = [Button(CX, y, f'slot_{i + 1}.png', f'slot_{i + 1}_hover.png', lambda s=i + 1: choose(s), 0.5 * i, 'save')
             for i, y in enumerate(SLOT_Y)]
    for c in cards:
        c.t = 0.0  # 카드는 흔들리지 않게 (아래 draw 에서 bob 없이 그린다)
    delete_buttons = [{'normal': _delete_button(s, 'normal'), 'confirm': _delete_button(s, 'confirm')}
                      for s in range(1, save_data.SLOTS + 1)]
    close_button = Button(CX, CLOSE_Y, 'button_close.png', 'button_close_hover.png', close, 1.0, 'save')
    confirm = None
    t = 0.0
    refresh()
    move(*title_mode.mouse)


def finish():
    pass


def pause():
    pass


def resume():
    pass


def visible_delete(slot):
    """그 슬롯에 지금 보이는 지우기 버튼 (빈 슬롯이면 None)."""
    if summaries[slot - 1] is None:
        return None
    return delete_buttons[slot - 1]['confirm' if confirm == slot else 'normal']


def move(mx, my):
    title_mode.move_mouse((mx, my))
    over_delete = False
    for slot in range(1, save_data.SLOTS + 1):
        for b in delete_buttons[slot - 1].values():
            b.hovered = False
        d = visible_delete(slot)
        if d:
            d.mouse_move(mx, my)
            over_delete = over_delete or d.hovered
    for c in cards:
        c.mouse_move(mx, my)
        c.hovered = c.hovered and not over_delete
    close_button.mouse_move(mx, my)


def click(mx, my):
    global confirm
    for slot in range(1, save_data.SLOTS + 1):
        d = visible_delete(slot)
        if d and d.click(mx, my):
            return
    was_confirming = confirm
    confirm = None  # 지우기 확인은 다른 곳을 누르면 취소
    if close_button.click(mx, my):
        return
    if was_confirming is not None:
        return      # 확인을 취소하는 클릭은 카드를 고르지 않는다
    for c in cards:
        if c.click(mx, my):
            return


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                close()
                return
            if event.key in (SDLK_1, SDLK_2, SDLK_3):
                choose(event.key - SDLK_1 + 1)
                return
        elif event.type == SDL_MOUSEMOTION:
            move(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            click(*title_mode.to_canvas(event))
            return


def update():
    global t
    t += game_framework.frame_time
    title_mode.update_ambient()
    for b in cards + [close_button] + [b for d in delete_buttons for b in d.values()]:
        b.update()


def draw_card(slot, card):
    """카드 + 그 위 글씨. 카드는 흔들림 없이, 올리면 살짝 커진다."""
    img = card.hover_image if card.hovered else card.normal
    s = card.scale
    img.draw(card.x, card.y, img.w * s, img.h * s)
    y = card.y
    info = summaries[slot - 1]
    text.draw(f'{slot}', TEXT_X - 20, y + 2, 44, INK, 'r')
    if info is None:
        text.draw('비어 있음', TEXT_X + 6, y + 14, 34, INK)
        text.draw('눌러서 새 여정을 시작해요', TEXT_X + 6, y - 22, 24, SOFT)
        return
    text.draw(save_data.stage_name(info['stage']), TEXT_X + 6, y + 14, 34, INK)
    detail = (f'플레이 {save_data.format_play_time(info["play_time"])}  ·  '
              f'잉크 {info["ink_total"]}  ·  {save_data.format_saved_at(info["saved_at"])}')
    text.draw(detail, TEXT_X + 6, y - 22, 22, SOFT)
    visible_delete(slot).draw()


def draw():
    clear_canvas()
    title_mode.draw_scene()
    k = min(1.0, t / OPEN_TIME)
    k = 1 - (1 - k) ** 3
    dim.opacify(0.45 * k)
    dim.draw(CX, CY, 1280, 720)
    dim.opacify(1)
    s = 0.92 + 0.08 * k
    panel.opacify(k)
    panel.draw(CX, CY, panel.w * s, panel.h * s)
    panel.opacify(1)
    if k >= 1:
        for slot, card in enumerate(cards, 1):
            draw_card(slot, card)
        close_button.draw()
    title_mode.draw_cursor()
    update_canvas()
