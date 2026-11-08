"""타이틀 화면.

- 파스텔 수채화 배경 위로 로고가 내려앉고, 모래시계 잉크통이 둥실 떠 있다.
- 비눗방울이 떠오르고 별이 반짝인다. 마우스는 깃펜이 되어 파스텔 붓자국을 남긴다.
- 빈 곳을 클릭하면 잉크 방울이 톡 튄다.
- 시작하기(Enter/Space) → 준비 화면, 끝내기(ESC) → 종료.
"""
import math

from pico2d import (clear_canvas, update_canvas, get_events, get_canvas_height, hide_cursor, show_cursor,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE)

import game_framework
import prepare_mode
from assets import image
from title_effects import Bubble, Twinkle, BrushTrail, InkSplash, sparkle_burst
from ui_button import Button

CX = 640
LOGO_Y = 585
SUBTITLE_Y = 472
BOTTLE_Y = 292
BUTTON_Y = 78
INTRO = 1.4  # 로고가 내려앉는 시간(초)
CURSOR_OFFSET = (26, 26)  # 깃펜 이미지 중심에서 펜촉 끝까지 거리

background = logo = logo_glow = subtitle = None
bottle = bottle_glow = bottle_shadow = cursor = None
buttons = []
bubbles = []
twinkles = []
splashes = []
trail = None
t = 0.0
mouse = (-100, -100)


def start_game():
    game_framework.change_mode(prepare_mode)


def init():
    global background, logo, logo_glow, subtitle, bottle, bottle_glow, bottle_shadow, cursor
    global buttons, bubbles, twinkles, splashes, trail, t, mouse
    background = image('title', 'background.png')
    logo = image('title', 'logo.png')
    logo_glow = image('title', 'logo_glow.png')
    subtitle = image('title', 'subtitle.png')
    bottle = image('title', 'ink_bottle.png')
    bottle_glow = image('title', 'bottle_glow.png')
    bottle_shadow = image('title', 'bottle_shadow.png')
    cursor = image('common', 'cursor_pen.png')

    buttons = [
        Button(CX - 150, BUTTON_Y, 'button_start.png', 'button_start_hover.png', start_game, 0.0),
        Button(CX + 150, BUTTON_Y, 'button_quit.png', 'button_quit_hover.png', game_framework.quit, 1.3),
    ]
    bubbles = [Bubble(start_anywhere=True) for _ in range(14)]
    twinkles = [Twinkle() for _ in range(16)]
    splashes = []
    trail = BrushTrail()
    t = 0.0
    mouse = (-100, -100)
    hide_cursor()


def finish():
    show_cursor()


def pause():
    pass


def resume():
    pass


def handle_events():
    global mouse
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                game_framework.quit()
            elif event.key in (SDLK_RETURN, SDLK_SPACE):
                start_game()
                return
        elif event.type == SDL_MOUSEMOTION:
            mouse = (event.x, get_canvas_height() - 1 - event.y)
            trail.move(*mouse)
            for b in buttons:
                b.mouse_move(*mouse)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            mx, my = event.x, get_canvas_height() - 1 - event.y
            if any(b.click(mx, my) for b in buttons):
                return  # 화면이 바뀌었거나 종료됨
            splashes.append(InkSplash(mx, my))
            twinkles.extend(sparkle_burst(mx, my))


def update():
    global t, splashes, twinkles
    t += game_framework.frame_time
    for obj in bubbles + twinkles + splashes + buttons:
        obj.update()
    trail.update()
    splashes = [s for s in splashes if not s.done][-20:]
    twinkles = [s for s in twinkles if not s.done]


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def draw():
    clear_canvas()
    background.draw(CX, 360)

    for s in splashes:
        s.draw()
    for tw in twinkles:
        tw.draw()

    # 모래시계 잉크통: 둥실 떠 있고 뒤에서 빛이 숨 쉰다
    float_y = math.sin(t * 1.4) * 9
    bottle_glow.opacify(0.55 + 0.3 * math.sin(t * 1.8))
    bottle_glow.draw(CX, BOTTLE_Y + float_y)
    bottle_glow.opacify(1)
    shadow_k = 1 - float_y / 40
    bottle_shadow.opacify(0.6 * shadow_k)
    bottle_shadow.draw(CX, BOTTLE_Y - 172, bottle_shadow.w * shadow_k, bottle_shadow.h)
    bottle_shadow.opacify(1)
    bottle.composite_draw(math.sin(t * 0.9) * 0.04, '', CX, BOTTLE_Y + float_y, bottle.w, bottle.h)

    for b in bubbles:
        b.draw()

    # 로고: 처음에 위에서 내려앉으며 나타난다
    k = ease_out(t / INTRO)
    logo_y = LOGO_Y + (1 - k) * 40 + math.sin(t * 1.1) * 4
    logo_glow.opacify(k * (0.6 + 0.25 * math.sin(t * 1.5)))
    logo_glow.draw(CX, logo_y)
    logo_glow.opacify(1)
    logo.opacify(k)
    logo.draw(CX, logo_y)
    logo.opacify(1)
    sub_k = ease_out((t - INTRO * 0.6) / INTRO)
    subtitle.opacify(sub_k)
    subtitle.draw(CX, SUBTITLE_Y)
    subtitle.opacify(1)

    btn_k = ease_out((t - INTRO * 0.9) / INTRO)
    if btn_k > 0:
        for b in buttons:
            b.normal.opacify(btn_k)
            b.hover_image.opacify(btn_k)
            b.draw()
            b.normal.opacify(1)
            b.hover_image.opacify(1)

    trail.draw()
    cursor.draw(mouse[0] + CURSOR_OFFSET[0], mouse[1] + CURSOR_OFFSET[1])
    update_canvas()
