from pico2d import open_canvas, close_canvas

import game_framework
import title_mode

SCREEN_W, SCREEN_H = 1280, 720

open_canvas(SCREEN_W, SCREEN_H)
game_framework.run(title_mode)
close_canvas()
