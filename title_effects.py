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

    def draw(self, alpha=1.0):
        fade = max(0.0, min(1.0, (SCREEN_H + 50 - self.y) / 240)) * alpha
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

    def draw(self, alpha=1.0):
        fade = max(0.0, min(1.0, (SCREEN_H + 20 - self.y) / 300, self.t / 1.0)) * alpha
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
    """마우스가 지나간 자리에 이어지는 무지갯빛 그라데이션 선. 오래된 쪽부터 가늘어지며 사라진다.
    마우스 점들을 부드러운 곡선으로 잇고, 가운데까지 부드러운 둥근 붓 도장(trail_brush, tools/gen_trail_brush.py)을
    고른 간격으로 촘촘히 찍어 그린다."""
    SPACING = 5
    LIFE = 0.6
    MAX_POINTS = 120
    WIDTH = 9.0
    COLOR_STEPS = 12   # tools/gen_title_images.py 의 TRAIL_STEPS 와 같아야 한다
    COLOR_SPEED = 0.35  # 점 하나마다 색이 넘어가는 정도 (작을수록 그라데이션이 길다)

    def __init__(self):
        self.brushes = [image('common', f'trail_brush_{i}.png') for i in range(self.COLOR_STEPS)]
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

    STAMP_GAP = 0.15   # 붓 도장 간격 (굵기 대비). 고르게 촘촘히 찍어야 이음새에 점이 안 생긴다
    STAMP_ALPHA = 0.38  # 도장 하나의 진하기 (여러 장이 겹쳐 선이 된다)

    @staticmethod
    def _catmull(p0, p1, p2, p3, u):
        """p1→p2 사이를 부드러운 곡선으로 (Catmull-Rom)."""
        u2, u3 = u * u, u * u * u
        return tuple(0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3)
                     for a, b, c, d in zip(p0, p1, p2, p3))

    def _samples(self):
        """점들을 지나는 곡선 위의 (x, y, k, 색) 를 촘촘히. k = 남은 수명 비율."""
        pts = [(x, y, 1 - age / self.LIFE, c) for x, y, age, c in self.points]
        out = []
        for i in range(len(pts) - 1):
            p0, p1, p2 = pts[max(0, i - 1)], pts[i], pts[i + 1]
            p3 = pts[min(len(pts) - 1, i + 2)]
            n = max(2, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / 1.5))
            for j in range(n):
                u = j / n
                x, y, k = self._catmull(p0[:3], p1[:3], p2[:3], p3[:3], u)
                out.append((x, y, k, p1[3] if u < 0.5 else p2[3]))
        if pts:
            out.append(pts[-1])
        return out

    def draw(self):
        """같은 붓 도장을 곡선을 따라 고른 간격으로 찍어 끊김 없는 선을 만든다."""
        samples = self._samples()
        if not samples:
            return
        carry = 0.0
        px, py = samples[0][0], samples[0][1]
        for x, y, k, c in samples:
            if k <= 0:
                px, py = x, y
                continue
            thick = self.WIDTH * (0.25 + 0.75 * k)
            carry += math.hypot(x - px, y - py)
            px, py = x, y
            if carry < thick * self.STAMP_GAP:
                continue
            carry = 0.0
            brush = self.brushes[c]
            brush.opacify(self.STAMP_ALPHA * min(1.0, 0.15 + k))
            brush.draw(x, y, thick * 2.6, thick * 2.6)
        for img in self.brushes:
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


class InkDrip:
    """모래시계 목에서 검정 잉크 방울이 맺혔다 떨어지고, 아래 칸에 닿으면 원소 색 방울로 톡 튄다.
    거리는 모두 모래시계 중심에서 아래로 잰 값(원래 크기 px)이고, 그릴 때 scale 을 곱한다.
    - 맺힘: 목 구멍에 위쪽이 붙은 채 커지다가, 떨어지기 직전 아래로 살짝 늘어진다
    - 떨어짐: 처음엔 느리게, 점점 빨라지며 세로로 조금 늘어난다
    - 튐: 방울 아래쪽이 쌓인 색에 닿는 순간 색 방울이 튄다"""
    COLORS = ('red', 'green', 'blue')
    NECK = 8        # 방울이 매달리는 목 구멍 (이음 고리 바로 아래)
    FLOOR = 102     # 아래 칸에 쌓인 색 (튀는 자리)
    GROW, GRAVITY = 0.7, 1300.0
    SPLASH_TIME = 0.6
    DROP_SCALE, SPLASH_SCALE = 1.1, 1.6  # 방울은 목보다 넓지 않게, 튀는 색은 잘 보이게

    def __init__(self, phase=0.0):
        self.drop = image(folder('title'), 'drip_black.png')
        self.splash_images = [image(folder('title'), f'drip_splash_{c}.png') for c in self.COLORS]
        self.state, self.t, self.d, self.v = 'grow', -phase, 0.0, 0.0
        self.color = 0
        self.splash_t = None

    def _size(self, k):
        """맺히는 정도 k(0~1) 에서 방울 폭·높이 (원래 크기 px). 끝에서 아래로 늘어진다."""
        g = 0.25 + 0.75 * (1 - (1 - k) ** 2)
        sag = 1 + 0.3 * max(0.0, (k - 0.75) / 0.25)
        return self.drop.w * self.DROP_SCALE * g / (sag ** 0.5), self.drop.h * self.DROP_SCALE * g * sag

    def update(self):
        dt = game_framework.frame_time
        self.t += dt
        if self.splash_t is not None:
            self.splash_t += dt
            if self.splash_t > self.SPLASH_TIME:
                self.splash_t = None
        if self.state == 'grow' and self.t >= self.GROW:
            _, h = self._size(1.0)
            self.state, self.d, self.v = 'fall', self.NECK - 1 + h / 2, 0.0  # 떨어지는 방울 중심
        elif self.state == 'fall':
            self.v += self.GRAVITY * dt
            self.d += self.v * dt
            if self.d + self.drop.h * self.DROP_SCALE * 0.45 >= self.FLOOR:
                self.state, self.t = 'grow', -random.uniform(0.25, 0.7)
                self.splash_t, self.color = 0.0, (self.color + 1) % len(self.COLORS)

    def draw(self, x, y, scale, alpha=1.0, angle=0.0):
        """x, y = 모래시계 중심. angle = 모래시계 기울기(라디안, 반시계) — 방울도 같이 기울어진 축을 따른다."""
        sin_a, cos_a = math.sin(angle), math.cos(angle)

        def at(d):  # 중심에서 아래로 d 떨어진 점 (기울기 반영)
            return x + d * scale * sin_a, y - d * scale * cos_a
        self.drop.opacify(alpha)
        if self.state == 'grow' and self.t > 0:
            w, h = self._size(min(1.0, self.t / self.GROW))
            self.drop.draw(*at(self.NECK - 1 + h / 2), w * scale, h * scale)
        elif self.state == 'fall':
            stretch = 1 + min(0.35, self.v / 2400)
            w, h = self.drop.w * self.DROP_SCALE, self.drop.h * self.DROP_SCALE
            self.drop.draw(*at(self.d), w * scale / stretch, h * scale * stretch)
        self.drop.opacify(1)
        if self.splash_t is not None:
            k = self.splash_t / self.SPLASH_TIME
            img = self.splash_images[self.color]
            img.opacify(alpha * (1 - k ** 2))
            s = scale * self.SPLASH_SCALE * (0.5 + 0.7 * (1 - (1 - k) ** 3))
            sx, sy = at(self.FLOOR)
            img.draw(sx, sy + img.h * s / 2 - 6 * scale, img.w * s, img.h * s)
            img.opacify(1)
