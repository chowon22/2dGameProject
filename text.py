"""실행 중에 바뀌는 글씨(세이브 슬롯 내용 등)를 손글씨 폰트로 그린다.

pico2d 의 Font.draw 는 그릴 때마다 텍스처를 새로 만들어서, 같은 글씨는 한 번만 만들어 두고 다시 쓴다.
open_canvas() 뒤에만 쓸 수 있다.
"""
import os

from pico2d import Image
import pico2d.pico2d as _p  # _p.renderer 는 open_canvas() 뒤에 생긴다
from sdl2 import SDL_Color, SDL_CreateTextureFromSurface, SDL_FreeSurface
from sdl2.sdlttf import TTF_OpenFont, TTF_RenderUTF8_Blended

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
HAND = 'GamjaFlower-Regular.ttf'  # 파스텔·되찾은 색 그림체 손글씨

_fonts = {}
_cache = {}


def _font(name, size):
    key = (name, size)
    if key not in _fonts:
        f = TTF_OpenFont(os.path.join(FONT_DIR, name).encode('utf-8'), size)
        if not f:
            raise IOError(name)
        _fonts[key] = f
    return _fonts[key]


def image(s, size=28, color=(86, 68, 106), name=HAND):
    """글씨 한 줄을 Image 로 (같은 글씨·크기·색이면 만들어 둔 것을 준다)."""
    key = (s, size, tuple(color), name)
    if key not in _cache:
        surface = TTF_RenderUTF8_Blended(_font(name, size), s.encode('utf-8'), SDL_Color(*color))
        texture = SDL_CreateTextureFromSurface(_p.renderer, surface)
        SDL_FreeSurface(surface)
        _cache[key] = Image(texture)
    return _cache[key]


def draw(s, x, y, size=28, color=(86, 68, 106), anchor='l', alpha=1.0, name=HAND):
    """x, y 에 글씨를 그린다. anchor: 'l'(왼쪽 맞춤) / 'c'(가운데) / 'r'(오른쪽)."""
    if not s:
        return
    img = image(s, size, color, name)
    dx = {'l': img.w / 2, 'c': 0, 'r': -img.w / 2}[anchor]
    if alpha < 1:
        img.opacify(alpha)
    img.draw(x + dx, y)
    if alpha < 1:
        img.opacify(1)
