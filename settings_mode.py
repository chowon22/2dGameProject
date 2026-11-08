"""설정 창. 타이틀 위에 겹쳐 뜬다 (push_mode / pop_mode).

- 배경음·효과음: 막대를 클릭하거나 끌어서 0~100% 조절
- 붓자국 효과·빛 입자 효과: 클릭해서 켜고 끄기
- 닫기 / ESC: 저장하고 타이틀로
"""
from pico2d import (clear_canvas, update_canvas, get_events,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_MOUSEBUTTONUP, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE)

import game_framework
import settings
import title_mode
from assets import image
from ui_button import Button

CX, CY = 640, 360
# 패널 이미지(680x500)에 써 둔 항목 이름과 같은 높이 (gen_title_images.settings_panel 참고)
ROW_Y = (460, 390, 320, 250)
SLIDER_X = 790
TOGGLE_X = 830
CLOSE_Y = 170
OPEN_TIME = 0.25

SLIDERS = {'bgm_volume': ROW_Y[0], 'sfx_volume': ROW_Y[1]}
TOGGLES = {'brush_trail': ROW_Y[2], 'light_motes': ROW_Y[3]}

dim = panel = track = track_fill = knob = toggle_on = toggle_off = None
close_button = None
dragging = None
t = 0.0


def close():
    settings.save()
    game_framework.pop_mode()


def init():
    global dim, panel, track, track_fill, knob, toggle_on, toggle_off, close_button, dragging, t
    dim = image('settings', 'dim.png')
    panel = image('settings', 'panel.png')
    track = image('settings', 'slider_track.png')
    track_fill = image('settings', 'slider_fill.png')
    knob = image('settings', 'slider_knob.png')
    toggle_on = image('settings', 'toggle_on.png')
    toggle_off = image('settings', 'toggle_off.png')
    close_button = Button(CX, CLOSE_Y, 'button_close.png', 'button_close_hover.png', close, folder='settings')
    dragging = None
    t = 0.0


def finish():
    pass


def pause():
    pass


def resume():
    pass


# ---------------------------------------------------------------- 슬라이더 계산
def track_range():
    """손잡이가 움직일 수 있는 x 범위 (막대 안쪽)."""
    half = track.w / 2 - 14
    return SLIDER_X - half, SLIDER_X + half


def value_to_x(v):
    x0, x1 = track_range()
    return x0 + (x1 - x0) * v


def x_to_value(x):
    x0, x1 = track_range()
    return (x - x0) / (x1 - x0)


def hit_slider(mx, my):
    for key, y in SLIDERS.items():
        if abs(my - y) <= 22 and abs(mx - SLIDER_X) <= track.w / 2 + 10:
            return key
    return None


def hit_toggle(mx, my):
    for key, y in TOGGLES.items():
        if abs(my - y) <= toggle_on.h / 2 and abs(mx - TOGGLE_X) <= toggle_on.w / 2:
            return key
    return None


# ---------------------------------------------------------------- 이벤트
def handle_events():
    global dragging
    for event in get_events():
        if event.type == SDL_QUIT:
            settings.save()
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            close()
            return
        elif event.type == SDL_MOUSEMOTION:
            mx, my = title_mode.to_canvas(event)
            title_mode.move_mouse((mx, my))
            close_button.mouse_move(mx, my)
            if dragging:
                settings.set(dragging, x_to_value(mx))
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            mx, my = title_mode.to_canvas(event)
            if close_button.click(mx, my):
                return
            key = hit_slider(mx, my)
            if key:
                dragging = key
                settings.set(key, x_to_value(mx))
            key = hit_toggle(mx, my)
            if key:
                settings.set(key, not settings.get(key))
        elif event.type == SDL_MOUSEBUTTONUP and event.button == SDL_BUTTON_LEFT:
            dragging = None


def update():
    global t
    t += game_framework.frame_time
    title_mode.update_ambient()
    close_button.update()


def draw():
    clear_canvas()
    title_mode.draw_scene()

    k = min(1.0, t / OPEN_TIME)
    k = 1 - (1 - k) ** 3
    dim.opacify(0.55 * k)
    dim.draw(CX, CY, 1280, 720)
    dim.opacify(1)

    # 창이 살짝 커지며 나타난다 (그동안 조작부는 숨김)
    s = 0.92 + 0.08 * k
    panel.opacify(k)
    panel.draw(CX, CY, panel.w * s, panel.h * s)
    panel.opacify(1)
    if k >= 1:
        for key, y in SLIDERS.items():
            v = settings.get(key)
            track.draw(SLIDER_X, y)
            fill_w = int(track.w * (value_to_x(v) - (SLIDER_X - track.w / 2)) / track.w)
            if fill_w > 0:
                track_fill.clip_draw(0, 0, fill_w, track_fill.h, SLIDER_X - track.w / 2 + fill_w / 2, y)
            knob.draw(value_to_x(v), y)
        for key, y in TOGGLES.items():
            (toggle_on if settings.get(key) else toggle_off).draw(TOGGLE_X, y)
        close_button.draw()

    title_mode.draw_cursor()
    update_canvas()
