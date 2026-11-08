"""타이틀·설정 화면 '잉크' 버전 이미지 생성 — 펜으로 그린 흑백 동화 세상이 잉크로 물든다.

처음엔 수채화 종이 위 펜 선으로만 그린 흑백 세상(동굴 있는 언덕, 동글동글한 나무, 해, 구름, 꽃).
잉크통에서 빨·초·파 잉크가 피어오르고, 수채 물감이 번져 나가며 그림에 색이 칠해진다(dye_*.png).
흑백 동굴만은 색이 들지 않는다 (PRD: 색을 빼앗긴 세상 → 잉크로 다시 물들인다).

사람이 수채화 종이에 펜으로 선을 긋고 수채 잉크로 칠한 그림처럼: 종이 결, 삐뚤한 펜 선과 해칭,
번진 가장자리가 진한 수채 얼룩, 잉크 구름 위 펜 소용돌이, 손글씨.

빛이 비치는 맑은 물속. 가운데 잉크통에서 빨·초·파 잉크가 구름처럼 뭉게뭉게 피어오르고,
시간이 지나면 그 잉크 구름이 물 전체로 번져 화면을 물들인다(dye_*.png 단계별 층).
아래쪽엔 안개 낀 언덕·나무 실루엣이 비친다.
- 로고: 짙은 잉크빛 만년필 필기체(Great Vibes), 'k' 끝에서 잉크 한 방울이 떨어진다
- 모래시계: 맑은 유리 (몽환 버전과 같은 그림)
- 버튼·설정 창: 맑은 유리 + 잉크 색 선·글씨

실행:  python tools/gen_title_ink.py
결과:  image/title_ink/*.png, image/settings_ink/*.png  (파일 이름은 다른 그림체와 같다)
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, bezier, ellipse_points  # noqa: E402
import gen_title_images as dreamy  # noqa: E402
from gen_title_images import (W, H, LIGHT, WHITE, ROOT, PANEL_W, PANEL_H, SETTING_ROWS, UI_FONT,  # noqa: E402
                              save, poly_mask, densify, lighter, darker, _rounded, _put)
from gen_title_doodle import empty, sketch_line, doodle_pill  # noqa: E402
from sketch import paper  # noqa: E402

TITLE, SETTINGS = 'title_ink', 'settings_ink'
SCRIPT_FONT = os.path.join(ROOT, 'fonts', 'GreatVibes-Regular.ttf')  # 만년필 필기체 (OFL)
PEN_FONT = os.path.join(ROOT, 'fonts', 'NanumPenScript-Regular.ttf')  # 손글씨 펜 (OFL)
INK = (28, 34, 72)             # 짙은 잉크빛 (블루블랙)
INK_SOFT = (96, 108, 150)
PEN = (44, 50, 86)             # 펜 선
INKS = {'red': (230, 72, 96), 'green': (40, 176, 140), 'blue': (52, 112, 232),
        'violet': (150, 90, 220), 'gold': (240, 180, 70)}
DYE_FRAMES = 12
DYE_SIZE = (640, 360)


def ui_font(size):
    return ImageFont.truetype(PEN_FONT, int(size * 1.35))  # 손글씨 펜은 글자가 작아 키운다


# ================================================================ 잉크 구름
def _flow(x, y, seed):
    return (math.sin(x * 0.013 + seed) * 1.3 + math.sin(y * 0.019 - seed * 0.7) * 1.1 +
            math.sin((x + y) * 0.008 + seed * 1.9) * 0.9)


def ink_cloud(size, ss, sources, seed, puffs=220, filaments=120, scale=1.0):
    """물속 잉크 구름 (RGBA). sources: [(x, y, color, 퍼지는 반경, 오르는 높이)].
    - 크고 흐린 덩어리 + 작고 또렷한 뭉게(가장자리 진함) 를 겹쳐 부피감을 내고
    - 흐름장을 따라가는 가는 실(필라멘트)로 잉크가 풀리는 결을 더한다."""
    w, h = size
    sh = Sheet(w, h, seed=seed, ss=ss)
    r = random.Random(seed)
    for sx, sy, col, spread, rise in sources:
        for k in range(puffs):
            t = r.random() ** 0.8
            ang = r.uniform(0, 2 * math.pi)
            x = sx + math.cos(ang) * spread * t * r.uniform(0.3, 1.0) + math.sin(t * 5 + seed) * 40 * scale
            y = sy - rise * t + math.sin(ang) * spread * 0.5 * t
            rad = (10 + 70 * t * r.uniform(0.4, 1.0)) * scale
            big = r.random() < 0.35
            sh.wash(x, y, rad * (1.6 if big else 1.0), rad * (1.3 if big else 0.85), col,
                    alpha=r.randint(14, 30) if big else r.randint(26, 60), layers=1,
                    edge=0.2 if big else 1.6, blur=(rad * 0.25 if big else 1.6), wobble=0.3)
        lay = Sheet(w, h, seed=seed + 1, ss=ss)
        for _ in range(filaments):
            x, y = sx + r.gauss(0, 14 * scale), sy + r.gauss(0, 8 * scale)
            vx, vy = r.uniform(-1.4, 1.4) * scale, -r.uniform(1.2, 2.4) * scale
            off = r.uniform(-160, 160)
            pts = [(x, y)]
            for _k in range(int(rise / 2.4 / scale * r.uniform(0.5, 1.1))):
                a = _flow(x + off, y - off * 0.5, seed)
                vx = vx * 0.92 + math.cos(a) * 0.55 * scale
                vy = vy * 0.92 + (math.sin(a) * 0.2 - 0.2) * scale
                x, y = x + vx, y + vy
                pts.append((x, y))
            if len(pts) > 3:
                lay.stroke(pts, r.uniform(0.6, 1.8) * scale, col, r.randint(24, 50), amp=0.3)
        lay.img = lay.img.filter(ImageFilter.GaussianBlur(1.6 * ss))
        sh.img.alpha_composite(lay.img)
    return sh.img


# ================================================================ 손그림 도구
_GRAIN = None


def grain(size):
    """수채화 종이 결 (0.75~1.0 배율) — 잉크가 종이 오목한 곳에 고이는 느낌."""
    global _GRAIN
    if _GRAIN is None or _GRAIN.shape[::-1] != size:
        g = np.asarray(paper(size[0], size[1], seed=91).convert('L'), np.float32)
        g = (g - g.min()) / max(1, g.max() - g.min())
        rng = np.random.default_rng(92)
        tooth = np.asarray(Image.fromarray((rng.random((size[1] // 2 + 1, size[0] // 2 + 1)) * 255).astype(np.uint8))
                           .resize(size, Image.BICUBIC), np.float32) / 255
        _GRAIN = 0.72 + 0.18 * g + 0.1 * tooth
    return _GRAIN


def granulate(img):
    """RGBA 의 알파에 종이 결을 곱한다."""
    a = np.asarray(img.split()[3], np.float32) * grain(img.size)
    img.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    return img


def watercolor(sh, pts, color, alpha=200, edge=1.4, body=0.62):
    """수채 칠: 가장자리에 물감이 고여 진하고 안쪽은 옅다 + 종이 결."""
    lay = Sheet(sh.w, sh.h, seed=sh.rng.randint(0, 9999), ss=sh.ss)
    lay.fill_poly(pts, color, 255)
    a = np.asarray(lay.img.split()[3].filter(ImageFilter.GaussianBlur(1.2 * sh.ss)), np.float32) / 255
    soft = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6 * sh.ss)),
                      np.float32) / 255
    a = a * body + np.clip(a - soft, 0, 1) * edge
    a *= grain(lay.img.size)
    lay.img.putalpha(Image.fromarray(np.clip(a * alpha, 0, 255).astype(np.uint8)))
    sh.img.alpha_composite(lay.img)


def pen(sh, pts, width=1.8, color=PEN, alpha=230):
    sketch_line(sh, pts, color, width, alpha, amp=1.0)


def hatch_inside(sh, pts, x0, x1, gap=6, angle=-1.0, color=PEN, alpha=120, width=1.0):
    """모양 안쪽 x0~x1 범위에만 빗금 (그늘)."""
    m = np.asarray(poly_mask((sh.w, sh.h), pts)) > 0
    ys = [p[1] for p in pts]
    sh.hatch(x0, min(ys), x1, max(ys), gap=gap, angle=angle, width=width, color=color, alpha=alpha,
             clip=lambda px, py: 0 <= int(py) < sh.h and 0 <= int(px) < sh.w and m[int(py), int(px)])


def swirl(sh, x, y, r, color, alpha=170, width=1.4, turns=1.3, seed=0):
    """잉크 구름 위 펜 소용돌이."""
    rr = random.Random(seed)
    ph = rr.uniform(0, 6)
    pts = []
    n = 50
    for k in range(n + 1):
        t = k / n
        a = ph + t * turns * 2 * math.pi
        rad = r * (0.25 + 0.75 * t)
        pts.append((x + math.cos(a) * rad, y - t * r * 0.8 + math.sin(a) * rad * 0.6))
    sh.stroke(pts, width, color, alpha, amp=0.6)


# ================================================================ 장면 (흑백 펜 그림 + 물들 색)
# 장면의 모양을 한 곳에 정의해 두고, 흑백 바탕(펜 선)과 물들이기 색 층이 같은 모양을 쓴다.
SUN = (1070, 128, 50)
CLOUDS = ((230, 150, 230, 38), (1000, 270, 180, 30), (90, 300, 140, 24), (1190, 330, 130, 22))


def _ridge(y0, amp1, f1, amp2, f2, ph):
    return [(x, y0 - amp1 * math.sin(x / f1 + ph) - amp2 * math.sin(x / f2 + ph * 2)) for x in range(-20, W + 41, 16)]


MOUNTAINS = [(-20, 430), (110, 360), (220, 400), (330, 340), (470, 410), (600, 430), (760, 420), (880, 350),
             (990, 400), (1110, 330), (1230, 390), (1300, 380)]
BACK_HILL = _ridge(486, 22, 150, 10, 57, 0.4)
FRONT_LEFT = [(-20, 540), (80, 530), (180, 546), (280, 580), (360, 640), (400, 730)]
FRONT_RIGHT = [(1300, 548), (1200, 536), (1100, 552), (1000, 590), (930, 650), (900, 730)]
MOUND = bezier((330, 730), (420, 610), (540, 604), (640, 606), 30) + bezier((640, 606), (740, 608), (860, 612), (950, 730), 30)[1:]
CAVE = (250, 486)  # 흑백 동굴 (뒤 언덕)
TREES = [  # (x, 땅 y, 높이, 수관 반지름, 앞뒤: 0 뒤 언덕 / 1 앞)
    (60, 492, 120, 40, 0), (150, 494, 96, 32, 0), (420, 500, 104, 34, 0), (860, 494, 110, 36, 0),
    (960, 488, 128, 42, 0), (1060, 492, 100, 32, 0), (1180, 488, 120, 40, 0),
    (90, 540, 190, 62, 1), (210, 552, 150, 48, 1), (1210, 546, 196, 64, 1), (1090, 556, 150, 48, 1)]
FLOWERS = [(x, y) for x, y in ((460, 640), (520, 628), (585, 622), (700, 624), (760, 630), (820, 642), (60, 620),
                               (150, 650), (250, 640), (1050, 640), (1150, 620), (1240, 660), (490, 690), (800, 690))]


def tree_shape(x, ground, height, r):
    cy = ground - height + r
    crown = []
    bumps = 7
    for k in range(73):
        a = 2 * math.pi * k / 72
        rr = r * (0.9 + 0.12 * abs(math.sin(a * bumps / 2)))
        crown.append((x + math.cos(a) * rr, cy + math.sin(a) * rr * 0.9))
    trunk = [(x - 6, ground), (x - 4, cy + r * 0.6), (x + 4, cy + r * 0.6), (x + 7, ground)]
    return crown, trunk, cy


def cloud_shape(x, y, w, h):
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    n = max(3, int(w / 45))
    for k in range(n):
        bx = x - w / 2 + w * (k + 0.5) / n
        br = h * (0.6 + 0.4 * math.sin(math.pi * (k + 0.5) / n))
        d.ellipse((bx - br, y - br * 1.3, bx + br, y + br * 0.7), fill=255)
    d.rectangle((x - w / 2, y - h * 0.2, x + w / 2, y + h * 0.4), fill=255)
    return m


def top_line(mask, x0, x1, step=3):
    arr = np.asarray(mask) > 100
    out = []
    for px in range(max(0, int(x0)), min(W, int(x1)), step):
        col = arr[:, px]
        if col.any():
            out.append((px, int(col.argmax()) + 1))
    return out


def close(ridge):
    return ridge + [(ridge[-1][0], H + 20), (ridge[0][0], H + 20)]


GRAY = (206, 204, 210)   # 흑백 세상의 옅은 회색 칠
PEN_DARK = (40, 40, 52)


def background():
    """흑백 동화 세상: 수채화 종이 위에 펜 선 + 옅은 회색 칠 + 빗금. 색은 물들이기 층이 입힌다."""
    base = Image.new('RGBA', (W, H), (248, 245, 238, 255))
    paper_rgb = np.asarray(paper(W, H, seed=93).convert('RGB'), np.float32) / 247.0
    arr = np.asarray(base, np.float32)
    arr[..., :3] *= 0.86 + 0.14 * paper_rgb
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    sh = Sheet(W, H, seed=72)
    rng = sh.rng

    # 해 (선만)
    sx, sy, sr = SUN
    pen(sh, ellipse_points(sx, sy, sr, sr, 40, 0, 2 * math.pi * 1.05), 2.2, PEN_DARK, 230)
    for k in range(12):
        a = k * 2 * math.pi / 12
        pen(sh, [(sx + math.cos(a) * (sr + 12), sy + math.sin(a) * (sr + 12)),
                 (sx + math.cos(a) * (sr + 26), sy + math.sin(a) * (sr + 26))], 1.8, PEN_DARK, 220)
    # 구름
    for x, y, w, h in CLOUDS:
        m = cloud_shape(x, y, w, h)
        pen(sh, top_line(m, x - w / 2 - h, x + w / 2 + h), 1.8, PEN_DARK, 210)
        pen(sh, [(x - w / 2 + 10, y + h * 0.4), (x + w / 2 - 10, y + h * 0.4)], 1.5, PEN_DARK, 170)
    # 먼 산 (옅은 선 + 빗금)
    mt = densify(MOUNTAINS, 10)
    watercolor(sh, close(mt), (226, 224, 230), 200, edge=1.0)
    pen(sh, mt, 1.6, (110, 110, 124), 200)
    for (x0, y0), (x1, y1) in zip(MOUNTAINS, MOUNTAINS[1:]):
        if y1 > y0:  # 내려가는 쪽 비탈에 빗금
            hatch_inside(sh, close(mt), x0, x1, gap=7, angle=-0.7, color=(120, 120, 134), alpha=90)
    # 뒤 언덕 + 동굴 + 뒤 나무
    watercolor(sh, close(BACK_HILL), GRAY, 230)
    pen(sh, BACK_HILL, 2.0, PEN_DARK, 230)
    cx_, cy_ = CAVE
    arch = bezier((cx_ - 70, cy_ + 6), (cx_ - 76, cy_ - 70), (cx_ + 76, cy_ - 70), (cx_ + 70, cy_ + 6), 30)
    rock = bezier((cx_ - 110, cy_ + 8), (cx_ - 120, cy_ - 120), (cx_ + 120, cy_ - 126), (cx_ + 112, cy_ + 8), 40)
    watercolor(sh, rock + [(cx_ + 112, cy_ + 10), (cx_ - 110, cy_ + 10)], (196, 194, 202), 240)
    watercolor(sh, arch + [(cx_ - 70, cy_ + 8)], (60, 58, 70), 245, edge=0.8)
    hatch_inside(sh, arch, cx_ - 70, cx_ + 70, gap=4, angle=-0.9, color=(20, 20, 28), alpha=160)
    pen(sh, rock, 2.2, PEN_DARK, 235)
    pen(sh, arch, 2.4, PEN_DARK, 240)
    for t in TREES:
        if t[4] == 0:
            draw_tree(sh, *t[:4])
    sh.wash(W / 2, 500, W * 0.7, 30, (250, 248, 244), alpha=80, layers=2, edge=0.0, blur=14)
    # 앞 언덕 + 가운데 꽃 언덕 + 앞 나무 + 꽃·풀
    for ridge in (FRONT_LEFT, FRONT_RIGHT):
        rd = densify(ridge, 10)
        watercolor(sh, close(rd), (214, 212, 218), 240)
        pen(sh, rd, 2.2, PEN_DARK, 240)
    watercolor(sh, close(MOUND), (226, 224, 228), 240)
    pen(sh, MOUND, 2.2, PEN_DARK, 240)
    for t in TREES:
        if t[4] == 1:
            draw_tree(sh, *t[:4])
    for x, y in FLOWERS:
        sh.stroke([(x, y + 14), (x, y + 3)], 1.4, PEN_DARK, 220, amp=0.3)
        for k in range(5):
            a = k * 2 * math.pi / 5 + 0.3
            sh.ellipse(x + math.cos(a) * 4, y + math.sin(a) * 4, 3, 3, 1.0, PEN_DARK, 220, amp=0.2)
    for _ in range(40):
        x, y = rng.uniform(0, W), rng.uniform(560, 715)
        sh.stroke([(x - 4, y - 7), (x, y), (x + 4, y - 8)], 1.3, PEN_DARK, 180, amp=0.3)
    # 잉크통에서 막 피어오르는 잉크 (처음부터 보이는 유일한 색)
    lx, ly = LIGHT
    cloud = ink_cloud((W, H), sh.ss, [(lx - 30, ly + 10, INKS['red'], 40, 150), (lx + 30, ly + 10, INKS['blue'], 40, 160),
                                      (lx, ly - 10, INKS['green'], 34, 190)], seed=73, puffs=50, filaments=10)
    sh.img.alpha_composite(granulate(cloud))
    sh.wash(lx, ly, 140, 130, (255, 253, 246), alpha=150, layers=3, edge=0.0, blur=24)
    base.alpha_composite(sh.result())
    return base.convert('RGB')


def draw_tree(sh, x, ground, height, r):
    crown, trunk, cy = tree_shape(x, ground, height, r)
    watercolor(sh, trunk, (170, 168, 176), 240)
    pen(sh, trunk[:2], 1.8, PEN_DARK, 230)
    pen(sh, trunk[2:], 1.8, PEN_DARK, 230)
    watercolor(sh, crown, (196, 194, 202), 240)
    hatch_inside(sh, crown, x + r * 0.15, x + r, gap=5, angle=-1.0, color=PEN_DARK, alpha=110)
    for _ in range(4):  # 잎 동글 무늬
        a, d = sh.rng.uniform(0, 6.3), r * sh.rng.uniform(0.2, 0.6)
        sh.stroke(ellipse_points(x + math.cos(a) * d, cy + math.sin(a) * d * 0.8, 7, 5, 10, sh.rng.uniform(0, 6), 3.6),
                  1.3, PEN_DARK, 170, amp=0.3)
    pen(sh, crown, 2.0, PEN_DARK, 240)


def color_layer():
    """물들이기 색: 같은 모양들을 수채 물감 색으로 칠한 층 (선 밖으로 살짝 번진다)."""
    sh = Sheet(W, H, seed=76, ss=1)

    def wc(pts, col, a=200):
        watercolor(sh, [(x + sh.rng.uniform(-3, 3), y + sh.rng.uniform(-3, 3)) for x, y in pts], col, a, edge=1.3)
    # 하늘: 위는 하늘색, 아래로 갈수록 복숭아빛
    sky = Sheet(W, H, seed=77, ss=1)
    ys = np.linspace(0, 1, H)[:, None]
    for (y0, y1, col) in ((0, 0.35, (126, 180, 236)), (0.3, 0.62, (186, 196, 240)), (0.55, 0.75, (250, 204, 196))):
        k = np.clip(1 - np.abs((ys - (y0 + y1) / 2) / ((y1 - y0) / 2 + 1e-6)), 0, 1) ** 0.7
        lay = np.zeros((H, W, 4), np.uint8)
        lay[..., :3] = col
        lay[..., 3] = (np.repeat(k, W, axis=1) * 150).astype(np.uint8)
        sky.img.alpha_composite(Image.fromarray(lay, 'RGBA'))
    sh.img.alpha_composite(granulate(sky.img))
    sx, sy, sr = SUN
    wc(ellipse_points(sx, sy, sr + 4, sr + 4, 40), (250, 200, 80), 235)
    sh.wash(sx, sy, sr * 2.4, sr * 2.4, (255, 220, 150), alpha=70, layers=2, edge=0.0, blur=20)
    for x, y, w, h in CLOUDS:
        m = cloud_shape(x, y, w, h)
        lay = Image.new('RGBA', (W, H), (255, 214, 230, 0))
        lay.putalpha(m.filter(ImageFilter.GaussianBlur(3)).point(lambda v: v * 150 // 255))
        sh.img.alpha_composite(granulate(lay))
    wc(close(densify(MOUNTAINS, 10)), (176, 164, 222), 200)
    wc(close(BACK_HILL), (150, 202, 132), 220)
    cx_, cy_ = CAVE
    rock = bezier((cx_ - 110, cy_ + 8), (cx_ - 120, cy_ - 120), (cx_ + 120, cy_ - 126), (cx_ + 112, cy_ + 8), 40)
    wc(rock + [(cx_ + 112, cy_ + 10), (cx_ - 110, cy_ + 10)], (178, 164, 150), 200)
    for ridge in (FRONT_LEFT, FRONT_RIGHT):
        wc(close(densify(ridge, 10)), (110, 182, 110), 230)
    wc(close(MOUND), (168, 214, 132), 230)
    for x, ground, height, r, _ in TREES:
        crown, trunk, _cy = tree_shape(x, ground, height, r)
        wc(trunk, (170, 120, 90), 230)
        wc(crown, (84, 168, 96) if (x // 10) % 2 else (120, 186, 90), 230)
    for k, (x, y) in enumerate(FLOWERS):
        wc(ellipse_points(x, y, 8, 8, 16), (INKS['red'], (250, 200, 80), INKS['violet'], (255, 170, 200))[k % 4], 240)
    # 잉크통 둘레 빨·초·파 잉크 구름
    lx, ly = LIGHT
    cloud = ink_cloud((W, H), 1, [(lx - 110, ly - 40, INKS['red'], 90, 140), (lx + 120, ly - 50, INKS['blue'], 90, 150),
                                  (lx, ly - 90, INKS['green'], 80, 160)], seed=74, puffs=60, filaments=0, scale=0.8)
    a = cloud.split()[3].point(lambda v: v * 75 // 100)
    cloud.putalpha(a)
    sh.img.alpha_composite(granulate(cloud))
    # 흑백 동굴만은 색이 들지 않는다 (색을 빼앗긴 곳)
    arch = bezier((cx_ - 70, cy_ + 6), (cx_ - 76, cy_ - 70), (cx_ + 76, cy_ - 70), (cx_ + 70, cy_ + 6), 30)
    hole = poly_mask((W, H), arch + [(cx_ - 70, cy_ + 8)]).filter(ImageFilter.GaussianBlur(2))
    a = ImageChops.subtract(sh.img.split()[3], hole)
    sh.img.putalpha(a)
    return sh.img


def dye_frames():
    """물들이기: 잉크통에서부터 수채 물감이 번져 나가는 단계별 색 층 (점점 넓어진다)."""
    w, h = DYE_SIZE
    col = np.asarray(color_layer().resize((w, h), Image.LANCZOS), np.float32)
    sx, sy = w / W, h / H
    lx, ly = LIGHT[0] * sx, LIGHT[1] * sy
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(78)
    noise = np.asarray(Image.fromarray((rng.random((h // 16 + 1, w // 16 + 1)) * 255).astype(np.uint8))
                       .resize((w, h), Image.BICUBIC), np.float32) / 255
    dist = np.hypot(xx - lx, (yy - ly) * 1.2) * (0.75 + 0.5 * noise)
    far = dist.max() * 1.02
    frames = []
    for i in range(DYE_FRAMES):
        r = far * ((i + 1) / DYE_FRAMES) ** 1.1
        m = np.clip((r - dist) / (14 + 30 * i / DYE_FRAMES), 0, 1)
        rim = np.exp(-((dist - r) / 6) ** 2) * (i < DYE_FRAMES - 1)  # 번지는 끝의 진한 물 자국
        out = col.copy()
        out[..., 3] = np.clip(out[..., 3] * m + out[..., 3] * rim * 0.6, 0, 255)
        out[..., :3] *= (1 - rim[..., None] * 0.25)
        frames.append(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA'))
    return frames


# ================================================================ 로고
def logo():
    """만년필 필기체 로고: 'what are you do' 바로 아래 큰 'Ink', 뒤로 은은한 잉크 구름,
    'k' 끝에서 떨어지는 잉크 방울과 물결."""
    lw, lh = 620, 300
    sh = Sheet(lw, lh, seed=1301)
    ss = sh.ss
    cx = lw / 2
    cloud = ink_cloud((lw, lh), ss, [(cx - 90, 220, INKS['red'], 60, 70), (cx + 10, 210, INKS['green'], 60, 70),
                                     (cx + 110, 220, INKS['blue'], 60, 70)], seed=1302, puffs=40, filaments=6,
                      scale=0.7)
    a = cloud.split()[3].point(lambda v: v * 70 // 100)
    cloud.putalpha(a)
    sh.img.alpha_composite(cloud)
    big = sh.text_mask('Ink', ImageFont.truetype(SCRIPT_FONT, 210), cx - 6, 248, anchor='ms')
    # 'what are you do' 는 'I' 고리 꼭대기 바로 위에 붙인다 (글자끼리 겹치지 않게)
    rows = np.where((np.asarray(big) > 128).any(axis=1))[0]
    small = sh.text_mask('what are you do', ImageFont.truetype(SCRIPT_FONT, 54), cx - 4, rows[0] / ss - 6,
                         anchor='ms')
    union = ImageChops.lighter(small, big)

    def lay(mask, color, alpha=255):
        if alpha < 255:
            mask = mask.point(lambda v: v * alpha // 255)
        l_ = Image.new('RGBA', sh.img.size, tuple(color) + (0,))
        l_.putalpha(mask)
        sh.img.alpha_composite(l_)
    lay(union.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(5 * ss)), WHITE, 230)
    lay(union.filter(ImageFilter.GaussianBlur(2 * ss)), INK, 90)  # 잉크가 살짝 번진 자국
    lay(union, INK)
    # 'k' 끝에서 떨어지는 방울
    arr = np.asarray(big) > 128
    cols = np.where(arr.any(axis=0))[0]
    kx = cols[-1] / ss - 12
    kcol = np.where(arr[:, int(kx * ss)])[0]
    ky = (kcol[-1] / ss if len(kcol) else 230) + 4
    sh.stroke([(kx, ky - 4), (kx, ky + 6)], 2.6, INK, 230, amp=0.1, taper=False)
    drop = ellipse_points(kx, ky + 22, 5, 6.5, 16)
    sh.fill_poly(drop + [(kx, ky + 8)], INK, 255)
    sh.wash(kx - 1.6, ky + 20, 1.4, 1.8, WHITE, alpha=230, layers=1, blur=0.3)
    for rx, a_ in ((16, 150), (28, 90)):
        sh.stroke(ellipse_points(kx, ky + 40, rx, rx * 0.22, 30), 1.4, INK_SOFT, a_, amp=0.6, taper=False)
    # 펜촉으로 그은 밑줄 스와시 (굵기가 변한다)
    sw = bezier((cx - 200, 268), (cx - 60, 252), (cx + 60, 284), (cx + 150, 262), 420)
    for k, (x_, y_) in enumerate(sw):
        t = k / (len(sw) - 1)
        rr = 0.6 + 2.6 * math.sin(math.pi * t) ** 1.5
        sh.wash(x_, y_ + sh.rng.uniform(-0.3, 0.3), rr, rr * 0.7, INK, alpha=240, layers=1, edge=0.2, blur=0.3)
    for x_, y_ in ((cx - 230, 140), (cx + 190, 120)):  # 잉크 튐
        for _ in range(6):
            a, d = sh.rng.uniform(0, 6.3), sh.rng.uniform(3, 18)
            rr = sh.rng.uniform(0.8, 2.6)
            sh.wash(x_ + math.cos(a) * d, y_ + math.sin(a) * d, rr, rr, INK, alpha=230, layers=1, edge=0.8, blur=0.3)
    return sh.result(crop=True, margin=10)


# ================================================================ 버튼 · 설정
def ink_bottle():
    """펜과 수채 잉크로 그린 모래시계: 펜 선 유리(두 번 그은 선) + 빗금 그늘,
    위 칸은 수채로 칠한 검정 잉크와 펜 별, 아래 칸은 번져 섞인 빨·초·파."""
    bw, bh = 230, 340
    cx = bw / 2
    sh = Sheet(bw, bh, seed=1501)
    size = (bw, bh)
    top, bottom = 58, 282
    neck = (top + bottom) / 2
    left = bezier((cx - 74, top), (cx - 84, top + 80), (cx - 13, neck - 30), (cx - 8, neck), 30) + \
        bezier((cx - 8, neck), (cx - 13, neck + 30), (cx - 84, bottom - 80), (cx - 74, bottom), 30)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner_pts = left + right[::-1]
    inner = poly_mask(size, inner_pts)
    glass = Sheet(bw, bh, seed=1502)
    glass.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (250, 251, 255), 200)
    watercolor(glass, [(0, top + 30), (bw, top + 27), (bw, neck + 4), (0, neck + 4)], (20, 20, 32), 255, edge=0.6,
               body=1.0)  # 검정 잉크는 진하게
    for sx_, sy_, r_ in ((cx + 18, top + 54, 5), (cx - 24, top + 72, 3.5)):
        glass.stroke([(sx_, sy_ - r_), (sx_, sy_ + r_)], 1.4, WHITE, 255, amp=0.2)
        glass.stroke([(sx_ - r_, sy_), (sx_ + r_, sy_)], 1.4, WHITE, 255, amp=0.2)
    glass.stroke([(cx, neck), (cx + 1, neck + 30), (cx, bottom - 58)], 2.0, (30, 30, 46), 230, amp=0.4)
    for y0, y1, key in ((bottom - 64, bottom - 40, 'red'), (bottom - 44, bottom - 19, 'green'), (bottom - 23, bh, 'blue')):
        watercolor(glass, [(0, y0), (bw, y0 + 3), (bw, y1), (0, y1)], INKS[key], 245, edge=1.1)
    sh.masked(glass, inner)
    hatch_inside(sh, inner_pts, cx + 30, cx + 80, gap=5, angle=-1.1, alpha=110)
    pen(sh, left, 2.2, PEN, 245)
    pen(sh, right, 2.2, PEN, 245)
    sh.stroke([(cx - 54, top + 18), (cx - 62, top + 52), (cx - 42, top + 86)], 3.0, WHITE, 240, amp=0.5)
    for x in (cx - 90, cx + 90):
        pen(sh, [(x, top - 6), (x + 1, bottom + 6)], 2.0, PEN, 235)
        pen(sh, [(x + 5, top - 6), (x + 6, bottom + 6)], 1.4, PEN, 200)
    for y in (top - 12, bottom + 12):
        disc = ellipse_points(cx, y, 104, 13, 40)
        watercolor(sh, disc, (196, 174, 230), 230, edge=1.2)
        hatch_inside(sh, disc, cx + 20, cx + 104, gap=5, angle=-0.9, alpha=120)
        pen(sh, disc, 2.0, PEN, 240)
    sh.add_glow((255, 252, 244), blur=8, strength=1.2)
    return sh.result(crop=True, margin=12)


def button(label, color, seed, hover, size=(260, 84)):
    """펜으로 그린 알약 버튼 + 손글씨. hover 면 안쪽에 원소 색 수채 잉크가 번진다."""
    bw, bh = size
    sh = Sheet(bw, bh, seed=seed)
    x0, y0, x1, y1 = 22, 20, bw - 22, bh - 20
    pill = doodle_pill(x0, y0, x1, y1, sh.rng)
    sh.fill_poly(pill, (252, 252, 255), 215)
    if hover:
        watercolor(sh, [(x + sh.rng.uniform(-2, 2), y + sh.rng.uniform(-2, 2)) for x, y in pill], lighter(color, 40),
                   220, edge=1.4)
    pen(sh, pill, 2.0, PEN, 245)
    sh.ink_text(label, ui_font(28), bw / 2, bh / 2 + 1, PEN, 255, anchor='mm')
    if hover:
        for _ in range(5):
            a, d = sh.rng.uniform(0, 6.3), sh.rng.uniform(2, 12)
            sh.wash(x1 - 6 + math.cos(a) * d, y0 + 2 + math.sin(a) * d, 1.8, 1.8, color, alpha=230, layers=1,
                    edge=0.8, blur=0.3)
    sh.add_glow(WHITE, blur=5, strength=1.0 if hover else 0.6)
    return sh.result()


def settings_panel():
    """맑은 유리 창: 모서리에 잉크 구름이 번져 있고, 잉크빛 글씨."""
    sh = Sheet(PANEL_W, PANEL_H, seed=1401)
    ss = sh.ss
    size = (PANEL_W, PANEL_H)
    box = (24, 24, PANEL_W - 24, PANEL_H - 24)
    outer = _rounded(size, box, 28, ss)
    inner = _rounded(size, (box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2), 26, ss)
    _put(sh, outer.filter(ImageFilter.GaussianBlur(10 * ss)), INK_SOFT, 80)
    _put(sh, inner, (250, 252, 255), 235)
    c = ink_cloud(size, ss, [(70, PANEL_H - 40, INKS['red'], 70, 90), (PANEL_W - 70, 70, INKS['blue'], 70, 60),
                             (PANEL_W - 90, PANEL_H - 50, INKS['green'], 60, 80)], seed=1402, puffs=40, filaments=20,
                  scale=0.6)
    r_, g_, b_, a_ = c.split()
    a_ = ImageChops.multiply(a_.point(lambda v: v * 55 // 100), inner)
    sh.img.alpha_composite(Image.merge('RGBA', (r_, g_, b_, a_)))
    edge_pts = doodle_pill(box[0], box[1], box[2], box[3], sh.rng) if False else \
        [(box[0] + 20, box[1]), (box[2] - 20, box[1] + 2), (box[2], box[1] + 20), (box[2] + 1, box[3] - 20),
         (box[2] - 20, box[3]), (box[0] + 20, box[3] - 1), (box[0], box[3] - 20), (box[0] - 1, box[1] + 20),
         (box[0] + 20, box[1])]
    pen(sh, densify(edge_pts, 8), 2.2, PEN, 240)
    sh.ink_text('설정', ui_font(40), PANEL_W / 2, 66, PEN, 255, anchor='mm')
    sw = bezier((PANEL_W / 2 - 52, 96), (PANEL_W / 2 - 10, 90), (PANEL_W / 2 + 20, 100), (PANEL_W / 2 + 56, 92), 140)
    for k, (x_, y_) in enumerate(sw):
        rr = 0.5 + 1.8 * math.sin(math.pi * k / (len(sw) - 1))
        sh.wash(x_, y_, rr, rr * 0.7, PEN, alpha=230, layers=1, edge=0.2, blur=0.3)
    for i, label in enumerate(SETTING_ROWS):
        y = 150 + i * 70
        sh.ink_text(label, ui_font(28), 78, y, PEN, 255, anchor='lm')
        sh.fill_poly(ellipse_points(60, y, 4, 4, 12), list(INKS.values())[i], 255)
    return sh.result()


def slider_track(filled=False):
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=1411 if filled else 1412)
    ss = sh.ss
    if filled:
        bar = _rounded((tw, th), (6, 14, tw - 6, th - 14), 4, ss)
        grad = dreamy._gradient_bar(tw, th, ss, [INKS['red'], INKS['violet'], INKS['blue'], INKS['green']])
        g2 = grad.copy()
        g2.putalpha(bar.filter(ImageFilter.GaussianBlur(4 * ss)).point(lambda v: v * 150 // 255))
        grad.putalpha(bar)
        sh.img.alpha_composite(g2)
        sh.img.alpha_composite(grad)
    else:
        pen(sh, [(8, 18), (tw / 2, 17), (tw - 8, 19)], 1.8, PEN, 230)
        for x in (8, tw - 8):
            sh.stroke([(x, 11), (x, 25)], 1.6, PEN, 220, amp=0.3)
    return sh.result()


def slider_knob():
    """잉크 방울 손잡이."""
    s_ = 44
    sh = Sheet(s_, s_, seed=1413)
    c = s_ / 2
    sh.fill_poly(ellipse_points(c, c + 2, 10, 10, 24) + [(c, c - 14)], INK, 255)
    sh.wash(c - 3, c, 2.4, 3, WHITE, alpha=230, layers=1, blur=0.3)
    sh.add_glow(WHITE, blur=3, strength=1.2)
    return sh.result()


def toggle(on):
    """켜짐: 잉크가 번진 동그라미 / 꺼짐: 빈 동그라미."""
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=1421 if on else 1422)
    cx_, cy_ = 32, th / 2
    if on:
        c = ink_cloud((tw, th), sh.ss, [(cx_, cy_ + 4, INKS['blue'], 12, 8)], seed=1423, puffs=20, filaments=8,
                      scale=0.25)
        sh.img.alpha_composite(c)
        sh.fill_poly(ellipse_points(cx_, cy_, 9, 9, 20), INKS['blue'], 255)
    pen(sh, ellipse_points(cx_, cy_, 14, 14, 30, 0, 2 * math.pi * 1.06), 1.8, PEN, 240)
    sh.ink_text('켜짐' if on else '꺼짐', ui_font(21), 88, th / 2, PEN if on else INK_SOFT, 255, anchor='mm')
    return sh.result()


def bubble(tint, seed):
    """펜으로 그린 물속 기포: 삐뚤한 동그라미 + 옅은 수채 + 반사광."""
    sz = 72
    sh = Sheet(sz, sz, seed=seed)
    c, r = sz / 2, 26
    body = ellipse_points(c, c, r, r, 36)
    watercolor(sh, body, tint, 120, edge=1.6)
    pen(sh, ellipse_points(c, c, r, r, 36, 0, 2 * math.pi * 1.05), 1.6, PEN, 220)
    sh.stroke(ellipse_points(c, c, r - 7, r - 7, 14, math.radians(200), math.radians(60)), 2.6, WHITE, 250, amp=0.2)
    sh.ellipse(c + 11, c + 10, 2, 2, 1.0, PEN, 180, amp=0.1)
    return sh.result()


def mote(color, seed):
    """물속을 떠도는 작은 잉크 방울."""
    s_ = 40
    sh = Sheet(s_, s_, seed=seed)
    sh.wash(s_ / 2, s_ / 2, 8, 8, color, alpha=90, layers=1, edge=0.3, blur=3)
    sh.wash(s_ / 2, s_ / 2, 3.2, 3.2, color, alpha=240, layers=1, edge=0.8, blur=0.6)
    return sh.result()


def sparkle():
    """반짝이는 기포."""
    s_ = 48
    sh = Sheet(s_, s_, seed=1461)
    sh.ellipse(s_ / 2, s_ / 2, 9, 9, 1.6, WHITE, 255, amp=0.1)
    sh.stroke(ellipse_points(s_ / 2, s_ / 2, 5, 5, 8, math.radians(200), math.radians(70)), 2.0, WHITE, 255, amp=0.1)
    sh.add_glow(WHITE, blur=3, strength=1.0)
    return sh.result()


def main():
    save(background(), TITLE, 'background.png')
    for i, f in enumerate(dye_frames()):
        save(f, TITLE, f'dye_{i}.png')
    save(logo(), TITLE, 'logo.png')
    save(empty(), TITLE, 'logo_glow.png')
    save(ink_bottle(), TITLE, 'ink_bottle.png')
    save(dreamy.soft_glow(380, 440, (255, 252, 244), 43, alpha=210), TITLE, 'bottle_glow.png')
    rings = Sheet(280, 70, seed=1152)
    for rx, ry, a in ((50, 7, 170), (82, 11, 120), (114, 15, 80)):
        rings.stroke(ellipse_points(140, 35, rx, ry, 40), 1.8, INK_SOFT, a, amp=0.2, taper=False)
    save(rings.result(), TITLE, 'light_pool.png')
    for name, label, color, seed in (('start', '시작하기', INKS['red'], 1381), ('settings', '설정', INKS['green'], 1383),
                                     ('quit', '끝내기', INKS['blue'], 1382)):
        save(button(label, color, seed, False), TITLE, f'button_{name}.png')
        save(button(label, color, seed, True), TITLE, f'button_{name}_hover.png')
    for i, (name, tint) in enumerate((('pearl', (255, 246, 236)), ('pink', (255, 200, 224)),
                                      ('lavender', (210, 196, 255)), ('sky', (186, 216, 255)))):
        save(bubble(tint, 1440 + i), TITLE, f'bubble_{name}.png')
    for i, (name, c) in enumerate((('pearl', INK), ('sky', INKS['blue']), ('lavender', INKS['violet']),
                                   ('gold', INKS['gold']), ('pink', INKS['red']))):
        save(mote(c, 1450 + i), TITLE, f'mote_{name}.png')
    save(sparkle(), TITLE, 'sparkle.png')

    save(Image.new('RGBA', (16, 16), (40, 50, 90, 255)), SETTINGS, 'dim.png')
    save(settings_panel(), SETTINGS, 'panel.png')
    save(slider_track(), SETTINGS, 'slider_track.png')
    save(slider_track(filled=True), SETTINGS, 'slider_fill.png')
    save(slider_knob(), SETTINGS, 'slider_knob.png')
    save(toggle(True), SETTINGS, 'toggle_on.png')
    save(toggle(False), SETTINGS, 'toggle_off.png')
    save(button('닫기', INKS['violet'], 1431, False, (220, 84)), SETTINGS, 'button_close.png')
    save(button('닫기', INKS['violet'], 1431, True, (220, 84)), SETTINGS, 'button_close_hover.png')


if __name__ == '__main__':
    main()
