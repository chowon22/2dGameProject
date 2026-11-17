"""월드 고르기 화면. 준비 화면의 '출발하기!' 를 누르면 그 위에 뜬다 (push_mode).

- 월드 카드 0 ~ 7 (열린 월드만 누를 수 있다. 처음엔 0 흑백 숲만)
- 월드를 누르면 그 월드의 스테이지 w-1 ~ w-7 이 길을 따라 뜬다 (깬 스테이지는 별, 다음 스테이지만 열림, 마지막은 보스)
- 스테이지를 누르면 내 유닛 화면이 '출전 준비' 로 뜬다: 적 자리·예상 전투력을 보고 유닛을 놓은 뒤 시작
- 뒤로 / ESC: 스테이지 → 월드 → 준비 화면
- 누르는 곳마다 물감이 톡 튄다 (준비 화면처럼). 출발하기! 를 누르고 들어오면 그 자리에서 바로 튄다
"""
import math

from pico2d import (clear_canvas, update_canvas, get_events, SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION,
                    SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT, SDLK_ESCAPE)

import game_framework
import prepare_mode
import save_data
import stages
import text
import title_mode
from assets import image
from title_effects import InkSplash
from ui_button import Button

W, H = 1280, 720
INK = prepare_mode.INK
SOFT = (150, 128, 170)
FADE_IN = 0.18
CARD_W, CARD_H = 230, 150
CARD_XS = (250, 510, 770, 1030)
CARD_YS = (470, 290)
PATH_Y = 340                    # 스테이지 길 가운데 높이
NODE_XS = [190 + i * 150 for i in range(stages.STAGES_PER_WORLD)]
TOAST_TIME = 1.6

panel = fade = toast_img = None
buttons = []
world = None                    # 고른 월드 (None 이면 월드 카드 화면)
hover = None                    # 마우스가 올라간 카드 번호 / 스테이지 id
toast = None
t = 0.0


def data():
    return save_data.current


def node_y(i):
    return PATH_Y + 46 * math.sin(i * 1.2)   # 꼬불꼬불한 길


def card_pos(wid):
    return CARD_XS[wid % 4], CARD_YS[wid // 4]


def say(msg):
    global toast
    toast = (msg, TOAST_TIME)


# ---------------------------------------------------------------- 행동
def back():
    global world
    if world is not None:
        world = None
    else:
        game_framework.pop_mode()


def open_world(wid):
    global world
    if not stages.world_unlocked(data(), wid):
        say(f'{wid - 1} 월드의 마지막 스테이지를 깨면 열려요')
        return
    world = wid


def open_stage(sid):
    import units_mode   # units_mode → world_mode 를 부르지 않지만, 화면끼리 엇갈려 부르지 않게 늦게
    if stages.stage(sid) is None:
        say('아직 준비 중인 곳이에요')
        return
    if not stages.unlocked(data(), sid):
        say('앞 스테이지를 먼저 깨야 해요')
        return
    units_mode.stage_id = sid
    game_framework.push_mode(units_mode)


# ---------------------------------------------------------------- 모드
splashes = []                   # 누른 자리에 튄 물감


def init():
    global panel, fade, toast_img, buttons, world, hover, toast, t
    panel = image('draw', 'panel.png')
    fade = image('common', 'fade.png')
    toast_img = image('prepare', 'toast.png')
    buttons = [Button(1140, 70, 'button_back.png', 'button_back_hover.png', back, 0.2, 'world')]
    world = hover = toast = None
    t = 0.0
    splashes[:] = [InkSplash(*title_mode.mouse)]   # 출발하기! 를 누른 자리에서 물감이 튄다
    title_mode.move_mouse(title_mode.mouse)


def finish():
    save_data.save_current()


def pause():
    for b in buttons:
        b.hovered = False


def resume():
    title_mode.move_mouse(title_mode.mouse)


def thing_at(mx, my):
    """마우스 아래 월드 번호(카드 화면) 또는 스테이지 id(스테이지 화면)."""
    if world is None:
        for w in stages.worlds():
            x, y = card_pos(w['id'])
            if abs(mx - x) <= CARD_W / 2 - 10 and abs(my - y) <= CARD_H / 2 - 10:
                return w['id']
        return None
    for i, sid in enumerate(stages.stage_ids(world)):
        if math.hypot(mx - NODE_XS[i], my - node_y(i)) <= 44:
            return sid
    return None


def handle_events():
    global hover
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            back()
            return
        elif event.type == SDL_MOUSEMOTION:
            mx, my = title_mode.to_canvas(event)
            title_mode.move_mouse((mx, my))
            for b in buttons:
                b.mouse_move(mx, my)
            hover = thing_at(mx, my)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT and t > FADE_IN:
            mx, my = title_mode.to_canvas(event)
            splashes.append(InkSplash(mx, my))
            if any(b.click(mx, my) for b in buttons):
                return
            thing = thing_at(mx, my)
            if thing is None:
                continue
            if world is None:
                open_world(thing)
            else:
                open_stage(thing)
            return


def update():
    global t, toast
    dt = game_framework.frame_time
    t += dt
    for b in buttons:
        b.update()
    for s in splashes:
        s.update()
    splashes[:] = [s for s in splashes if not s.done][-12:]
    title_mode.trail.update()
    if toast:
        toast = (toast[0], toast[1] - dt) if toast[1] > dt else None


# ---------------------------------------------------------------- 그리기
def draw_worlds():
    text.draw('어디로 떠날까요?', W / 2, 640, 40, INK, 'c')
    for w in stages.worlds():
        x, y = card_pos(w['id'])
        state = 'locked' if not stages.world_unlocked(data(), w['id']) else ('hover' if hover == w['id'] else 'off')
        img = image('world', f'world_{w["id"]}{"" if state == "off" else "_" + state}.png')
        img.draw(x, y + (3 * math.sin(t * 2 + w['id']) if state != 'locked' else 0))
    text.draw('흑백이 된 세상을 하나씩 되찾아요', W / 2, 160, 24, SOFT, 'c')


def draw_stages():
    w = stages.worlds()[world]
    text.draw(f'{w["id"]}  {w["name"]}', W / 2, 640, 40, INK, 'c')
    ids = stages.stage_ids(world)
    # 길: 이어지는 점선
    for i in range(len(ids) - 1):
        x0, y0, x1, y1 = NODE_XS[i], node_y(i), NODE_XS[i + 1], node_y(i + 1)
        for k in range(1, 8, 2):
            a, b = k / 9, (k + 1) / 9
            text.draw('·', x0 + (x1 - x0) * (a + b) / 2, y0 + (y1 - y0) * (a + b) / 2, 34, SOFT, 'c')
    for i, sid in enumerate(ids):
        st = stages.stage(sid)
        x, y = NODE_XS[i], node_y(i)
        if st is None or not stages.unlocked(data(), sid):
            kind = 'locked'
        elif st.get('boss'):
            kind = 'boss'
        elif stages.is_cleared(data(), sid):
            kind = 'clear'
        else:
            kind = 'open'
        on = hover == sid and kind != 'locked'
        image('world', f'stage_{kind}{"_hover" if on else ""}.png').draw(x, y + (4 if on else 0))
        col = (150, 144, 158) if kind == 'locked' else INK
        text.draw(sid, x, y + (4 if on else 0), 28, col, 'c')
        name = st['name'] if st else '준비 중'
        text.draw(name, x, y - 66, 20, SOFT if kind == 'locked' else INK, 'c')
    nxt = next((sid for sid in ids if stages.unlocked(data(), sid) and not stages.is_cleared(data(), sid)), None)
    msg = f'{nxt} 에서 운반자들이 색을 나르고 있어요' if nxt else '이 월드의 색을 모두 되찾았어요!'
    text.draw(msg, W / 2, 160, 24, SOFT, 'c')


def draw_toast():
    if not toast:
        return
    msg, left = toast
    a = min(1.0, left / 0.4, (TOAST_TIME - left) / 0.15)
    toast_img.opacify(a)
    toast_img.draw(W / 2, 90)
    toast_img.opacify(1)
    text.draw(msg, W / 2, 92, 26, INK, 'c', alpha=a)


def draw():
    clear_canvas()
    prepare_mode.draw_scene()
    panel.draw(W / 2, H / 2, W - 16, H - 12)
    if world is None:
        draw_worlds()
    else:
        draw_stages()
    for b in buttons:
        b.draw()
    for s in splashes:
        s.draw()
    draw_toast()
    if t < FADE_IN:
        fade.opacify(0.5 * (1 - t / FADE_IN))
        fade.draw(W / 2, H / 2, W, H)
        fade.opacify(1)
    title_mode.draw_cursor()
    update_canvas()
