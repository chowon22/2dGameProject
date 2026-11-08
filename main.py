from pico2d import open_canvas, close_canvas
from sdl2 import SDL_StopTextInput

import game_framework
import title_mode

SCREEN_W, SCREEN_H = 1280, 720

open_canvas(SCREEN_W, SCREEN_H)
# SDL은 기본으로 텍스트 입력(IME)을 켜 둔다. 한/영이 한글이면 글자 키가 입력기로 먼저 가서
# 게임에 키가 안 오므로 끈다. (글자를 입력받는 화면이 생기면 그때만 SDL_StartTextInput)
SDL_StopTextInput()
game_framework.run(title_mode)
close_canvas()
