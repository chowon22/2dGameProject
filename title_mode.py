"""타이틀 화면.

- 깊은 밤 하늘 아래, 빛을 내뿜는 모래시계 잉크통이 둥실 떠 있고 로고가 내려앉는다.
- 빛 입자가 떠오르고 별이 반짝인다. 마우스는 분필 깃펜이 되어 빛나는 붓자국을 남긴다.
- 빈 곳을 클릭하면 원소 색 잉크 방울이 톡 튄다.
- 시작하기(Enter/Space) → 준비 화면, 설정 → 설정 창, 끝내기(ESC) → 종료.
- T / Tab / F2: 그림체 바꾸기 (낙서체 → 몽환 → 스케치북 → 잉크)
- 잉크 그림체는 펜으로 그린 흑백 동화 세상에서 시작해 잉크통에서부터 수채 물감이 번져 색이 칠해진다
"""
import math
import os

from pico2d import (clear_canvas, update_canvas, get_events, get_canvas_height, hide_cursor, show_cursor,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_t, SDLK_TAB, SDLK_F2)

import game_framework
import prepare_mode
import settings
import settings_mode
from assets import image, folder, IMAGE_DIR
from title_effects import Bubble, Mote, Twinkle, BrushTrail, InkSplash, sparkle_burst
from ui_button import Button

CX = 640
# 그림체마다 로고·잉크통 배치가 다르다
LAYOUTS = {
    'default': {'logo': (330, 562), 'bottle_y': 320, 'bottle_scale': 1.0},
    'sketchbook': {'logo': (640, 584), 'bottle_y': 284, 'bottle_scale': 0.84},  # 로고가 가운데 위
    'ink': {'logo': (640, 572), 'bottle_y': 264, 'bottle_scale': 0.84},
}
DYE_START, DYE_TIME = 0.5, 6.0  # 물들이기: 시작 시각과 다 번지는 데 걸리는 시간(초)
BUTTON_Y = 70
BUTTON_GAP = 262
INTRO = 1.6  # 로고가 내려앉는 시간(초)
CURSOR_OFFSET = (26, 26)  # 깃펜 이미지 중심에서 펜촉 끝까지 거리

background = logo = logo_glow = bottle = bottle_glow = light_pool = cursor = theme_hint = None
dye = []  # 물들이기 단계별 색 층 (있는 그림체만)
buttons = []
bubbles = []
motes = []
twinkles = []
splashes = []
trail = None
t = 0.0
mouse = (-100, -100)


def start_game():
    game_framework.change_mode(prepare_mode)


def open_settings():
    game_framework.push_mode(settings_mode)


def init():
    settings.load()
    load_scene()
    hide_cursor()


def switch_theme():
    """다음 그림체로 바꾸고 저장한 뒤 장면을 다시 불러온다."""
    themes = settings.THEMES
    now = settings.get('title_theme')
    settings.set('title_theme', themes[(themes.index(now) + 1) % len(themes)])
    settings.save()
    keep_mouse = mouse
    load_scene()
    move_mouse(keep_mouse)


def load_scene():
    global background, logo, logo_glow, bottle, bottle_glow, light_pool, cursor, theme_hint, dye
    global buttons, bubbles, motes, twinkles, splashes, trail, t, mouse
    title = folder('title')
    theme_hint = image('common', 'hint_theme.png')
    dye = []
    while os.path.exists(os.path.join(IMAGE_DIR, title, f'dye_{len(dye)}.png')):
        dye.append(image(title, f'dye_{len(dye)}.png'))
    background = image(title, 'background.png')
    logo = image(title, 'logo.png')
    logo_glow = image(title, 'logo_glow.png')
    bottle = image(title, 'ink_bottle.png')
    bottle_glow = image(title, 'bottle_glow.png')
    light_pool = image(title, 'light_pool.png')
    cursor = image('common', 'cursor_pen.png')

    buttons = [
        Button(CX - BUTTON_GAP, BUTTON_Y, 'button_start.png', 'button_start_hover.png', start_game, 0.0, title),
        Button(CX, BUTTON_Y, 'button_settings.png', 'button_settings_hover.png', open_settings, 0.8, title),
        Button(CX + BUTTON_GAP, BUTTON_Y, 'button_quit.png', 'button_quit_hover.png', game_framework.quit, 1.6,
               title),
    ]
    bubbles = [Bubble(start_anywhere=True) for _ in range(12)]
    motes = [Mote(start_anywhere=True) for _ in range(28)]
    twinkles = [Twinkle() for _ in range(14)]
    splashes = []
    trail = BrushTrail()
    t = 0.0
    mouse = (-100, -100)


def finish():
    show_cursor()


def pause():
    for b in buttons:
        b.hovered = False


def resume():
    pass


def to_canvas(event):
    return event.x, get_canvas_height() - 1 - event.y


def move_mouse(pos):
    """설정 창이 떠 있을 때도 커서와 붓자국은 여기서 처리한다."""
    global mouse
    mouse = pos
    if settings.get('brush_trail'):
        trail.move(*pos)
    else:
        trail.last = None


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                game_framework.quit()
            elif event.key in (SDLK_RETURN, SDLK_SPACE):
                start_game()
                return
            elif event.key in (SDLK_t, SDLK_TAB, SDLK_F2):
                switch_theme()
        elif event.type == SDL_MOUSEMOTION:
            move_mouse(to_canvas(event))
            for b in buttons:
                b.mouse_move(*mouse)
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            mx, my = to_canvas(event)
            if any(b.click(mx, my) for b in buttons):
                return  # 화면이 바뀌었거나 종료됨
            splashes.append(InkSplash(mx, my))
            twinkles.extend(sparkle_burst(mx, my))


def update_ambient():
    """배경 움직임만 갱신 (설정 창 뒤에서도 계속 흐르게)."""
    global t, splashes, twinkles
    t += game_framework.frame_time
    if settings.get('light_motes'):
        for m in motes + bubbles:
            m.update()
    for obj in twinkles + splashes:
        obj.update()
    trail.update()
    splashes = [s for s in splashes if not s.done][-20:]
    twinkles = [s for s in twinkles if not s.done]


def update():
    update_ambient()
    for b in buttons:
        b.update()


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def draw_with_alpha(img, alpha, *args):
    img.opacify(alpha)
    img.draw(*args)
    img.opacify(1)


def draw_dye():
    """색 층을 단계별로 겹쳐 그려 잉크통에서부터 색이 번져 나가게 한다.
    k 번째 층을 다 그리고 k+1 번째 층을 비율만큼 겹치면 경계가 부드럽게 넓어진다."""
    if not dye:
        return
    p = max(0.0, min(1.0, (t - DYE_START) / DYE_TIME)) * len(dye)
    k = int(p)
    if k > 0:
        dye[min(k, len(dye)) - 1].draw(CX, 360, 1280, 720)
    if k < len(dye):
        draw_with_alpha(dye[k], p - k, CX, 360, 1280, 720)


def layout():
    return LAYOUTS.get(settings.get('title_theme'), LAYOUTS['default'])


def draw_scene():
    """커서를 뺀 타이틀 화면 전체."""
    lay = layout()
    logo_x, logo_base_y = lay['logo']
    bottle_y, sc = lay['bottle_y'], lay['bottle_scale']
    background.draw(CX, 360)
    draw_dye()

    for tw in twinkles:
        tw.draw()

    # 잉크통: 둥실 떠 있고 뒤에서 빛이 숨 쉰다
    float_y = math.sin(t * 1.3) * 10 * sc
    draw_with_alpha(bottle_glow, 0.6 + 0.3 * math.sin(t * 1.7), CX, bottle_y + float_y,
                    bottle_glow.w * sc, bottle_glow.h * sc)
    pool_k = 1 - float_y / 50
    pool_y = bottle_y - bottle.h * sc / 2 - 32 * sc
    draw_with_alpha(light_pool, 0.7 * pool_k, CX, pool_y, light_pool.w * pool_k * sc, light_pool.h * sc)
    bottle.composite_draw(math.sin(t * 0.8) * 0.035, '', CX, bottle_y + float_y, bottle.w * sc, bottle.h * sc)

    if settings.get('light_motes'):
        for b in bubbles:
            b.draw()
        for m in motes:
            m.draw()
    for s in splashes:
        s.draw()

    # 로고: 처음에 위에서 내려앉으며 나타난다
    k = ease_out(t / INTRO)
    logo_y = logo_base_y + (1 - k) * 40 + math.sin(t * 1.1) * 4
    draw_with_alpha(logo_glow, k * (0.55 + 0.25 * math.sin(t * 1.5)), logo_x, logo_y)
    draw_with_alpha(logo, k, logo_x, logo_y)

    btn_k = ease_out((t - INTRO * 0.6) / INTRO)
    if btn_k > 0:
        for b in buttons:
            b.normal.opacify(btn_k)
            b.hover_image.opacify(btn_k)
            b.draw()
            b.normal.opacify(1)
            b.hover_image.opacify(1)

    trail.draw()


def draw_hint():
    """오른쪽 아래 'T 그림체 바꾸기' 안내."""
    draw_with_alpha(theme_hint, 0.75 * ease_out((t - INTRO) / INTRO), 1280 - theme_hint.w / 2 - 12, theme_hint.h / 2 + 8)


def draw_cursor():
    cursor.draw(mouse[0] + CURSOR_OFFSET[0], mouse[1] + CURSOR_OFFSET[1])


def draw():
    clear_canvas()
    draw_scene()
    draw_hint()
    draw_cursor()
    update_canvas()
