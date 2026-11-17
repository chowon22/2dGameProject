"""내 유닛 화면. 준비 화면의 '내 유닛' 을 누르면 그 위에 뜬다 (push_mode).

- 필드 미리보기 (위): 흑백 들판 왼쪽에 우리 자리 6칸 (앞줄 3 + 뒷줄 3), 오른쪽은 적이 설 자리.
  놓은 유닛은 그린 그림 그대로 자리에 서 있고, 발밑에 역할 마크가 붙는다.
  · 자리를 누르면 고름(노랗게) → 프리셋을 누르면 그 자리에 놓인다 (있던 유닛은 바뀐다)
  · 자리를 고른 채 다른 자리를 누르면 두 자리를 맞바꾼다 (빈 자리면 옮기기). 같은 자리를 다시 누르면 고르기 취소
  · 자리를 안 고르고 프리셋을 누르면 앞줄부터 빈 자리에 놓인다
  · 놓인 유닛을 두 번 빠르게 누르면(더블클릭) 자리에서 뺀다
  · 끌어 놓기: 놓인 유닛을 다른 자리로 끌면 옮기기·맞바꾸기, 프리셋 카드를 자리로 끌면 그 자리에 놓기.
    자리 밖에 놓으면 그대로 돌아간다
- 잉크 (오른쪽 위): 색마다 남은 잉크. 유닛을 놓으면 그만큼 줄고 빼면 돌아온다. 남은 잉크보다 많이 드는 유닛은 못 놓는다
- 내 프리셋 (아래): 전체 / 탱커 / 근접 딜러 / 원거리 딜러 / 서포터 칸으로 나눠 본다. 지금 놓을 수 없는 카드는 흐리게.
  같은 프리셋을 여러 번 놓을 수 있다. 많으면 마우스 휠로 넘긴다. 카드에 마우스를 올리면 드는 잉크가 뜨고,
  × 를 두 번 누르면 프리셋을 지운다
- 다 빼기 / 닫기, ESC 닫기
- 전투에서 다친 유닛은 반투명한 채로 남는다 (남은 체력 % 표시, 쓰러지면 '쓰러짐').
  치료하기: 고른 다친 유닛 하나를, 전체 치료하기: 다친 유닛 모두를 가득 치료한다. 버튼 아래에 드는 잉크 (병 + 숫자).
  흐려진 만큼 다시 칠하는 셈이라 색마다 드는 잉크 = 그 유닛을 그린 그 색 잉크 x 잃은 체력 비율 (save_data.heal_cost)
- 아래 한 줄 도움말: 드래그 · 더블클릭
출전 준비 (월드 화면에서 스테이지를 누르면 stage_id 를 정하고 띄운다):
- 적 자리에 그 스테이지의 몬스터가 서 있고, 우리 전투력 vs 적 예상 전투력이 뜬다
- 시작! 을 누르면 전투(battle_mode)로
"""
import math

from pico2d import (clear_canvas, update_canvas, get_events, SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION,
                    SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDL_BUTTON_LEFT, SDLK_ESCAPE)
from sdl2 import SDL_MOUSEWHEEL

import frames
import game_framework
import painter
import prepare_mode
import save_data
import stages
import stats
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

# 필드 미리보기 (image/draw/field.png 780x240)
FIELD_X, FIELD_Y = 590, 572
FIELD_MID = FIELD_X                       # 가운데 점선: 왼쪽 우리, 오른쪽 적
LANE_Y = (572, 522, 472)                  # 줄(위 = 먼 쪽 → 아래 = 가까운 쪽)마다 발 자리 y
LANE_SKEW = (56, 0, -56)                  # 먼 줄은 오른쪽으로 (비스듬히 서서 덜 겹치게)
FRONT_X, BACK_X = 476, 316
FIGURE_SCALE = 0.2                        # 자리에 서 있는 그림 배율 (체형마다 크기가 다르게 보이도록 모두 같은 배율)
SPOT_W, SPOT_TOP = 48, 50                 # 자리 누르는 범위: 가로 ±48, 발 아래 16 ~ 위 50
HEAL_RATE = 1.0                           # 치료: 그 유닛을 그린 잉크 x 잃은 체력 비율 x 이 배율 (색마다)
HEAL_X = 112
HEAL_Y = (536, 450)                       # 치료하기 / 전체 치료하기 버튼 y
DOUBLE_CLICK = 0.4                        # 이 시간(초) 안에 같은 유닛을 두 번 누르면 자리에서 뺀다

INK_X, INK_TOP = 1010, 668
LIST_Y = 404
ROW_X = 220
GAP = 124
COLS = 6
GRID_Y = (322, 214, 106)                  # 프리셋 줄마다 y
TABS = ('all',) + frames.IDS              # 프리셋 나누기 칸
TAB_GAP = 148

stage_id = None                  # 출전 준비 중인 스테이지 (월드 화면이 정한다)
heal_buttons = []                # [치료하기(고른 유닛), 전체 치료하기]
panel = fade = toast_img = field_img = None
spot_imgs = {}
ink_icons = {}
buttons = []
row0 = 0                         # 휠로 넘긴 줄 수
tab = 'all'
deleter = None
selected = None                  # 고른 자리 (없으면 None)
last_click = None                # 더블클릭 판단: (자리, 누른 시각)
press = None                     # 누르고 있는 것: ('slot', 자리) / ('preset', 유닛), 누른 자리
dragging = False                 # 누른 채 DRAG_START 넘게 움직였으면 끌기
DRAG_START = 6
toast = None
t = 0.0


# ---------------------------------------------------------------- 자리 계산
def spot_pos(slot):
    """자리 번호 → 발 자리 (x, y). 0~2 앞줄, 3~5 뒷줄, 줄 안에서는 위(먼 쪽)부터."""
    lane = slot % 3
    x = (FRONT_X if slot < 3 else BACK_X) + LANE_SKEW[lane]
    return x, LANE_Y[lane]


def enemy_pos(slot):
    x, y = spot_pos(slot)
    return 2 * FIELD_MID - x, y


def slot_at(mx, my):
    """(mx, my) 아래 자리. 가까운 줄(앞에 그려짐)부터 본다."""
    for slot in sorted(range(save_data.PARTY_MAX), key=lambda s: -(s % 3)):
        x, y = spot_pos(slot)
        if abs(mx - x) <= SPOT_W and y - 16 <= my <= y + SPOT_TOP:
            return slot
    return None


def card_x(i):
    return ROW_X + 56 + GAP * i


def tab_x(i):
    return ROW_X + 69 + TAB_GAP * i


def data():
    return save_data.current


def presets():
    """지금 칸(전체 또는 틀 하나)의 프리셋."""
    units = data()['units'] if data() else []
    return units if tab == 'all' else [u for u in units if u.get('frame') == tab]


def visible():
    """지금 보이는 프리셋: [(유닛, x, y)]."""
    units = presets()[row0 * COLS:(row0 + len(GRID_Y)) * COLS]
    return [(u, card_x(i % COLS), GRID_Y[i // COLS]) for i, u in enumerate(units)]


def max_row0():
    rows = (len(presets()) + COLS - 1) // COLS
    return max(0, rows - len(GRID_Y))


def placeable(unit):
    """지금 이 프리셋을 놓을 수 있는가 (고른 자리가 있으면 그 자리에)."""
    if selected is not None:
        return save_data.can_place(data(), unit, selected)
    return save_data.can_add(data(), unit)


def say(msg):
    global toast
    toast = (msg, TOAST_TIME)


# ---------------------------------------------------------------- 행동
def pick(unit):
    global selected
    if selected is not None:
        if save_data.place(data(), selected, unit['id']):
            selected = None
        else:
            say('잉크가 모자라요')
        return
    if save_data.add_to_party(data(), unit['id']) is not None:
        return
    say('자리가 꽉 찼어요.  자리를 골라 바꿔 놓아요' if None not in data()['party'] else '잉크가 모자라요')


def click_slot(slot):
    global selected
    if selected is None:
        selected = slot
    elif selected == slot:
        selected = None
    else:
        save_data.swap_slots(data(), selected, slot)
        selected = None


def pick_tab(name):
    global tab, row0
    tab = name
    row0 = 0


def unequip_all():
    global selected
    if data():
        data()['party'] = [None] * save_data.PARTY_MAX
    selected = None


def close():
    game_framework.pop_mode()


def heal_targets(everyone):
    """치료할 자리들: everyone 이면 다친 유닛 모두, 아니면 고른 자리의 다친 유닛 하나 (안 골랐으면 없음)."""
    hurt = save_data.hurt_slots(data()) if data() else []
    if everyone:
        return hurt
    return [selected] if selected in hurt else []


def heal_cost(everyone):
    return save_data.heal_cost(data(), heal_targets(everyone), HEAL_RATE)


def heal(everyone):
    global selected
    slots = heal_targets(everyone)
    if not slots:
        say('다친 유닛을 골라 주세요' if save_data.hurt_slots(data()) else '다친 유닛이 없어요')
        return
    if save_data.heal(data(), slots, heal_cost(everyone)):
        say('모두 나았어요!' if everyone else '다 나았어요!')
        selected = None
    else:
        say('잉크가 모자라요')


def start_battle():
    import battle_mode   # battle_mode 가 이 모듈을 부르지 않지만, 화면 모듈은 쓸 때 부른다
    if not save_data.party_units(data()):
        say('필드에 유닛을 놓아 주세요')
        return
    if all(save_data.hp_list(data())[s] <= 0 for s, uid in enumerate(data()['party']) if uid is not None):
        say('모두 쓰러져 있어요.  치료하고 가요')
        return
    battle_mode.stage_id = stage_id
    game_framework.push_mode(battle_mode)


def our_power():
    return stats.team_power([stats.unit_stats(u) for u in save_data.party_units(data())]) if data() else 0


# ---------------------------------------------------------------- 모드
def init():
    global panel, fade, toast_img, field_img, spot_imgs, ink_icons, buttons, row0, tab, deleter
    global selected, last_click, press, dragging, toast, t, heal_buttons
    panel = image('draw', 'panel.png')
    fade = image('common', 'fade.png')
    toast_img = image('prepare', 'toast.png')
    field_img = image('draw', 'field.png')
    spot_imgs = {k: image('draw', f'spot{k}.png') for k in ('', '_on', '_enemy')}
    ink_icons = {c: image('prepare', f'ink_{c}.png') for c in painter.COLORS}
    buttons = [Button(1130, 482, 'button_unequip.png', 'button_unequip_hover.png', unequip_all, 0.0, 'draw'),
               Button(1150, 70, 'button_close.png', 'button_close_hover.png', close, 0.4, 'draw')]
    if stage_id:
        buttons.append(Button(1130, 392, 'button_start.png', 'button_start_hover.png', start_battle, 0.6, 'world'))
    heal_buttons = [Button(HEAL_X, HEAL_Y[0], 'button_heal.png', 'button_heal_hover.png', lambda: heal(False), 0.9, 'world'),
                    Button(HEAL_X, HEAL_Y[1], 'button_heal_all.png', 'button_heal_all_hover.png', lambda: heal(True),
                           1.1, 'world')]
    if data():   # 지워진 프리셋 자리는 비운다
        data()['party'] = save_data.normalize_party(data()['party'], data()['units'])
    row0 = 0
    tab = 'all'
    deleter = unit_cards.Deleter()
    selected = last_click = press = None
    dragging = False
    toast = None
    t = 0.0
    title_mode.move_mouse(title_mode.mouse)


def finish():
    global stage_id
    save_data.save_current()
    stage_id = None   # 다음에 '내 유닛' 으로 열면 그냥 내 유닛 화면


def pause():
    for b in buttons:
        b.hovered = False


def resume():
    pass


def press_down(mx, my):
    """마우스 누름: 버튼·× ·칸은 바로 처리, 놓인 유닛과 프리셋 카드는 뗄 때 (누르기·더블클릭 / 끌어 놓기) 처리."""
    global press, dragging
    dragging = False
    press = None
    if not data():
        return
    if not any(unit_cards.hit_delete(x, y, mx, my) and deleter.state(u) for u, x, y in visible()):
        slot = slot_at(mx, my)
        if slot is not None and data()['party'][slot] is not None:
            press = (('slot', slot), (mx, my))
            return
        for unit, x, y in visible():
            if unit_cards.hit(x, y, mx, my):
                press = (('preset', unit), (mx, my))
                return
    click(mx, my)


def release(mx, my):
    global press, dragging, selected, last_click
    if press is None:
        return
    (kind, what), (px, py) = press
    was_drag = dragging
    press, dragging = None, False
    if not was_drag and kind == 'slot':
        if last_click and last_click[0] == what and t - last_click[1] < DOUBLE_CLICK:   # 더블클릭: 빼기
            save_data.remove_from_party(data(), what)
            selected = last_click = None
            return
        last_click = (what, t)
        click_slot(what)
        return
    if not was_drag:   # 프리셋 그냥 누르기
        pick(what)
        return
    target = slot_at(mx, my)
    selected = None
    if target is None:
        return         # 자리 밖: 그대로
    if kind == 'slot':
        if target != what:
            save_data.swap_slots(data(), what, target)
    elif not save_data.place(data(), target, what['id']):
        say('잉크가 모자라요')


def click(mx, my):
    global row0, selected
    if any(b.click(mx, my) for b in buttons) or not data():
        return
    if save_data.hurt_slots(data()) and any(b.click(mx, my) for b in heal_buttons):
        return
    slot = slot_at(mx, my)
    if slot is not None:
        click_slot(slot)
        return
    gone = deleter.click(visible(), mx, my)
    if gone == 'asked':
        say('한 번 더 누르면 이 프리셋을 지워요')
        return
    if gone is not None:
        row0 = min(row0, max_row0())
        say('프리셋을 지웠어요')
        return
    for i, name in enumerate(TABS):
        if abs(mx - tab_x(i)) <= 62 and abs(my - LIST_Y) <= 24:
            pick_tab(name)
            return
    for unit, x, y in visible():
        if unit_cards.hit(x, y, mx, my):
            pick(unit)
            return


def mouse_move(mx, my):
    global dragging
    title_mode.move_mouse((mx, my))
    if press and not dragging and abs(mx - press[1][0]) + abs(my - press[1][1]) > DRAG_START:
        dragging = True
    deleter.move(visible(), mx, my)
    for b in buttons + heal_buttons:
        b.mouse_move(mx, my)


def handle_events():
    global row0
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            close()
            return
        elif event.type == SDL_MOUSEMOTION:
            mouse_move(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            if t > FADE_IN:
                press_down(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEBUTTONUP and event.button == SDL_BUTTON_LEFT:
            release(*title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEWHEEL:
            row0 = min(max(0, row0 - event.wheel.y), max_row0())


def update():
    global t, toast
    dt = game_framework.frame_time
    t += dt
    for b in buttons + heal_buttons:
        b.update()
    title_mode.trail.update()
    if toast:
        toast = (toast[0], toast[1] - dt) if toast[1] > dt else None


# ---------------------------------------------------------------- 그리기
def draw_field():
    if stage_id:
        text.draw('출전 준비', 46, FIELD_Y + 40, 30, INK)
        text.draw(f'{stage_id}  {stages.stage(stage_id)["name"]}', 46, FIELD_Y, 22, SOFT)
    else:
        text.draw('내 유닛', 46, FIELD_Y + 40, 30, INK)
    field_img.draw(FIELD_X, FIELD_Y)
    for s in range(save_data.PARTY_MAX):
        spot_imgs['_enemy'].draw(*enemy_pos(s))
    if stage_id:
        draw_enemies()
    if not data():
        return
    party = data()['party']
    source = press[0][1] if dragging and press[0][0] == 'slot' else None
    target = slot_at(*title_mode.mouse) if dragging else None
    # 먼 줄부터 그려야 가까운 줄이 앞에 온다
    for slot in sorted(range(save_data.PARTY_MAX), key=lambda s: s % 3):
        x, y = spot_pos(slot)
        spot_imgs['_on' if slot in (selected, target) else ''].draw(x, y)
        unit = save_data.find_unit(data(), party[slot]) if party[slot] is not None else None
        if unit:
            img = unit_cards.thumb(unit, scale=FIGURE_SCALE)
            frac = save_data.hp_list(data())[slot]
            if img:
                a = 0.3 if slot == source else stats.hurt_alpha(frac)   # 다친 유닛은 반투명 (끌고 있으면 흐리게)
                img.opacify(a)
                img.draw(x, y - 6 + img.h / 2)
                img.opacify(1)
            if frac < 1:   # 역할 마크 + 남은 체력
                unit_cards.draw_mark(unit, x - 24, y - 20, 22)
                text.draw('쓰러짐' if frac <= 0 else f'{round(frac * 100)}%', x + 12, y - 20, 18,
                          (200, 80, 90) if frac <= 0 else INK, 'c')
            else:
                unit_cards.draw_mark(unit, x, y - 20, 22)


def draw_dragged():
    """끌고 있는 유닛·프리셋을 커서에 붙여 그린다."""
    if not dragging or not data():
        return
    kind, what = press[0]
    unit = save_data.find_unit(data(), data()['party'][what]) if kind == 'slot' else what
    img = unit_cards.thumb(unit, scale=FIGURE_SCALE) if unit else None
    if img:
        mx, my = title_mode.mouse
        img.opacify(0.85)
        img.draw(mx, my - 10)
        img.opacify(1)


def draw_enemies():
    """출전 준비: 적 자리에 이 스테이지 몬스터들, 필드 아래에 전투력 비교."""
    es = stages.enemies(stage_id)
    for e in sorted(es, key=lambda e: e['slot'] % 3):   # 먼 줄부터
        x, y = enemy_pos(e['slot'])
        img = image(*e['image'])
        k = 0.42 * e['scale']
        img.draw(x, y + img.h * k / 2 - 4 + 2 * math.sin(t * 2.4 + e['slot']), img.w * k, img.h * k)
    ours, theirs = our_power(), stats.team_power(es)
    col = (70, 150, 100) if ours >= theirs else (200, 80, 90)   # 시작! 버튼 아래
    text.draw(f'우리 전투력  {ours}', 1130, 332, 24, col, 'c')
    text.draw(f'적 예상 전투력  {theirs}', 1130, 300, 24, INK, 'c')


def draw_cost(cost, cx, y):
    """드는 잉크를 병 + 숫자로 한 줄에 (가운데 cx)."""
    items = [(c, cost[c]) for c in painter.COLORS if cost.get(c)]
    widths = [22 + 10 * len(str(n)) + 10 for _, n in items]
    x = cx - (sum(widths) - 10) / 2
    for (c, n), w in zip(items, widths):
        ink_icons[c].draw(x + 8, y, 16, 19)
        text.draw(str(n), x + 19, y - 1, 18, INK)
        x += w


def draw_heal():
    """다친 유닛이 있으면 왼쪽에 치료하기(고른 유닛) / 전체 치료하기 버튼, 버튼 아래에 드는 잉크."""
    if not data() or not save_data.hurt_slots(data()):
        return
    for everyone, b, y in ((False, heal_buttons[0], HEAL_Y[0]), (True, heal_buttons[1], HEAL_Y[1])):
        cost = heal_cost(everyone)
        b.draw(1.0 if cost else 0.4)   # 고른 다친 유닛이 없으면 흐리게
        if cost:
            draw_cost(cost, HEAL_X, y - 46)


def draw_ink():
    if not data():
        return
    left = save_data.ink_left(data())
    have = data()['ink']
    text.draw('남은 잉크', INK_X, INK_TOP + 2, 22, SOFT)
    for i, c in enumerate(painter.COLORS):
        y = INK_TOP - 36 - 34 * i
        icon = ink_icons[c]
        if have.get(c, 0) <= 0:
            icon.opacify(0.35)
        icon.draw(INK_X + 14, y, 26, 30)
        icon.opacify(1)
        text.draw(str(left.get(c, 0)), INK_X + 36, y - 2, 26, INK)
        if left.get(c, 0) != have.get(c, 0):   # 놓은 유닛에 쓰인 만큼
            text.draw(f'(-{have.get(c, 0) - left.get(c, 0)})', INK_X + 104, y - 3, 20, SOFT)


def draw_presets():
    text.draw('내 프리셋', 46, LIST_Y, 30, INK)
    for i, name in enumerate(TABS):
        image('draw', f'tab_{name}{"_on" if name == tab else ""}.png').draw(tab_x(i), LIST_Y)
    if not data() or not data()['units']:
        text.draw('아직 그린 유닛이 없어요.  유닛 추가하기에서 그려 보세요!', ROW_X, GRID_Y[0], 24, SOFT)
        return
    if not presets():
        text.draw('이 칸에는 아직 그린 유닛이 없어요', ROW_X, GRID_Y[0], 24, SOFT)
    hint = '드래그: 유닛 옮기기  ·  더블클릭: 유닛 빼기'
    if max_row0():
        hint += f'  ·  휠: 더 보기 ({row0 + 1}/{max_row0() + 1})'
    text.draw(hint, 46, 30, 20, SOFT)
    party = data()['party']
    for unit, x, y in visible():
        unit_cards.draw(unit, x, y, on=unit['id'] in party, alpha=1.0 if placeable(unit) else 0.38,
                        delete=deleter.state(unit))
        n = party.count(unit['id'])
        if n > 1:
            text.draw(f'×{n}', x + 44, y - 28, 16, INK, 'c')


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
    draw_field()
    draw_heal()
    draw_ink()
    draw_presets()
    for b in buttons:
        b.draw()
    if not dragging:
        unit_cards.draw_tip(deleter.hover, visible())   # 마우스를 올린 카드: 드는 잉크
    draw_dragged()
    draw_toast()
    if t < FADE_IN:
        fade.opacify(0.5 * (1 - t / FADE_IN))
        fade.draw(W / 2, H / 2, W, H)
        fade.opacify(1)
    title_mode.draw_cursor()
    update_canvas()
