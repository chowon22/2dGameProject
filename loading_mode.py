"""타이틀 → 준비 화면 사이 로딩 화면. 타이틀 위에 겹쳐 뜬다 (push_mode).

1. 타이틀이 어둡게 사라지고 (페이드 아웃)
2. 로딩 그림이 밝아지며 나타나 잠깐 머물고 (그동안 준비 화면 이미지를 미리 읽는다)
3. 다시 어두워진 뒤 준비 화면으로 바꾼다. 준비 화면은 어둠 속에서 밝아지며 시작한다 (prepare_mode 의 페이드 인)
"""
from pico2d import clear_canvas, update_canvas, get_events, SDL_QUIT

import game_framework
import prepare_mode
import title_mode
import text
from assets import image

FADE = 0.45        # 한 번 어두워지거나 밝아지는 데 걸리는 시간(초)
HOLD = 1.1         # 로딩 그림이 머무는 시간
NIGHT_TEXT = (226, 218, 236)

fade = loading = None
t = 0.0
phase = 'out'      # 'out' 타이틀이 사라짐 → 'in' 로딩이 나타남 → 'hold' → 'leave' 로딩이 사라짐
preloaded = False


def init():
    global fade, loading, t, phase, preloaded
    fade = image('common', 'fade.png')
    loading = image('prepare', 'loading.png')
    t = 0.0
    phase = 'out'
    preloaded = False


def finish():
    pass


def pause():
    pass


def resume():
    pass


def handle_events():
    for event in get_events():  # 전환 중에는 입력을 받지 않는다 (창 닫기만)
        if event.type == SDL_QUIT:
            game_framework.quit()


NEXT = {'out': ('in', FADE), 'in': ('hold', HOLD), 'hold': ('leave', FADE)}


def update():
    global t, phase, preloaded
    t += game_framework.frame_time
    if phase == 'out':
        title_mode.update_ambient()
    if phase == 'hold' and not preloaded:
        prepare_mode.preload()
        preloaded = True
    limit = FADE if phase in ('out', 'in', 'leave') else HOLD
    if t < limit:
        return
    if phase == 'leave':
        game_framework.reset_mode(prepare_mode)
        return
    phase, t = NEXT[phase][0], 0.0


def draw_dark(k):
    if k > 0:
        fade.opacify(min(1.0, k))
        fade.draw(640, 360, 1280, 720)
        fade.opacify(1)


def draw():
    clear_canvas()
    k = min(1.0, t / FADE)
    if phase == 'out':
        title_mode.draw_scene()
        draw_dark(k)
    else:
        loading.draw(640, 360)
        dots = '.' * (1 + int(t * 3) % 3) if phase != 'out' else ''
        text.draw(dots, 822, 128, 46, NIGHT_TEXT)
        draw_dark({'in': 1 - k, 'hold': 0.0, 'leave': k}[phase])
    update_canvas()
