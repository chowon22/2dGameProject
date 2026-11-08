"""손그림 쪽지 버튼. 마우스를 올리면 색이 진해지고 살짝 커진다."""
import math

import game_framework
from assets import image

HIT_W, HIT_H = 264, 66  # 이미지(300x96)에서 실제 쪽지 부분만 클릭 범위로 쓴다


class Button:
    def __init__(self, x, y, normal, hover, on_click, phase=0.0):
        self.x, self.y = x, y
        self.normal = image('title', normal)
        self.hover_image = image('title', hover)
        self.on_click = on_click
        self.hovered = False
        self.scale = 1.0
        self.t = phase  # 버튼마다 흔들림 박자를 다르게

    def contains(self, mx, my):
        return abs(mx - self.x) <= HIT_W / 2 and abs(my - self.y) <= HIT_H / 2

    def mouse_move(self, mx, my):
        self.hovered = self.contains(mx, my)

    def click(self, mx, my):
        if self.contains(mx, my):
            self.on_click()
            return True
        return False

    def update(self):
        dt = game_framework.frame_time
        self.t += dt
        target = 1.07 if self.hovered else 1.0
        self.scale += (target - self.scale) * min(1.0, dt * 12)

    def draw(self):
        img = self.hover_image if self.hovered else self.normal
        bob = math.sin(self.t * 2.2) * 2.5
        tilt = math.sin(self.t * 1.7) * 0.015 if self.hovered else 0.0
        img.composite_draw(tilt, '', self.x, self.y + bob, img.w * self.scale, img.h * self.scale)
