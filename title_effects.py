"""타이틀 화면의 몽환적인 움직임: 빛 입자, 반짝이, 붓자국, 잉크 방울."""
import math
import random

import game_framework
from assets import image

LIGHT_COLORS = ('white', 'cyan', 'lavender', 'gold', 'pink')       # 빛 입자·붓자국
INK_COLORS = ('red', 'green', 'blue', 'yellow', 'cyan', 'magenta')  # 원소 색 잉크 방울
SCREEN_W, SCREEN_H = 1280, 720


class Mote:
    """반딧불처럼 깜빡이며 천천히 떠오르는 빛 입자. 잉크통 쪽에서 더 많이 생긴다."""

    def __init__(self, start_anywhere=False):
        self.reset()
        if start_anywhere:
            self.y = random.uniform(0, SCREEN_H)

    def reset(self):
        self.image = image('title', f'mote_{random.choice(LIGHT_COLORS)}.png')
        if random.random() < 0.45:
            self.base_x = random.gauss(SCREEN_W / 2, 120)  # 잉크통 빛기둥 근처
        else:
            self.base_x = random.uniform(20, SCREEN_W - 20)
        self.y = random.uniform(-40, 120)
        self.size = random.uniform(10, 30)
        self.speed = random.uniform(14, 40)
        self.sway = random.uniform(8, 36)
        self.phase = random.uniform(0, 2 * math.pi)
        self.blink = random.uniform(1.2, 3.0)
        self.t = 0.0

    @property
    def x(self):
        return self.base_x + math.sin(self.t * 0.7 + self.phase) * self.sway

    def update(self):
        dt = game_framework.frame_time
        self.t += dt
        self.y += self.speed * dt
        if self.y > SCREEN_H + 40:
            self.reset()

    def draw(self):
        fade = max(0.0, min(1.0, (SCREEN_H + 20 - self.y) / 300, self.t / 1.0))
        self.image.opacify((0.55 + 0.45 * math.sin(self.t * self.blink + self.phase)) * fade)
        self.image.draw(self.x, self.y, self.size, self.size)
        self.image.opacify(1)


class Twinkle:
    """하늘에서 커졌다 작아지며 반짝이는 별."""

    def __init__(self, x=None, y=None, size=None, life=None, vx=0.0, vy=0.0):
        self.image = image('title', 'sparkle.png')
        self.burst = x is not None  # 클릭으로 튄 반짝이는 한 번만 빛나고 사라진다
        self.respawn(x, y, size, life)
        self.vx, self.vy = vx, vy
        if not self.burst:
            self.t = random.uniform(0, self.life)  # 처음부터 제각각 반짝이게

    def respawn(self, x=None, y=None, size=None, life=None):
        self.x = x if x is not None else random.uniform(30, SCREEN_W - 30)
        self.y = y if y is not None else random.uniform(SCREEN_H * 0.4, SCREEN_H - 20)
        self.size = size or random.uniform(14, 30)
        self.life = life or random.uniform(1.6, 3.2)
        self.t = 0.0

    @property
    def done(self):
        return self.burst and self.t >= self.life

    def update(self):
        dt = game_framework.frame_time
        self.t += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 1 - min(1.0, dt * 3)
        self.vy *= 1 - min(1.0, dt * 3)
        if self.t >= self.life and not self.burst:
            self.respawn()

    def draw(self):
        k = math.sin(math.pi * min(1.0, self.t / self.life))
        if k <= 0.02:
            return
        self.image.opacify(k)
        s = self.size * (0.4 + 0.6 * k)
        self.image.composite_draw(self.t * 0.8, '', self.x, self.y, s, s)
        self.image.opacify(1)


class BrushTrail:
    """마우스가 지나간 자리에 빛나는 붓 점이 남았다가 사라진다."""
    SPACING = 7
    LIFE = 0.7
    MAX_DOTS = 260

    def __init__(self):
        self.images = [image('common', f'brush_dot_{c}.png') for c in LIGHT_COLORS]
        self.dots = []  # [x, y, age, color_index]
        self.last = None
        self.hue = 0.0

    def move(self, x, y):
        if self.last is None:
            self.last = (x, y)
            return
        lx, ly = self.last
        dist = math.hypot(x - lx, y - ly)
        steps = int(dist / self.SPACING)
        for i in range(1, steps + 1):
            t = i / steps
            self.hue = (self.hue + 0.12) % len(self.images)
            self.dots.append([lx + (x - lx) * t, ly + (y - ly) * t, 0.0, int(self.hue)])
        if steps:
            self.last = (x, y)
        del self.dots[:-self.MAX_DOTS]

    def update(self):
        dt = game_framework.frame_time
        for d in self.dots:
            d[2] += dt
        self.dots = [d for d in self.dots if d[2] < self.LIFE]

    def draw(self):
        for x, y, age, c in self.dots:
            k = 1 - age / self.LIFE
            img = self.images[c]
            img.opacify(min(1.0, 0.3 + k))
            s = 8 + 18 * k
            img.draw(x, y, s, s)
        for img in self.images:
            img.opacify(1)


class InkSplash:
    """클릭한 곳에 톡 튀었다가 번지며 사라지는 잉크 방울."""
    POP = 0.12
    HOLD = 0.5
    FADE = 1.2

    def __init__(self, x, y):
        self.image = image('common', f'ink_drop_{random.choice(INK_COLORS)}.png')
        self.x, self.y = x, y
        self.size = random.uniform(80, 120)
        self.rot = random.uniform(0, 2 * math.pi)
        self.t = 0.0

    @property
    def done(self):
        return self.t >= self.POP + self.HOLD + self.FADE

    def update(self):
        self.t += game_framework.frame_time

    def draw(self):
        if self.t < self.POP:
            k, alpha = 0.6 + 0.5 * self.t / self.POP, 1.0
        else:
            spread = (self.t - self.POP) / (self.HOLD + self.FADE)
            k = 1.1 + 0.15 * spread
            alpha = 1.0 if self.t < self.POP + self.HOLD else 1 - (self.t - self.POP - self.HOLD) / self.FADE
        self.image.opacify(max(0.0, alpha) * 0.9)
        s = self.size * k
        self.image.composite_draw(self.rot, '', self.x, self.y, s, s)
        self.image.opacify(1)


def sparkle_burst(x, y, count=5):
    """클릭 위치에서 사방으로 튀는 반짝이들."""
    out = []
    for _ in range(count):
        a = random.uniform(0, 2 * math.pi)
        speed = random.uniform(80, 180)
        out.append(Twinkle(x, y, random.uniform(12, 22), random.uniform(0.5, 0.9),
                           math.cos(a) * speed, math.sin(a) * speed))
    return out
