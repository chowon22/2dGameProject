"""스토리 컷씬: 새 여정을 시작하면 준비 화면 전에 한 번 보여 주는 도입 이야기 (PRD 2.4 스토리 흐름, 10장 P2 스토리 컷).

동화책을 한 장씩 넘기듯 일곱 컷이 이어지고, 컷마다 아래 쪽지에 한 문장씩 손글씨가 써진다.
1. 숲속 흑백 동굴 앞에 온 소년이 동굴 안으로 들어간다
2. 동굴 안에서 컬러 잉크통을 발견한다 → 잉크통에서부터 동굴에 색이 번진다
3. 잉크통으로 불도 피우고 얼음도 만들며 즐겁게 지낸다
4. 소년이 잠든 밤, 긴 외투의 남자가 잉크통을 가져간다
5. 아침, 세상의 색이 빠져나가고 색을 담아 나르는 운반자 몬스터들이 날아다닌다
6. 봉인 장소에서 검정 잉크통을 찾는다. 검정은 색을 빨아들인다
7. 검정 잉크통을 안고 흑백 들판을 달려 여정을 떠난다

- 클릭 / Space / Enter: 글씨가 써지는 중이면 다 쓰고, 다 써졌으면 다음 문장·다음 컷
- ESC: 건너뛰기
- 끝나면(건너뛰어도) 세이브에 본 것으로 적고 준비 화면으로 (로딩 화면 대신 컷씬이 준비 화면 이미지를 미리 읽는다)

바깥 동굴(낮·밤)은 타이틀 그림, 동굴 안은 image/cutscene_inside, 소년은 준비 화면 달리기 스프라이트, 나머지는 tools/gen_cutscene.py.
"""
import math
import random

from pico2d import (clear_canvas, update_canvas, get_events, hide_cursor,
                    SDL_QUIT, SDL_KEYDOWN, SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN, SDL_BUTTON_LEFT,
                    SDLK_ESCAPE, SDLK_SPACE, SDLK_RETURN)

import game_framework
import prepare_mode
import save_data
import text
import title_mode
from assets import image

W, H = 1280, 720
CX = W / 2
GROUND = 135            # 타이틀 배경의 땅 (tools/gen_title_bg.GROUND, PIL 585)
FADE = 0.6              # 컷이 어둠에서 밝아지거나 어두워지는 시간
TYPE_SPEED = 15         # 쪽지에 글씨가 써지는 빠르기 (글자/초)
CAPTION_Y = 62
CAPTION_SIZE = 34
INK = (86, 68, 106)
HINT = (250, 246, 255)
# 컬러 잉크통 자리: 동굴 안 바위 위에 떠 있다 (물들이기가 시작되는 곳 gen_title_pastel.DYE_FROM 바로 아래).
# 모래시계는 검정·컬러 두 잉크통이 합쳐진 모습이고, 동굴에서 찾는 건 아래 칸 컬러 잉크통 하나다
BOTTLE = (CX, 232)
BOTTLE_SCALE = 0.62
COLORS = ('red', 'green', 'blue')


# ---------------------------------------------------------------- 그리기 도우미
def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def pop(x):
    """0 → 1 로 살짝 넘쳤다가 자리 잡는 크기 (톡 튀어나오기)."""
    x = clamp01(x)
    return 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2


def draw_alpha(img, a, x, y, w=None, h=None, rad=0.0, flip=''):
    if a <= 0:
        return
    w = img.w if w is None else w
    h = img.h if h is None else h
    if a < 1:
        img.opacify(a)
    if rad or flip:
        img.composite_draw(rad, flip, x, y, w, h)
    else:
        img.draw(x, y, w, h)
    if a < 1:
        img.opacify(1)


def draw_dye(frames, p):
    """타이틀과 같은 물들이기: 색 층을 단계별로 겹쳐 잉크통 자리에서부터 색이 번져 나간다 (p 0~1)."""
    p = clamp01(p) * len(frames)
    k = int(p)
    if k > 0:
        frames[min(k, len(frames)) - 1].draw(CX, H / 2)
    if k < len(frames):
        draw_alpha(frames[k], p - k, CX, H / 2)


def dye_frames(folder):
    return [image(folder, f'dye_{i}.png') for i in range(10)]


def draw_boy(t, x, ground=GROUND, frame=None, flip=False, lift=0.0, scale=1.0, alpha=1.0):
    """준비 화면 달리기 스프라이트 (평소엔 1:1). frame 을 주지 않으면 달린다.
    scale·alpha: 동굴 안으로 들어가며 작아지고 흐려질 때."""
    if frame is None:
        frame = int(t * prepare_mode.RUN_FPS) % prepare_mode.RUN_FRAMES
    s = (1 - min(0.3, lift / 60)) * scale
    draw_alpha(shadow, alpha, x + 2, ground - 2, shadow.w * 0.55 * s, shadow.h * 0.6 * s)
    img = boys[frame]
    y = ground - 4 + (prepare_mode.BOY_FEET + lift) * scale
    if scale == 1.0 and alpha >= 1 and not flip:
        img.draw(round(x), round(y))
    else:
        draw_alpha(img, alpha, round(x), round(y), img.w * scale, img.h * scale, flip='h' if flip else '')


def draw_bottle(t, x, y, scale=BOTTLE_SCALE, glow=0.6, float_k=1.0):
    """둥실 떠서 숨 쉬듯 빛나는 컬러 잉크통 (타이틀 모래시계의 아래 칸). float_k: 둥실거리는 정도 (손에 들면 0)."""
    fy = math.sin(t * 1.3) * 6 * scale * float_k
    draw_alpha(bottle_glow, glow * (0.8 + 0.2 * math.sin(t * 1.7)), x, y + fy,
               bottle_glow.w * scale, bottle_glow.h * scale)
    draw_alpha(bottle, 1.0, x, y + fy, bottle.w * scale, bottle.h * scale, math.sin(t * 0.8) * 0.035 * float_k)


class Spark:
    """톡 튀어 퍼지며 반짝이다 사라지는 별빛."""

    def __init__(self, x, y, speed=(60, 160), size=(12, 22), life=(0.5, 0.9)):
        a = random.uniform(0, 2 * math.pi)
        v = random.uniform(*speed)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * v, math.sin(a) * v
        self.size = random.uniform(*size)
        self.life = random.uniform(*life)
        self.t = 0.0

    @property
    def done(self):
        return self.t >= self.life

    def update(self, dt):
        self.t += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        k = 1 - min(1.0, dt * 3)
        self.vx, self.vy = self.vx * k, self.vy * k

    def draw(self):
        u = self.t / self.life
        s = self.size * math.sin(math.pi * u)
        draw_alpha(sparkle, 1 - u * 0.5, self.x, self.y, s, s, u * 2)


def burst(x, y, count=8, **kw):
    return [Spark(x, y, **kw) for _ in range(count)]


class Drop:
    """색 방울이 target 쪽으로 빨려 들어간다 (운반자 몬스터의 배 속, 검정 잉크통)."""

    def __init__(self, color, x, y, target, time=1.0, swirl=0.0, size=22):
        self.image = image('common', f'ink_drop_{color}.png')
        self.x0, self.y0 = x, y
        self.target = target        # () -> (x, y): 움직이는 대상도 따라간다
        self.time = time
        self.swirl = swirl          # 빙 돌아 들어가는 정도 (라디안)
        self.size = size
        self.t = 0.0

    @property
    def done(self):
        return self.t >= self.time

    def update(self, dt):
        self.t += dt

    def draw(self):
        u = clamp01(self.t / self.time)
        k = u * u
        tx, ty = self.target()
        dx, dy = self.x0 - tx, self.y0 - ty
        a = self.swirl * k
        r = 1 - k
        x = tx + (dx * math.cos(a) - dy * math.sin(a)) * r
        y = ty + (dx * math.sin(a) + dy * math.cos(a)) * r
        s = self.size * (1 - 0.6 * k) * min(1.0, u * 6)
        draw_alpha(self.image, min(1.0, (1 - u) * 4), x, y, s, s)


# ---------------------------------------------------------------- 컷
class Cut:
    """컷 하나. lines 의 문장이 한 번에 하나씩 쪽지에 써진다.
    t: 컷이 시작된 뒤 시간, step: 지금 문장 번호, st: 지금 문장이 시작된 뒤 시간."""
    lines = ()

    def __init__(self):
        self.t = self.st = 0.0
        self.step = 0
        self.effects = []

    def next_step(self):
        self.step += 1
        self.st = 0.0
        self.on_step(self.step)

    def on_step(self, step):
        pass

    def update(self, dt):
        self.t += dt
        self.st += dt
        for e in self.effects:
            e.update(dt)
        self.effects = [e for e in self.effects if not e.done]

    def draw_effects(self):
        for e in self.effects:
            e.draw()


class CaveCut(Cut):
    """1. 숲속 흑백 동굴 앞까지 달려와 갸웃하다가, 동굴 입구로 들어간다 (작아지고 흐려지며 안쪽으로)."""
    lines = ('숲속 깊은 곳, 모든 것이 흑백인 신기한 동굴이 있었어요.',
             '호기심 많은 소년은 동굴 안으로 들어가 보았어요.')
    ARRIVE = 2.4
    STOP_X = 400
    MOUTH = (CX, GROUND + 26)   # 동굴 입구 안쪽 (발이 닿는 곳이 조금 높아져 깊어 보인다)
    ENTER = 1.8

    def __init__(self):
        super().__init__()
        self.from_x = self.STOP_X

    def on_step(self, step):
        if step == 1:
            self.from_x = self.arrive_x()

    def arrive_x(self):
        return -90 + (self.STOP_X + 90) * ease_out(self.t / self.ARRIVE) ** 0.8

    def draw(self):
        bg_gray.draw(CX, H / 2)
        if self.step == 0:
            x = self.arrive_x()
            running = self.t < self.ARRIVE * 0.92
            draw_boy(self.t, x, frame=None if running else 1)
            if not running:   # 머리 위 물음표
                s = pop((self.t - self.ARRIVE * 0.92) / 0.35)
                text.draw('?', x + 18, GROUND + 205, 56, INK, 'c', scale=s)
        else:
            k = ease_in_out(self.st / self.ENTER)
            x = self.from_x + (self.MOUTH[0] - self.from_x) * k
            ground = GROUND + (self.MOUTH[1] - GROUND) * k
            alpha = 1 - clamp01((k - 0.55) / 0.45)
            draw_boy(self.t, x, ground, scale=1 - 0.45 * k, alpha=alpha)
        self.draw_effects()


class InsideCut(Cut):
    """2. 흑백 동굴 안쪽 바위 위에 잉크통이 빛난다. 소년이 찾아내자 잉크통에서부터 동굴에 색이 번진다."""
    lines = ('동굴 안쪽에서, 소년은 반짝이는 컬러 잉크통을 발견했어요.',
             '잉크통이 반짝 빛나자, 흑백이던 동굴에 색이 번져 나갔어요.')
    ARRIVE = 2.2
    STOP_X = 380
    DYE_TIME = 3.2

    def __init__(self):
        super().__init__()
        self.found = None   # 색이 번지기 시작한 시각 (self.t)

    def on_step(self, step):
        if step == 1:
            self.found = self.t
            self.effects += burst(*BOTTLE, 14, speed=(80, 220))

    def boy_x(self):
        return -90 + (self.STOP_X + 90) * ease_out(self.t / self.ARRIVE) ** 0.8

    def draw(self):
        inside_gray.draw(CX, H / 2)
        ft = None if self.found is None else self.t - self.found
        if ft is not None:
            draw_dye(dye_inside, ft / self.DYE_TIME)
        glow = 0.45 if ft is None else 0.45 + 0.4 * ease_out(ft / 0.8)
        draw_bottle(self.t, *BOTTLE, glow=glow)
        stop = self.ARRIVE * 0.92
        running = self.t < stop
        lift = 0.0
        if ft is not None and ft < 1.3:
            lift = abs(math.sin(ft * math.pi / 0.43)) * 18   # 신이 나서 콩콩 뛴다
        x = self.boy_x()
        draw_boy(self.t, x, frame=None if running else 1, lift=lift)
        if not running:   # 잉크통을 보고 느낌표
            text.draw('!', x + 18, GROUND + 205 + lift, 56, INK, 'c', scale=pop((self.t - stop) / 0.35))
        self.draw_effects()


class PlayCut(Cut):
    """3. 잉크통을 들고 나와, 색을 되찾은 동굴 앞에서 불도 피우고 얼음도 만들며 뛰논다."""
    lines = ('잉크통의 색으로 불도 피우고, 얼음도 만들고.',
             '소년은 하루하루가 즐거웠어요.')
    LEFT, RIGHT = 400, 880
    SPEED = 230
    FIRE = (250, 0.5)   # (x, 나타나는 시각)
    ICE = (1035, 1.4)

    def __init__(self):
        super().__init__()
        self.next_spark = 0.0
        self.popped = set()

    def boy(self):
        """두 지점 사이를 왔다 갔다 달린다 → (x, 왼쪽을 보는가)."""
        span = self.RIGHT - self.LEFT
        d = (self.t * self.SPEED) % (span * 2)
        return (self.LEFT + d, False) if d < span else (self.RIGHT - (d - span), True)

    def update(self, dt):
        super().update(dt)
        for name, (x, t0) in (('fire', self.FIRE), ('ice', self.ICE)):
            if name not in self.popped and self.t >= t0:
                self.popped.add(name)
                self.effects += burst(x, GROUND + 70, 10)
        if self.step == 1 and self.t >= self.next_spark:   # 즐거운 반짝이
            self.next_spark = self.t + 0.35
            x, _ = self.boy()
            self.effects.append(Spark(x + random.uniform(-60, 60), GROUND + random.uniform(120, 220),
                                      speed=(10, 40), life=(0.8, 1.2)))

    def draw(self):
        bg_gray.draw(CX, H / 2)
        dye_day[-1].draw(CX, H / 2)
        draw_bottle(self.t, *BOTTLE, glow=0.7)
        for img, (x, t0), flick in ((fire, self.FIRE, 9.0), (ice, self.ICE, 0.0)):
            u = self.t - t0
            if u <= 0:
                continue
            s = pop(u / 0.45)
            sy = s * (1 + 0.05 * math.sin(self.t * flick)) if flick else s
            sx = s * (1 - 0.03 * math.sin(self.t * flick)) if flick else s
            img.draw(x, GROUND - 6 + img.h * sy / 2, img.w * sx, img.h * sy)
        x, left = self.boy()
        draw_boy(self.t, x, flip=left)
        self.draw_effects()


class NightCut(Cut):
    """4. 소년이 잠든 밤, 긴 외투의 남자가 몰래 다가와 잉크통을 가져간다."""
    lines = ('그러던 어느 밤, 소년이 잠든 사이…',
             '긴 외투를 입은 남자가 몰래 잉크통을 가져가 버렸어요.')
    SLEEPER_X = 230
    MAN_SCALE = 0.8
    HAND = (100, 20)        # man.png 가운데에서 손까지 (tools/gen_cutscene.MAN_HAND)
    FEET = 210              # man.png 가운데에서 발바닥까지
    ENTER = (0.8, 4.8)      # 왼쪽 밖에서 잉크통 앞까지 걸어오는 때
    OUT_X = 1500

    def __init__(self):
        super().__init__()
        self.stop_x = BOTTLE[0] - self.HAND[0] * self.MAN_SCALE
        self.from_x = None  # 둘째 문장이 시작될 때 남자가 있던 곳

    def on_step(self, step):
        if step == 1:
            self.from_x = self.enter_x()

    def enter_x(self):
        """첫 문장 동안: 왼쪽 밖에서 잠든 소년 옆을 지나 잉크통 앞까지 걸어온다."""
        t0, t1 = self.ENTER
        return -160 + (self.stop_x + 160) * ease_in_out((self.t - t0) / (t1 - t0))

    def man_x(self):
        if self.step == 0:
            return self.enter_x()
        if self.st < 0.6:   # 아직 다 오지 않았으면 마저 다가온다
            return self.from_x + (self.stop_x - self.from_x) * ease_in_out(self.st / 0.6)
        return self.stop_x + (self.OUT_X - self.stop_x) * ease_in_out((self.st - 1.8) / 4.5)

    def walking(self):
        if self.step == 0:
            return self.ENTER[0] < self.t < self.ENTER[1]
        return self.st < 0.6 or self.st > 1.8

    def hand(self, x, y):
        return x + self.HAND[0] * self.MAN_SCALE, y + self.HAND[1] * self.MAN_SCALE

    def draw(self):
        bg_night.draw(CX, H / 2)
        dye_night[-1].draw(CX, H / 2)
        x = self.man_x()
        bob = abs(math.sin(self.t * 5.5)) * 6 if self.walking() else 0.0
        y = GROUND - 6 + self.FEET * self.MAN_SCALE + bob
        # 잉크통: 동굴 안에 떠 있다가 둘째 문장에서 남자 손으로 날아간다
        grab = 0.0 if self.step == 0 else ease_in_out((self.st - 0.6) / 0.8)
        hx, hy = self.hand(x, y)
        bs = 0.45
        bx = BOTTLE[0] + (hx - BOTTLE[0]) * grab
        by = BOTTLE[1] + (hy + bottle.h * bs / 2 - BOTTLE[1]) * grab
        scale = BOTTLE_SCALE + (bs - BOTTLE_SCALE) * grab
        # 잠든 소년과 머리 위 z
        sleeper.draw(self.SLEEPER_X, GROUND - 8 + sleeper.h / 2)
        for i in range(3):
            u = (self.t * 0.45 + i / 3) % 1
            text.draw('z' if i % 2 else 'Z', self.SLEEPER_X - 40 + u * 50, GROUND + 110 + u * 80,
                      int(24 + u * 16), HINT, 'c', alpha=math.sin(math.pi * u) * 0.9)
        man_img.draw(x, y, man_img.w * self.MAN_SCALE, man_img.h * self.MAN_SCALE)
        draw_bottle(self.t, bx, by, scale, glow=0.7 * (1 - grab * 0.6), float_k=1 - grab)
        self.draw_effects()


class DrainCut(Cut):
    """5. 아침, 세상의 색이 빠져나가고 운반자 몬스터들이 색을 몸에 담아 날아다닌다."""
    lines = ('아침이 되자, 세상의 색이 빠져나가고 있었어요.',
             '색을 몸에 담아 나르는 몬스터들이 날아다녔어요.')
    DRAIN = (0.6, 5.5)      # 색이 빠지기 시작하는 때, 다 빠질 때
    # (색, 지나가는 높이, 출발 위치, 빠르기)
    CARRIERS = (('red', 500, 0, 110), ('green', 430, 520, 95), ('blue', 560, 1050, 120))

    def __init__(self):
        super().__init__()
        self.next_drop = 0.0

    def carrier_pos(self, i, t=None):
        t = self.t if t is None else t
        _, y, start, speed = self.CARRIERS[i]
        x = W + 120 - (start + t * speed) % (W + 360)
        return x, y + math.sin(t * 1.7 + i * 2) * 22

    def drained(self):
        t0, t1 = self.DRAIN
        return ease_in_out((self.t - t0) / (t1 - t0))

    def update(self, dt):
        super().update(dt)
        left = 1 - self.drained()
        if self.t >= self.next_drop and left > 0.02:   # 땅에서 색 방울이 떠올라 몬스터 배 속으로
            self.next_drop = self.t + 0.12 / max(0.3, left)
            i = random.randrange(len(self.CARRIERS))
            x, _ = self.carrier_pos(i)
            if -40 < x < W + 40:
                self.effects.append(Drop(self.CARRIERS[i][0], x + random.uniform(-120, 120),
                                         GROUND + random.uniform(0, 140),
                                         lambda i=i: self.carrier_pos(i), random.uniform(0.9, 1.4), 0.0, 34))

    def draw(self):
        bg_gray.draw(CX, H / 2)
        draw_dye(dye_day, 1 - self.drained())
        self.draw_effects()
        for i, (color, *_rest) in enumerate(self.CARRIERS):
            x, y = self.carrier_pos(i)
            img = carriers[color]
            s = 1 + 0.04 * math.sin(self.t * 4 + i)
            img.composite_draw(math.sin(self.t * 2 + i) * 0.08, '', x, y, img.w * s, img.h / s)


class SealCut(Cut):
    """6. 봉인 장소에서 검정 잉크통을 찾는다. 검정은 색을 빨아들인다."""
    lines = ('망연자실해 찾아간 봉인 장소에서,',
             '소년은 오래된 검정 잉크통을 찾았어요.',
             '검정은 색 있는 것에 닿으면, 그 색을 빨아들였어요.')
    PEDESTAL = 250          # 제단 윗면 (gen_cutscene.seal, PIL 470)
    SCALE = 0.62

    def __init__(self):
        super().__init__()
        self.next_drop = 0.0
        self.pulse = 0.0

    def mouth(self):
        """잉크통 아가리 (색이 빨려 들어가는 곳)."""
        return CX, self.PEDESTAL + black_bottle.h * self.SCALE * 0.6

    def on_step(self, step):
        if step == 1:
            self.effects += burst(*self.mouth(), 12, speed=(60, 160))

    def update(self, dt):
        if any(isinstance(e, Drop) and e.t < e.time <= e.t + dt for e in self.effects):
            self.pulse = 1.0    # 색 방울을 하나 빨아들일 때마다 꿀꺽
        super().update(dt)
        self.pulse = max(0.0, self.pulse - dt * 2)
        if self.step == 2 and self.t >= self.next_drop:
            self.next_drop = self.t + 0.16
            a = random.uniform(0, 2 * math.pi)
            r = random.uniform(260, 420)
            mx, my = self.mouth()
            d = Drop(random.choice(COLORS), mx + math.cos(a) * r, my + math.sin(a) * r * 0.6, self.mouth,
                     random.uniform(1.0, 1.5), random.choice((-1, 1)) * 2.2, 36)
            self.effects.append(d)

    def draw(self):
        seal_bg.draw(CX, H / 2)
        s = self.SCALE * (1 + 0.06 * self.pulse)
        found = 0.0 if self.step == 0 else ease_out(self.st / 1.0) if self.step == 1 else 1.0
        bw, bh = black_bottle.w * s, black_bottle.h * s
        draw_alpha(bottle_glow, 0.25 + 0.35 * found + 0.2 * self.pulse, CX, self.PEDESTAL + bh / 2,
                   bottle_glow.w * 0.5, bottle_glow.h * 0.45)
        black_bottle.draw(CX, self.PEDESTAL - 2 + bh / 2, bw, bh)
        self.draw_effects()


class DepartCut(Cut):
    """7. 검정 잉크통을 안고 색을 빼앗긴 흑백 들판을 달려 여정을 떠난다."""
    lines = ('이 검정이라면, 빼앗긴 색을 되찾을 수 있을지도 몰라.',
             '소년은 검정 잉크통을 안고 길을 떠났어요.')
    GROUND = prepare_mode.GROUND
    SPEED = {'far': 14, 'mid': 60, 'ground': 170}
    STOP_X = 560

    def draw_layer(self, name, y):
        img = run_layers[name]
        off = (self.t * self.SPEED[name]) % img.w
        for i in range(2):
            img.draw(img.w / 2 - off + img.w * i, y)

    def draw(self):
        run_layers['sky'].draw(CX, H / 2)
        self.draw_layer('far', H / 2)
        self.draw_layer('mid', H / 2)
        self.draw_layer('ground', run_layers['ground'].h / 2)
        x = -120 + (self.STOP_X + 120) * ease_out(self.t / 2.0)
        draw_boy(self.t, x, ground=self.GROUND)
        self.draw_effects()


CUTS = (CaveCut, InsideCut, PlayCut, NightCut, DrainCut, SealCut, DepartCut)

# ---------------------------------------------------------------- 모드
fade = caption = next_mark = sparkle = shadow = None
bottle = bottle_glow = bg_gray = bg_night = inside_gray = fire = ice = man_img = sleeper = seal_bg = black_bottle = None
boys = []
dye_day = dye_night = dye_inside = []
carriers = {}
run_layers = {}
cut = None
index = 0
phase = 'title'     # 'title' 타이틀이 어두워짐 → 컷마다 'in' 밝아짐 → 'play' → 'out' 어두워짐
t = 0.0             # 지금 phase 가 시작된 뒤 시간
typed = 0.0         # 지금 문장이 써진 글자 수
skipping = False


def load_images():
    global fade, caption, next_mark, sparkle, shadow, bottle, bottle_glow, bg_gray, bg_night, fire, ice, man_img
    global inside_gray, dye_inside, sleeper, seal_bg, black_bottle, boys, dye_day, dye_night, carriers, run_layers
    fade = image('common', 'fade.png')
    caption = image('cutscene', 'caption.png')
    next_mark = image('common', 'ink_drop_blue.png')
    sparkle = image('title_pastel', 'sparkle.png')
    shadow = image('prepare', 'shadow.png')
    boys = [image('prepare', f'boy_run_{i}.png') for i in range(prepare_mode.RUN_FRAMES)]
    bottle = image('cutscene', 'color_bottle.png')
    bottle_glow = image('title_pastel', 'bottle_glow.png')
    bg_gray = image('title_restore', 'background.png')
    bg_night = image('title_restore_night', 'background.png')
    dye_day = dye_frames('title_restore')
    dye_night = dye_frames('title_restore_night')
    inside_gray = image('cutscene_inside', 'background.png')
    dye_inside = dye_frames('cutscene_inside')
    fire = image('cutscene', 'fire.png')
    ice = image('cutscene', 'ice.png')
    man_img = image('cutscene', 'man.png')
    sleeper = image('cutscene', 'sleeper.png')
    carriers = {c: image('cutscene', f'carrier_{c}.png') for c in COLORS}
    seal_bg = image('cutscene', 'seal.png')
    black_bottle = image('cutscene', 'black_bottle.png')
    run_layers = {n: image('cutscene', f'run_{n}.png') for n in ('sky', 'far', 'mid', 'ground')}


def init():
    global cut, index, phase, t, typed, skipping
    load_images()
    cut = None
    index = 0
    phase = 'title'
    t = typed = 0.0
    skipping = False
    hide_cursor()


def finish():
    pass


def pause():
    pass


def resume():
    pass


def start_cut(i):
    global cut, index, phase, t, typed
    index = i
    cut = CUTS[i]()
    phase, t, typed = 'in', 0.0, 0.0


def line():
    return cut.lines[cut.step]


def advance():
    """다 안 써졌으면 마저 쓰고, 다 써졌으면 다음 문장 → 다음 컷."""
    global typed, phase, t
    if phase not in ('in', 'play') or cut is None:
        return
    if typed < len(line()):
        typed = len(line())
    elif cut.step < len(cut.lines) - 1:
        cut.next_step()
        typed = 0.0
    else:
        phase, t = 'out', 0.0


def skip():
    global skipping, phase, t
    if skipping:
        return
    skipping = True
    if phase == 'title':
        return      # 타이틀이 다 어두워지면 바로 끝낸다 (update)
    if phase != 'out':
        # 지금 어두워지는 정도에서 이어서 어두워진다
        t = 0.0 if phase == 'play' else FADE * (1 - min(1.0, t / FADE))
        phase = 'out'


def end():
    """본 것으로 적고 준비 화면으로 (준비 화면은 어둠 속에서 밝아지며 시작한다)."""
    if save_data.current is not None:
        save_data.current['intro_seen'] = True
        save_data.save_current()
    prepare_mode.preload()
    game_framework.reset_mode(prepare_mode)


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                skip()
            elif event.key in (SDLK_SPACE, SDLK_RETURN):
                advance()
        elif event.type == SDL_MOUSEMOTION:
            title_mode.move_mouse(title_mode.to_canvas(event))
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            advance()


def update():
    global phase, t, typed
    dt = game_framework.frame_time
    t += dt
    title_mode.trail.update()
    if phase == 'title':
        title_mode.update_ambient()
        if t >= FADE:
            end() if skipping else start_cut(0)
        return
    cut.update(dt)
    if phase == 'in' and t >= FADE:
        phase, t = 'play', 0.0
    if phase in ('in', 'play') and (cut.step > 0 or cut.t > FADE * 0.6):
        typed = min(len(line()), typed + dt * TYPE_SPEED)
    if phase == 'out' and t >= FADE:
        if skipping or index == len(CUTS) - 1:
            end()
        else:
            start_cut(index + 1)


def draw_dark(k):
    if k > 0:
        draw_alpha(fade, min(1.0, k), CX, H / 2, W, H)


def draw_caption():
    s = line()
    a = clamp01(cut.t / (FADE * 0.6)) if cut.step == 0 else 1.0
    draw_alpha(caption, 0.95 * a, CX, CAPTION_Y)
    if typed <= 0:
        return
    img = text.image(s, CAPTION_SIZE, INK)
    shown = int(img.w * typed / len(s)) if typed < len(s) else img.w
    if shown <= 0:
        return
    left = CX - img.w / 2
    img.clip_draw(0, 0, shown, img.h, left + shown / 2, CAPTION_Y + 2)
    if typed >= len(s):   # 다 써지면 오른쪽 끝에 잉크 방울이 콩콩 (눌러서 넘기기)
        bob = abs(math.sin(cut.st * 3.5 + typed)) * 6
        draw_alpha(next_mark, 0.9, CX + caption.w / 2 - 52, CAPTION_Y - 14 + bob, 26, 26)


def draw_hint():
    msg = 'ESC  건너뛰기'
    text.draw(msg, W - 22, H - 27, 24, (40, 32, 56), 'r', alpha=0.45)
    text.draw(msg, W - 23, H - 26, 24, HINT, 'r', alpha=0.9)


def draw():
    clear_canvas()
    if phase == 'title':
        title_mode.draw_scene()
        draw_dark(t / FADE)
    else:
        cut.draw()
        draw_caption()
        draw_hint()
        draw_dark({'in': 1 - t / FADE, 'play': 0.0, 'out': t / FADE}[phase])
    title_mode.draw_cursor()
    update_canvas()
