"""준비 화면 (틀 고르기 + 유닛 그리기). 지금은 타이틀에서 넘어오는 자리만 잡아 둔 임시 화면.

세이브 파일 선택 화면에서 고른 세이브(save_data.current)로 들어온다. 나갈 때(ESC·창 닫기) 저장한다.
"""
from pico2d import clear_canvas, update_canvas, get_events, SDL_QUIT, SDL_KEYDOWN, SDLK_ESCAPE

import game_framework
import save_data
import text
import title_mode
from assets import image

paper = None
wip_text = None


def init():
    global paper, wip_text
    paper = image('common', 'paper.png')
    wip_text = image('prepare', 'wip_text.png')


def finish():
    save_data.save_current()


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
    if save_data.current:
        text.draw(f'세이브 {save_data.current["slot"]}  ·  {save_data.stage_name(save_data.current["stage"])}',
                  24, 700, 26, (86, 68, 106))
    update_canvas()
