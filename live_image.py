"""numpy RGBA 배열을 pico2d Image 처럼 그리고, 바뀐 부분만 다시 올리는 이미지 (그리는 종이·틀 실루엣).

PNG 로 저장했다가 load_image 로 다시 읽지 않고, SDL 스트리밍 텍스처에 픽셀을 바로 넣는다.
open_canvas() 뒤에만 만들 수 있다.
"""
import ctypes

import numpy as np
from pico2d import Image
import pico2d.pico2d as _p  # _p.renderer 는 open_canvas() 뒤에 생긴다
from sdl2 import (SDL_CreateTexture, SDL_UpdateTexture, SDL_SetTextureBlendMode, SDL_Rect,
                  SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, SDL_BLENDMODE_BLEND)


class LiveImage(Image):
    def __init__(self, w, h, rgba=None):
        texture = SDL_CreateTexture(_p.renderer, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, w, h)
        SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_BLEND)
        super().__init__(texture)
        self.upload(np.zeros((h, w, 4), np.uint8) if rgba is None else rgba)

    def upload(self, rgba, x=0, y=0):
        """rgba (h, w, 4) 를 텍스처의 (x, y) (왼쪽 위 기준) 자리에 넣는다."""
        h, w = rgba.shape[:2]
        if not w or not h:
            return
        data = np.ascontiguousarray(rgba, dtype=np.uint8)
        SDL_UpdateTexture(self.texture, SDL_Rect(x, y, w, h), data.ctypes.data_as(ctypes.c_void_p), w * 4)
