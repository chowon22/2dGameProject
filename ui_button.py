"""분필로 그린 버튼. 마우스를 올리면 원소 색으로 칠해지고 살짝 커진다."""
import math

import game_framework
from assets import image

HIT_MARGIN_W, HIT_MARGIN_H = 36, 32  # 이미지 둘레의 빛 번짐 여백은 클릭 범위에서 뺀다


class Button:
    def __init__(self, x, y, normal, hover, on_click, phase=0.0, folder='title'):
        self.x, self.y = x, y
        self.normal = image(folder, normal)
        self.hover_image = image(folder, hover)
        self.on_click = on_click
        self.hovered = False
        self.scale = 1.0
        self.t = phase  # 버튼마다 흔들림 박자를 다르게

    def contains(self, mx, my):
        return (abs(mx - self.x) <= (self.normal.w - HIT_MARGIN_W) / 2 and
                abs(my - self.y) <= (self.normal.h - HIT_MARGIN_H) / 2)

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

    def draw(self, alpha=1.0):
        img = self.hover_image if self.hovered else self.normal
        bob = math.sin(self.t * 2.2) * 2.5
        tilt = math.sin(self.t * 1.7) * 0.015 if self.hovered else 0.0
        if alpha < 1:
            img.opacify(alpha)
        img.composite_draw(tilt, '', self.x, self.y + bob, img.w * self.scale, img.h * self.scale)
        if alpha < 1:
            img.opacify(1)
