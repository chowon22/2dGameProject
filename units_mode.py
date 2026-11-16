"""내 유닛 화면. 준비 화면의 '내 유닛' 을 누르면 그 위에 뜬다 (push_mode).

- 내 유닛 (위): 데리고 갈 유닛 6자리. 누르면 빠진다
- 잉크: 색마다 '고른 유닛에 드는 잉크 / 가진 잉크'
- 내 프리셋 (아래): 그려서 저장한 유닛 전부. 누르면 내 유닛에 들어간다.
  가진 잉크 안에서만 고를 수 있고, 지금 더 고를 수 없는 카드는 흐리게 보인다.
  같은 프리셋을 여러 번 고를 수 있다. 많으면 마우스 휠로 넘긴다
- 다 빼기 / 닫기, ESC 닫기
"""
from pico2d import (clear_canvas, update_canvas, get_events,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT, SDLK_ESCAPE)
from sdl2 import SDL_MOUSEWHEEL

import game_framework
import painter
import prepare_mode
import save_data
import text
import title_mode
import unit_cards
from assets import image
from ui_button import Button

W, H = 1280, 720
INK = prepare_mode.INK
SOFT = (150, 128, 170)
TOAST_TIME = 1.8
FADE_IN = 0.18
NAMES = {'black': '검정', 'red': '빨강', 'green': '초록', 'blue': '파랑'}

PARTY_Y, INK_Y, LIST_Y = 640, 540, 462
ROW_X = 220
GAP = 124
COLS = 7
GRID_Y = (384, 276, 168)         # 프리셋 줄마다 y

panel = fade = toast_img = None
ink_icons = {}
buttons = []
row0 = 0                         # 휠로 넘긴 줄 수
toast = None
t = 0.0


def slot_x(i):
    return ROW_X + 56 + GAP * i


def data():
    return save_data.current


def presets():
    return data()['units'] if data() else []


def visible():
    """지금 보이는 프리셋: [(유닛, x, y)]."""
    units = presets()[row0 * COLS:(row0 + len(GRID_Y)) * COLS]
    return [(u, slot_x(i % COLS), GRID_Y[i // COLS]) for i, u in enumerate(units)]


def max_row0():
    rows = (len(presets()) + COLS - 1) // COLS
    return max(0, rows - len(GRID_Y))


def say(msg):
    global toast
    toast = (msg, TOAST_TIME)


# ---------------------------------------------------------------- 행동
def pick(unit):
    if save_data.add_to_party(data(), unit['id']):
        return
    if len(save_data.party_units(data())) >= save_data.PARTY_MAX:
        say(f'내 유닛은 {save_data.PARTY_MAX}자리까지예요')
    else:
        say('잉크가 모자라요')


def unequip_all():
    if data():
        data()['party'].clear()


def close():
    game_framework.pop_mode()


# ---------------------------------------------------------------- 모드
def init():
    global panel, fade, toast_img, ink_icons, buttons, row0, toast, t
    panel = image('draw', 'panel.png')
    fade = image('common', 'fade.png')
    toast_img = image('prepare', 'toast.png')
    ink_icons = {c: image('prepare', f'ink_{c}.png') for c in painter.COLORS}
    buttons = [Button(1130, PARTY_Y, 'button_unequip.png', 'button_unequip_hover.png', unequip_all, 0.0, 'draw'),
               Button(1150, 70, 'button_close.png', 'button_close_hover.png', close, 0.4, 'draw')]
    if data():   # 지워진 프리셋이 남아 있으면 정리
        data()['party'] = [u['id'] for u in save_data.party_units(data())]
    row0 = 0
    toast = None
    t = 0.0
    title_mode.move_mouse(title_mode.mouse)


def finish():
    save_data.save_current()


def pause():
    pass


def resume():
    pass


def click(mx, my):
    if any(b.click(mx, my) for b in buttons) or not data():
        return
    for i in range(len(save_data.party_units(data()))):
        if unit_cards.hit(slot_x(i), PARTY_Y, mx, my):
            save_data.remove_from_party(data(), i)
            return
    for unit, x, y in visible():
        if unit_cards.hit(x, y, mx, my):
            pick(unit)
            return


def handle_events():
    global row0
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            close()
            return
        elif event.type == SDL_MOUSEMOTION:
            pos = title_mode.to_canvas(event)
            title_mode.move_mouse(pos)
            for b in buttons:
                b.mouse_move(*pos)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            if t > FADE_IN:
                click(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEWHEEL:
            row0 = min(max(0, row0 - event.wheel.y), max_row0())


def update():
    global t, toast
    dt = game_framework.frame_time
    t += dt
    for b in buttons:
        b.update()
    title_mode.trail.update()
    if toast:
        toast = (toast[0], toast[1] - dt) if toast[1] > dt else None


# ---------------------------------------------------------------- 그리기
def draw_party():
    text.draw('내 유닛', 46, PARTY_Y, 30, INK)
    party = save_data.party_units(data()) if data() else []
    for i in range(save_data.PARTY_MAX):
        if i < len(party):
            unit_cards.draw(party[i], slot_x(i), PARTY_Y, on=True)
        else:
            unit_cards.draw_empty(slot_x(i), PARTY_Y)


def draw_ink():
    text.draw('잉크', 46, INK_Y, 30, INK)
    if not data():
        return
    used = save_data.party_cost(data())
    have = data()['ink']
    for i, c in enumerate(painter.COLORS):
        x = ROW_X + 30 + 180 * i
        icon = ink_icons[c]
        if have.get(c, 0) <= 0:
            icon.opacify(0.35)
        icon.draw(x, INK_Y, 42, 48)
        icon.opacify(1)
        text.draw(f'{used.get(c, 0)} / {have.get(c, 0)}', x + 28, INK_Y - 2, 28, INK)
    text.draw('드는 잉크 / 가진 잉크', ROW_X + 30 + 180 * 4, INK_Y, 22, SOFT)


def draw_presets():
    text.draw('내 프리셋', 46, LIST_Y, 30, INK)
    if not presets():
        text.draw('아직 그린 유닛이 없어요.  유닛 추가하기에서 그려 보세요!', ROW_X, LIST_Y, 24, SOFT)
        return
    hint = '누르면 내 유닛에 들어가요  ·  내 유닛을 누르면 빠져요'
    if max_row0():
        hint += f'  ·  휠로 더 보기 ({row0 + 1}/{max_row0() + 1})'
    text.draw(hint, ROW_X, LIST_Y, 22, SOFT)
    picked = set(data()['party'])
    for unit, x, y in visible():
        ok = save_data.can_add(data(), unit)
        unit_cards.draw(unit, x, y, on=unit['id'] in picked, alpha=1.0 if ok else 0.38)
        n = data()['party'].count(unit['id'])
        if n > 1:
            text.draw(f'×{n}', x + 36, y + 30, 18, INK)


def draw_toast():
    if not toast:
        return
    msg, left = toast
    a = min(1.0, left / 0.4, (TOAST_TIME - left) / 0.15)
    toast_img.opacify(a)
    toast_img.draw(W / 2, 300)
    toast_img.opacify(1)
    text.draw(msg, W / 2, 302, 28, INK, 'c', alpha=a)


def draw():
    clear_canvas()
    prepare_mode.draw_scene()
    panel.draw(W / 2, H / 2, W - 16, H - 12)
    draw_party()
    draw_ink()
    draw_presets()
    for b in buttons:
        b.draw()
    draw_toast()
    if t < FADE_IN:
        fade.opacify(0.5 * (1 - t / FADE_IN))
        fade.draw(W / 2, H / 2, W, H)
        fade.opacify(1)
    title_mode.draw_cursor()
    update_canvas()
