"""준비 화면 (틀 고르기 + 유닛 그리기). 지금은 타이틀에서 넘어오는 자리만 잡아 둔 임시 화면."""
from pico2d import clear_canvas, update_canvas, get_events, SDL_QUIT, SDL_KEYDOWN, SDLK_ESCAPE

import game_framework
import title_mode
from assets import image

paper = None
wip_text = None


def init():
    global paper, wip_text
    paper = image('common', 'paper.png')
    wip_text = image('prepare', 'wip_text.png')


def finish():
    pass


def pause():
    pass


def resume():
    pass


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            game_framework.change_mode(title_mode)


def update():
    pass


def draw():
    clear_canvas()
    paper.draw(640, 360)
    wip_text.draw(640, 360)
    update_canvas()
