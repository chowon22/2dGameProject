"""타이틀 화면의 몽환적인 움직임: 비눗방울, 빛 입자, 반짝이, 커서 빛 선, 잉크 방울."""
import math
import random

import game_framework
from assets import image, folder

LIGHT_COLORS = ('pearl', 'sky', 'lavender', 'gold', 'pink')       # 빛 입자·붓자국
INK_COLORS = ('red', 'green', 'blue', 'yellow', 'cyan', 'magenta')  # 원소 색 잉크 방울
SCREEN_W, SCREEN_H = 1280, 720


class Bubble:
    """아래에서 위로 흔들리며 떠오르는 비눗방울 (무지갯빛 테두리)."""
    COLORS = ('pearl', 'pink', 'lavender', 'sky')

    def __init__(self, start_anywhere=False):
        self.reset()
        if start_anywhere:
            self.y = random.uniform(0, SCREEN_H)

    def reset(self):
        self.image = image(folder('title'), f'bubble_{random.choice(self.COLORS)}.png')
        self.base_x = random.uniform(40, SCREEN_W - 40)
        self.y = random.uniform(-90, -30)
        self.size = random.uniform(24, 64)
        self.speed = random.uniform(20, 44)
        self.sway = random.uniform(10, 30)
        self.phase = random.uniform(0, 2 * math.pi)
        self.t = 0.0

    @property
    def x(self):
        return self.base_x + math.sin(self.t * 0.9 + self.phase) * self.sway

    def update(self):
        dt = game_framework.frame_time
        self.t += dt
        self.y += self.speed * dt
        if self.y > SCREEN_H + 70:
            self.reset()

    def draw(self):
        fade = max(0.0, min(1.0, (SCREEN_H + 50 - self.y) / 240))
        self.image.opacify((0.75 + 0.2 * math.sin(self.t * 2 + self.phase)) * fade)
        wobble = 1 + 0.05 * math.sin(self.t * 3 + self.phase)
        self.image.draw(self.x, self.y, self.size * wobble, self.size / wobble)
        self.image.opacify(1)


class Mote:
    """반딧불처럼 깜빡이며 천천히 떠오르는 빛 입자. 잉크통 쪽에서 더 많이 생긴다."""

    def __init__(self, start_anywhere=False):
        self.reset()
        if start_anywhere:
            self.y = random.uniform(0, SCREEN_H)

    def reset(self):
        self.image = image(folder('title'), f'mote_{random.choice(LIGHT_COLORS)}.png')
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
        self.image = image(folder('title'), 'sparkle.png')
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
    """마우스가 지나간 자리에 이어지는 무지갯빛 그라데이션 선. 오래된 쪽부터 가늘어지며 사라진다."""
    SPACING = 5
    LIFE = 0.6
    MAX_POINTS = 120
    WIDTH = 9.0
    COLOR_STEPS = 12   # tools/gen_title_images.py 의 TRAIL_STEPS 와 같아야 한다
    COLOR_SPEED = 0.35  # 점 하나마다 색이 넘어가는 정도 (작을수록 그라데이션이 길다)

    def __init__(self):
        self.segments = [image('common', f'trail_segment_{i}.png') for i in range(self.COLOR_STEPS)]
        self.caps = [image('common', f'trail_cap_{i}.png') for i in range(self.COLOR_STEPS)]
        self.points = []  # [x, y, age, color_index]
        self.last = None
        self.hue = 0.0

    def _add(self, x, y):
        self.hue = (self.hue + self.COLOR_SPEED) % self.COLOR_STEPS
        self.points.append([x, y, 0.0, int(self.hue)])

    def move(self, x, y):
        if self.last is None:
            self.last = (x, y)
            self._add(x, y)
            return
        lx, ly = self.last
        if math.hypot(x - lx, y - ly) >= self.SPACING:
            self._add(x, y)
            self.last = (x, y)
            del self.points[:-self.MAX_POINTS]

    def update(self):
        dt = game_framework.frame_time
        for p in self.points:
            p[2] += dt
        self.points = [p for p in self.points if p[2] < self.LIFE]
        if not self.points:
            self.last = None

    def draw(self):
        for (x0, y0, a0, _), (x1, y1, a1, c) in zip(self.points, self.points[1:]):
            k = 1 - (a0 + a1) / 2 / self.LIFE
            if k <= 0:
                continue
            length = math.hypot(x1 - x0, y1 - y0)
            angle = math.atan2(y1 - y0, x1 - x0)
            thick = self.WIDTH * (0.25 + 0.75 * k)
            alpha = min(1.0, 0.15 + k)
            seg, cap = self.segments[c], self.caps[c]
            # 선 이미지(64x24)의 가운데 띠가 굵기가 되도록 높이를 맞춘다
            seg.opacify(alpha)
            seg.composite_draw(angle, '', (x0 + x1) / 2, (y0 + y1) / 2, length + 2, thick * 2.4)
            cap.opacify(alpha)
            cap.draw(x1, y1, thick * 2.4, thick * 2.4)
        for img in self.segments + self.caps:
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
