"""준비 화면. 세이브를 고르면 로딩 화면을 거쳐 여기로 온다 (save_data.current).

- 옆에서 본 수채화 들판이 층마다 다른 빠르기로 흘러가고 (먼 언덕은 느리게, 땅은 빠르게),
  검은 잉크통을 안은 소년이 왼쪽에서 달려 들어와 오른쪽을 향해 계속 달린다 (3프레임 달리기)
- 왼쪽 위: 지금 가진 잉크 (검정·빨강·초록·파랑), 가운데 위: 세이브 번호·진행 단계
- 아래 버튼: 유닛 추가하기 / 잉크 섞기 / 내 유닛 / 출발하기! — 아직 만들지 않은 기능은 '곧 만들어요' 쪽지
- 타이틀로 / ESC: 저장하고 타이틀로. 나갈 때(창 닫기 포함) 저장한다
"""
from pico2d import (clear_canvas, update_canvas, get_events, hide_cursor,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT, SDLK_ESCAPE)

import game_framework
import save_data
import text
import title_mode
from assets import image
from title_effects import InkSplash
from ui_button import Button

W, H = 1280, 720
GROUND = 160            # 땅 윗선 (pico y). tools/gen_prepare.py 의 GROUND_Y(PIL 560) 와 같은 자리
BOY_X = 400             # 소년이 달려와 멈추는(제자리 달리기) x
BOY_SCALE = 0.75
BOY_FEET = 144 - 80     # 스프라이트 가운데에서 발바닥까지 (gen_prepare.FEET, 스프라이트 높이 160)
ENTER_TIME = 1.6        # 왼쪽 밖에서 BOY_X 까지 달려 들어오는 시간
RUN_FPS = 10
RUN_CYCLE = (0, 1, 2, 1)
# 층마다 흘러가는 빠르기 (px/초). 멀수록 느리다
SPEED = {'far': 14, 'mid': 60, 'ground': 170}
FADE_IN = 0.6
TOAST_TIME = 1.8
INK = (86, 68, 106)
INK_COLORS = ('black', 'red', 'green', 'blue')
IMAGES = ['sky', 'far', 'mid', 'ground', 'boy_0', 'boy_1', 'boy_2', 'shadow', 'hud', 'toast'] + \
    [f'ink_{c}' for c in INK_COLORS]

layers = {}
boys = []
buttons = []
splashes = []
fade = shadow = hud = toast_img = None
ink_icons = {}
t = 0.0
scroll = 0.0
toast = None    # (글씨, 남은 시간)


def preload():
    """로딩 화면이 머무는 동안 미리 읽어 둔다 (assets 가 한 번 읽은 이미지는 다시 읽지 않는다)."""
    for name in IMAGES:
        image('prepare', name + '.png')


def soon(name):
    def show():
        global toast
        toast = (f'{name}  —  곧 만들어요!', TOAST_TIME)
    return show


def depart():
    global toast
    toast = ('아직 떠날 수 없어요  —  필드는 곧 만들어요!', TOAST_TIME)


def back_to_title():
    game_framework.change_mode(title_mode)


def init():
    global layers, boys, buttons, splashes, fade, shadow, hud, toast_img, ink_icons, t, scroll, toast
    layers = {name: image('prepare', name + '.png') for name in ('sky', 'far', 'mid', 'ground')}
    boys = [image('prepare', f'boy_{i}.png') for i in range(3)]
    shadow = image('prepare', 'shadow.png')
    hud = image('prepare', 'hud.png')
    toast_img = image('prepare', 'toast.png')
    ink_icons = {c: image('prepare', f'ink_{c}.png') for c in INK_COLORS}
    fade = image('common', 'fade.png')
    gap = 272
    x0 = W / 2 - gap * 1.5
    buttons = [Button(x0 + gap * i, 62, f'button_{name}.png', f'button_{name}_hover.png', action, 0.4 * i, 'prepare')
               for i, (name, action) in enumerate((('add_unit', soon('유닛 추가하기')), ('mix', soon('잉크 섞기')),
                                                   ('units', soon('내 유닛')), ('depart', depart)))]
    buttons.append(Button(W - 112, H - 52, 'button_back.png', 'button_back_hover.png', back_to_title, 1.3, 'prepare'))
    splashes = []
    t = scroll = 0.0
    toast = None
    hide_cursor()
    title_mode.move_mouse(title_mode.mouse)


def finish():
    save_data.save_current()


def pause():
    for b in buttons:
        b.hovered = False


def resume():
    pass


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            back_to_title()
            return
        elif event.type == SDL_MOUSEMOTION:
            title_mode.move_mouse(title_mode.to_canvas(event))
            for b in buttons:
                b.mouse_move(*title_mode.mouse)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            mx, my = title_mode.to_canvas(event)
            if t > FADE_IN and any(b.click(mx, my) for b in buttons):
                return
            splashes.append(InkSplash(mx, my))


def update():
    global t, scroll, toast, splashes
    dt = game_framework.frame_time
    t += dt
    scroll += dt
    for b in buttons:
        b.update()
    for s in splashes:
        s.update()
    splashes = [s for s in splashes if not s.done][-12:]
    title_mode.trail.update()
    if toast:
        toast = (toast[0], toast[1] - dt) if toast[1] > dt else None


def boy_x():
    k = min(1.0, t / ENTER_TIME)
    k = 1 - (1 - k) ** 2   # 달려 들어오다가 제자리 달리기로 자연스럽게
    return -120 + (BOY_X + 120) * k


def draw_layer(name, y):
    """가로로 이어지는 층을 두 장 붙여 그린다 (왼쪽으로 흘러간다 = 소년은 오른쪽으로 달린다)."""
    img = layers[name]
    off = (scroll * SPEED[name]) % img.w
    for i in range(2):
        img.draw(img.w / 2 - off + img.w * i, y)


def draw_boy():
    frame = RUN_CYCLE[int(t * RUN_FPS) % len(RUN_CYCLE)]
    x = boy_x()
    shadow.draw(x + 2, GROUND - 2, shadow.w * 0.55, shadow.h * 0.6)
    img = boys[frame]
    img.draw(x, GROUND - 4 + BOY_FEET * BOY_SCALE, img.w * BOY_SCALE, img.h * BOY_SCALE)


def draw_hud():
    hud.draw(250, 646)
    ink = save_data.current['ink'] if save_data.current else {c: 0 for c in INK_COLORS}
    for i, c in enumerate(INK_COLORS):
        x = 72 + i * 106
        ink_icons[c].draw(x, 648, 42, 48)
        text.draw(str(ink.get(c, 0)), x + 26, 646, 30, INK)
    if save_data.current:
        cur = save_data.current
        text.draw(f'세이브 {cur["slot"]}  ·  {save_data.stage_name(cur["stage"])}', W / 2, 676, 34, INK, 'c')


def draw_toast():
    if not toast:
        return
    msg, left = toast
    a = min(1.0, left / 0.4, (TOAST_TIME - left) / 0.15)
    toast_img.opacify(a)
    toast_img.draw(W / 2, 470)
    toast_img.opacify(1)
    text.draw(msg, W / 2, 472, 30, INK, 'c', alpha=a)


def draw():
    clear_canvas()
    layers['sky'].draw(W / 2, H / 2)
    draw_layer('far', H / 2)
    draw_layer('mid', H / 2)
    draw_layer('ground', layers['ground'].h / 2)
    draw_boy()
    for b in buttons:
        b.draw()
    draw_hud()
    for s in splashes:
        s.draw()
    draw_toast()
    if t < FADE_IN:
        fade.opacify(1 - t / FADE_IN)
        fade.draw(W / 2, H / 2, W, H)
        fade.opacify(1)
    title_mode.draw_cursor()
    update_canvas()
