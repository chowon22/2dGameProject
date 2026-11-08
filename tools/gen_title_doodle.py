"""타이틀·설정 화면 '낙서체' 버전 이미지 생성.

몽환적인 버전(gen_title_images.py)과 같은 장면·색감(라벤더·분홍 안개, 해를 등진 고목, 길쭉한 나무,
가운데 잉크통)을, 종이 위에 색연필·크레용으로 끄적인 낙서처럼 다시 그린다.
- 판판한 색 대신 결이 보이는 크레용 칠, 두 번 그은 듯한 삐뚤빼뚤한 선
- 해·구름·별·소용돌이·새 같은 낙서 장식
- 글씨는 손글씨(감자꽃체)

실행:  python tools/gen_title_doodle.py
결과:  image/title_doodle/*.png, image/settings_doodle/*.png  (파일 이름은 몽환 버전과 같다)
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, paper, bezier, ellipse_points  # noqa: E402
from gen_title_images import (W, H, LIGHT, SUN, WHITE, GOLD, ELEMENT, FONT_PATH, PANEL_W, PANEL_H,  # noqa: E402
                              SETTING_ROWS, save, poly_mask, lumpy, densify, star_doodle, lighter, darker,
                              day_sky, bloom)

TITLE, SETTINGS = 'title_doodle', 'settings_doodle'
PLUM = (96, 78, 140)        # 낙서 선의 기본 색 (자두빛 색연필)
PLUM_SOFT = (150, 132, 190)
PAPER_WHITE = (255, 252, 248)


def hand(size):
    return ImageFont.truetype(FONT_PATH, size)


# ================================================================ 낙서 도구
def sketch_line(sh, pts, color, width=2.4, alpha=230, amp=1.4, double=True):
    """두 번 그은 듯한 색연필 선. 두 번째 선은 살짝 어긋나고 옅다."""
    sh.stroke(pts, width, color, alpha, amp=amp)
    if double:
        off = [(x + sh.rng.uniform(-1.2, 1.2), y + sh.rng.uniform(-1.2, 1.2)) for x, y in pts]
        sh.stroke(off, width * 0.6, color, int(alpha * 0.55), amp=amp * 1.4)


def crayon_fill(sh, pts, color, base_alpha=150, gap=5, angle=-0.6, cross=True, size=(W, H)):
    """크레용 칠: 옅은 바탕 + 결이 보이는 끄적임 두 겹 (방향을 달리해서)."""
    sh.fill_poly(pts, color, base_alpha)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = (min(xs), min(ys), max(xs), max(ys))
    m = poly_mask(size, pts)
    sh.scribble(box, darker(color, 0.92), alpha=150, gap=gap, angle=angle, width=2.0, mask=m)
    if cross:
        sh.scribble(box, lighter(color, 30), alpha=110, gap=gap * 1.6, angle=angle + 1.1, width=1.6, mask=m)


def crayon_mask_fill(sh, mask, color, base_alpha=150, gap=5, angle=-0.6, box=None):
    """마스크 모양으로 크레용 칠 (mask: 시트 원래 크기 L)."""
    f = Sheet(sh.w, sh.h, seed=sh.rng.randint(0, 99999))
    f.fill_poly([(0, 0), (sh.w, 0), (sh.w, sh.h), (0, sh.h)], color, base_alpha)
    box = box or (0, 0, sh.w, sh.h)
    f.scribble(box, darker(color, 0.92), alpha=170, gap=gap, angle=angle, width=2.0)
    f.scribble(box, lighter(color, 30), alpha=110, gap=gap * 1.6, angle=angle + 1.1, width=1.6)
    sh.masked(f, mask)


def top_contour(mask, x0, x1, step=3):
    arr = np.asarray(mask) > 100
    out = []
    for px in range(max(0, int(x0)), min(arr.shape[1], int(x1)), step):
        col = arr[:, px]
        if col.any():
            out.append((px, int(col.argmax()) + 1))
    return out


def spiral(sh, x, y, r, color, alpha=200, width=1.8, turns=1.6):
    pts = []
    n = 40
    for i in range(n + 1):
        t = i / n
        a = t * turns * 2 * math.pi
        rr = r * t
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    sh.stroke(pts, width, color, alpha, amp=0.4)


def heart(sh, x, y, r, color, alpha=220, width=1.8):
    pts = []
    for i in range(41):
        t = i / 40 * 2 * math.pi
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x + hx * r / 16, y + hy * r / 16))
    sh.stroke(pts, width, color, alpha, amp=0.3)


def bird(sh, x, y, s, color, alpha=200):
    sh.stroke([(x - s, y - s * 0.4), (x - s * 0.4, y - s * 0.1), (x, y + s * 0.2)], 1.8, color, alpha, amp=0.3)
    sh.stroke([(x, y + s * 0.2), (x + s * 0.4, y - s * 0.1), (x + s, y - s * 0.4)], 1.8, color, alpha, amp=0.3)


# ================================================================ 배경
def doodle_cloud(sh, x, y, w, h):
    bumps = []
    n = max(3, int(w / 45))
    for i in range(n):
        bx = x - w / 2 + w * (i + 0.5) / n
        br = h * (0.55 + 0.45 * math.sin(math.pi * (i + 0.5) / n)) * sh.rng.uniform(0.85, 1.1)
        bumps.append((bx, y - br * 0.3, br))
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    for bx, by, br in bumps:
        d.ellipse((bx - br, by - br, bx + br, by + br), fill=255)
    d.rectangle((x - w / 2, y - h * 0.2, x + w / 2, y + h * 0.35), fill=255)
    crayon_mask_fill(sh, m, PAPER_WHITE, base_alpha=200, gap=5, angle=-0.3,
                     box=(x - w / 2 - 40, y - h * 1.3, x + w / 2 + 40, y + h * 0.5))
    sh.scribble((x - w / 2, y, x + w / 2, y + h * 0.4), (214, 200, 244), alpha=120, gap=4, angle=-0.2, width=1.6,
                mask=m)
    sketch_line(sh, top_contour(m, x - w / 2 - h, x + w / 2 + h), PLUM_SOFT, 2.2, 200)
    sketch_line(sh, [(x - w / 2 + 12, y + h * 0.35), (x + w / 2 - 12, y + h * 0.35)], PLUM_SOFT, 1.8, 150)


def doodle_sun(sh):
    sx, sy = SUN
    r = 44
    disc = ellipse_points(sx, sy, r, r, 48)
    crayon_fill(sh, disc, (255, 244, 214), base_alpha=230, gap=4, angle=-0.8)
    sh.ellipse(sx, sy, r, r, 2.4, (236, 190, 120), 240, amp=0.8)
    for k in range(14):
        a = k * 2 * math.pi / 14 + sh.rng.uniform(-0.05, 0.05)
        r0, r1 = r + 12, r + sh.rng.uniform(26, 40)
        sh.stroke([(sx + math.cos(a) * r0, sy + math.sin(a) * r0), (sx + math.cos(a) * r1, sy + math.sin(a) * r1)],
                  2.2, (236, 190, 120), 220, amp=0.3)


def doodle_tall_tree(sh, cx, ground, height, width, fill, line):
    top = ground - height
    lean = sh.rng.uniform(-6, 6)
    left = bezier((cx, ground), (cx - width * 1.1, ground - height * 0.25),
                  (cx - width * 0.9, top + height * 0.25), (cx + lean, top), 24)
    right = bezier((cx + lean, top), (cx + width * 0.9, top + height * 0.25),
                   (cx + width * 1.1, ground - height * 0.25), (cx, ground), 24)[1:]
    pts = left + right
    crayon_fill(sh, pts, fill, base_alpha=200, gap=5, angle=-1.25, cross=False)
    sketch_line(sh, pts, line, 2.0, 210, amp=1.0)
    # 가운데 잎맥 낙서
    sh.stroke([(cx, ground - 4), (cx + lean * 0.7, top + height * 0.18)], 1.4, line, 150, amp=0.8)
    for t in (0.35, 0.55, 0.75):
        y = ground - height * t
        sh.stroke([(cx + lean * t, y), (cx + lean * t + width * 0.45, y - width * 0.35)], 1.2, line, 120, amp=0.3)
    sh.stroke([(cx, ground), (cx, ground + 8)], 2.4, darker(line, 0.9), 220, amp=0.2)


def doodle_great_tree(sh):
    tx, ground = SUN[0], 470
    fill, line = (200, 182, 226), (150, 130, 196)
    trunk = bezier((tx - 70, ground), (tx - 40, ground - 90), (tx - 34, ground - 170), (tx - 22, ground - 230), 20) + \
        bezier((tx + 22, ground - 230), (tx + 34, ground - 170), (tx + 40, ground - 90), (tx + 74, ground), 20)
    crayon_fill(sh, trunk, fill, base_alpha=230, gap=5, angle=-1.4)
    for k in range(6):  # 나무껍질 낙서
        y = ground - 30 - k * 34
        sh.stroke([(tx - 20 + k * 3, y), (tx - 4, y - 10), (tx + 12, y - 4)], 1.4, line, 150, amp=0.5)
    blobs = [(0, -300, 150), (-140, -270, 105), (140, -275, 110), (-70, -380, 110), (80, -380, 115),
             (-220, -230, 70), (225, -235, 72), (0, -440, 85)]
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    for bx, by, r in blobs:
        d.ellipse((tx + bx - r, ground + by - r * 0.85, tx + bx + r, ground + by + r * 0.85), fill=255)
    crayon_mask_fill(sh, m, fill, base_alpha=220, gap=6, angle=-0.8, box=(tx - 320, ground - 560, tx + 320, ground - 120))
    # 수관 안 동글동글 잎 낙서
    arr = np.asarray(m) > 100
    for _ in range(40):
        px, py = sh.rng.uniform(tx - 280, tx + 280), sh.rng.uniform(ground - 540, ground - 170)
        if 0 <= px < W and 0 <= py < H and arr[int(py), int(px)]:
            sh.stroke(ellipse_points(px, py, 10, 7, 12, sh.rng.uniform(0, 6), 4.0), 1.5, line, 150, amp=0.3)
    sketch_line(sh, top_contour(m, tx - 300, tx + 300), line, 2.4, 220)
    sketch_line(sh, trunk[:21], line, 2.2, 220)
    sketch_line(sh, trunk[21:], line, 2.2, 220)


def white_haze(sh, y, height, alpha=90):
    """크레용으로 하얗게 문지른 안개 띠."""
    sh.wash(W / 2, y, W * 0.65, height, (255, 248, 252), alpha=int(alpha * 0.8), layers=3, edge=0.0, blur=14)
    sh.scribble((-20, y - height * 0.6, W + 20, y + height * 0.6), WHITE, alpha=alpha, gap=6, angle=-0.12, width=2.2)


def doodle_flower(sh, x, y, color):
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        px, py = x + math.cos(a) * 4.2, y + math.sin(a) * 4.2
        sh.fill_poly(ellipse_points(px, py, 3.2, 3.2, 10), color, 240)
        sh.ellipse(px, py, 3.2, 3.2, 1.0, PLUM_SOFT, 200, amp=0.2)
    sh.fill_poly(ellipse_points(x, y, 1.8, 1.8, 8), (255, 220, 120), 255)


def doodle_grass(sh, x, y, color):
    for dx, lean in ((-5, -0.5), (0, 0.0), (5, 0.45)):
        hgt = sh.rng.uniform(9, 16)
        sh.stroke([(x + dx, y), (x + dx + lean * hgt * 0.8, y - hgt)], 1.8, color, 210, amp=0.4)


def background():
    sky = day_sky()
    # 종이 결을 더 진하게 곱해 색연필 종이 느낌
    grain = np.asarray(paper(W, H, seed=8).convert('RGB'), np.float32) / 247.0
    arr = np.asarray(sky.convert('RGB'), np.float32) * (0.82 + 0.18 * grain)
    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')
    sh = Sheet(W, H, seed=12)

    # 하늘 크레용 결 (분홍·라벤더·흰색으로 넓게 문지름)
    for x, y, col in ((200, 90, (255, 214, 232)), (640, 60, (220, 206, 250)), (1100, 60, (230, 214, 255)),
                      (380, 260, WHITE), (860, 300, (255, 226, 236))):
        sh.scribble((x - 220, y - 50, x + 220, y + 50), col, alpha=38, gap=12, angle=-0.25, width=2.2)

    doodle_sun(sh)
    for x, y, w, h in ((640, 90, 190, 26), (560, 290, 150, 22), (330, 360, 170, 24)):
        doodle_cloud(sh, x, y, w, h)
    # 하늘 낙서 장식: 별, 소용돌이, 하트, 새
    for x, y, r in ((90, 60, 9), (470, 40, 7), (760, 200, 8), (330, 340, 6), (1230, 300, 8), (60, 300, 6)):
        star_doodle(sh, x, y, r, WHITE, 255, 2.0)
        star_doodle(sh, x, y, r * 0.5, PLUM_SOFT, 200, 1.2)
    spiral(sh, 420, 210, 12, PLUM_SOFT, 170)
    spiral(sh, 1210, 200, 10, PLUM_SOFT, 150)
    heart(sh, 740, 40, 8, (240, 150, 190), 230)
    for x, y, s in ((360, 110, 8), (385, 96, 6), (410, 118, 7)):
        bird(sh, x, y, s, PLUM_SOFT, 200)

    # 먼 산
    far = [(-20, 400), (120, 360), (240, 380), (380, 330), (520, 384), (660, 400), (780, 372), (900, 396),
           (1080, 360), (1200, 380), (1300, 368), (1300, 720), (-20, 720)]
    far = lumpy(densify(far, 8), 4, sh.rng, 0.15)
    crayon_fill(sh, far, (222, 208, 236), base_alpha=200, gap=7, angle=-0.2, cross=False)
    sketch_line(sh, [p for p in far if p[1] < H - 2], PLUM_SOFT, 1.8, 140)
    white_haze(sh, 410, 30, 80)

    doodle_great_tree(sh)
    # 해에서 내리는 빛: 흰 색연필 사선
    for k in range(7):
        a = math.pi * 0.62 + (k - 3) * 0.1
        r0, r1 = 80, 520 + sh.rng.uniform(-60, 60)
        sh.stroke([(SUN[0] + math.cos(a) * r0, SUN[1] + math.sin(a) * r0),
                   (SUN[0] + math.cos(a) * r1, SUN[1] + math.sin(a) * r1)], 3.0, WHITE, 120, amp=1.0)
    white_haze(sh, 466, 34, 90)

    # 먼 숲
    hill = [(-20, 470), (200, 452), (420, 470), (640, 480), (860, 470), (1080, 456), (1300, 466), (1300, 720), (-20, 720)]
    hill = lumpy(densify(hill, 8), 3, sh.rng, 0.2)
    crayon_fill(sh, hill, (206, 190, 228), base_alpha=210, gap=6, angle=-0.2, cross=False)
    sketch_line(sh, [p for p in hill if p[1] < H - 2], PLUM_SOFT, 1.8, 150)
    for i in range(24):
        x = -10 + i * 56 + sh.rng.uniform(-14, 14)
        if 520 < x < 760:
            continue
        doodle_tall_tree(sh, x, 472 + sh.rng.uniform(-6, 6), sh.rng.uniform(70, 130), sh.rng.uniform(14, 20),
                         (204, 188, 228), (170, 152, 210))
    white_haze(sh, 520, 30, 80)

    # 가운데 숲
    mid = [(-20, 540), (160, 520), (360, 540), (640, 556), (920, 540), (1120, 516), (1300, 530), (1300, 720), (-20, 720)]
    mid = lumpy(densify(mid, 8), 3, sh.rng, 0.18)
    crayon_fill(sh, mid, (178, 168, 212), base_alpha=220, gap=6, angle=-0.25, cross=False)
    sketch_line(sh, [p for p in mid if p[1] < H - 2], (140, 126, 190), 2.0, 170)
    for x in list(range(-10, 470, 48)) + list(range(830, 1300, 48)):
        x += sh.rng.uniform(-12, 12)
        doodle_tall_tree(sh, x, 540 + sh.rng.uniform(-8, 8), sh.rng.uniform(120, 200), sh.rng.uniform(20, 30),
                         (172, 162, 210), (134, 120, 186))
    white_haze(sh, 590, 26, 70)

    # 잉크통 둘레: 따뜻한 빛 + 낙서 강조선(방사형 짧은 선)
    lx, ly = LIGHT
    sh.wash(lx, ly, 170, 150, (255, 250, 240), alpha=150, layers=3, edge=0.0, blur=26)

    # 가까운 겹: 세이지빛 숲 + 꽃 언덕
    near_fill, near_line = (140, 168, 166), (90, 116, 128)
    mound = bezier((300, 720), (380, 604), (520, 600), (640, 602), 30) + \
        bezier((640, 602), (760, 604), (900, 602), (980, 720), 30)[1:]
    mound = lumpy(densify(mound, 8), 3, sh.rng, 0.2)
    crayon_fill(sh, mound, (194, 210, 200), base_alpha=230, gap=5, angle=-0.3)
    sketch_line(sh, [p for p in mound if p[1] < H - 2], (120, 140, 150), 2.4, 220)
    left = lumpy(densify([(-20, 720), (-20, 470), (80, 470), (180, 510), (260, 590), (330, 720)], 8), 3, sh.rng, 0.2)
    right = lumpy(densify([(1300, 720), (1300, 480), (1200, 476), (1100, 520), (1030, 600), (980, 720)], 8), 3,
                  sh.rng, 0.2)
    for shape in (left, right):
        crayon_fill(sh, shape, near_fill, base_alpha=230, gap=5, angle=-0.3)
        sketch_line(sh, [p for p in shape if p[1] < H - 2 and -10 < p[0] < W + 10], near_line, 2.4, 220)
    for x, g, hgt, wdt in ((20, 480, 380, 52), (96, 486, 300, 44), (170, 520, 220, 34), (230, 580, 150, 26),
                           (1262, 488, 400, 56), (1186, 486, 310, 46), (1110, 530, 220, 34), (1050, 600, 150, 26)):
        doodle_tall_tree(sh, x, g, hgt, wdt, (132 + sh.rng.randint(-6, 6), 162, 162), near_line)
    petals = [WHITE, (255, 200, 222), (226, 210, 255), (255, 232, 196)]
    for i in range(50):
        side = sh.rng.random()
        if side < 0.6:
            x = sh.rng.uniform(410, 870)
            y = 618 + abs(x - 640) * 0.08 + sh.rng.uniform(0, 70)
        elif side < 0.8:
            x, y = sh.rng.uniform(0, 240), sh.rng.uniform(600, 715)
        else:
            x, y = sh.rng.uniform(1040, 1280), sh.rng.uniform(600, 715)
        if sh.rng.random() < 0.55:
            doodle_flower(sh, x, y, petals[i % len(petals)])
        else:
            doodle_grass(sh, x, y, (90, 116, 128))
    # 공기 중 낙서 반짝이
    for _ in range(40):
        x, y = sh.rng.uniform(0, W), sh.rng.uniform(40, 620)
        if sh.rng.random() < 0.3:
            star_doodle(sh, x, y, sh.rng.uniform(3, 5), WHITE, 230, 1.4)
        else:
            sh.fill_poly(ellipse_points(x, y, 1.6, 1.6, 8), WHITE, 230)

    base.alpha_composite(sh.result())
    return bloom(base, radius=22, strength=0.35)


# ================================================================ 로고
def logo():
    """손글씨 로고: 'what are you do' + 큼직한 'Ink'(두 번 그은 흰 손글씨 + 자두빛 외곽선),
    낙서 별똥별과 빨·초·파 크레용 점."""
    lw, lh = 560, 320
    sh = Sheet(lw, lh, seed=501)
    ss = sh.ss
    cx = lw / 2

    small = hand(44)
    big = hand(200)
    m_small = sh.text_mask('what are you do', small, cx, 74, anchor='ms')
    m_big = sh.text_mask('Ink', big, cx - 10, 238, anchor='ms').filter(ImageFilter.MaxFilter(5))
    union = ImageChops.lighter(m_small, m_big)

    def solid(mask, color, alpha=255, off=(0, 0)):
        m = ImageChops.offset(mask, off[0], off[1])
        if alpha < 255:
            m = m.point(lambda v: v * alpha // 255)
        lay = Image.new('RGBA', sh.img.size, tuple(color) + (0,))
        lay.putalpha(m)
        sh.img.alpha_composite(lay)

    # 자두빛 외곽선 두 번 (살짝 어긋나게) + 흰 글씨 + 흰 크레용 결
    outline = m_big.filter(ImageFilter.MaxFilter(9))
    solid(outline.filter(ImageFilter.GaussianBlur(6 * ss)), (120, 96, 168), 110, (0, 4 * ss))
    solid(outline, PLUM, 255)
    solid(m_big, PLUM, 160, (3 * ss, -2 * ss))
    solid(m_big, WHITE)
    crayon_mask_fill(sh, m_big.resize((lw, lh), Image.BILINEAR), (236, 228, 252), base_alpha=0, gap=5, angle=-0.9)
    solid(m_small.filter(ImageFilter.MaxFilter(5)), PLUM, 230)
    solid(m_small, WHITE)

    # 낙서 별똥별: 점선 꼬리 + 별
    x1, y1 = cx + 186, 120
    for k in range(9):
        t0, t1 = k / 9, k / 9 + 0.06
        p0 = (x1 - 150 * t0, y1 + 110 * t0)
        p1 = (x1 - 150 * t1, y1 + 110 * t1)
        sh.stroke([p0, p1], 3.0 * (1 - t0) + 1, WHITE, 255, amp=0.2)
    star_doodle(sh, x1 + 4, y1 - 4, 14, WHITE, 255, 2.6)
    star_doodle(sh, x1 + 4, y1 - 4, 7, GOLD, 255, 1.8)
    # 밑줄 낙서 (물결)
    wave = [(cx - 160 + i * 4, 262 + 4 * math.sin(i / 3)) for i in range(80)]
    sketch_line(sh, wave, WHITE, 2.6, 255, amp=0.4)
    # 빨·초·파 크레용 점
    for k, key in enumerate(('red', 'green', 'blue')):
        dx = cx + 80 + k * 26
        dot = ellipse_points(dx, 290, 6, 6, 16)
        sh.fill_poly(dot, ELEMENT[key], 255)
        sh.scribble((dx - 7, 283, dx + 7, 297), lighter(ELEMENT[key], 70), alpha=180, gap=3, width=1.2,
                    mask=poly_mask((lw, lh), dot))
        sh.ellipse(dx, 290, 6, 6, 1.4, PLUM, 230, amp=0.3)
    sh.add_glow(WHITE, blur=5, strength=1.0)
    return sh.result(crop=True, margin=12)


def empty(w=16, h=16):
    return Image.new('RGBA', (w, h), (0, 0, 0, 0))


# ================================================================ 모래시계
def ink_bottle():
    """낙서 모래시계: 손으로 그은 유리 선, 위 칸은 별 낙서가 있는 검정 크레용, 아래 칸은 빨·초·파 크레용 층."""
    bw, bh = 230, 340
    cx = bw / 2
    sh = Sheet(bw, bh, seed=541)
    top, bottom = 58, 282
    neck = (top + bottom) / 2
    left = bezier((cx - 74, top), (cx - 84, top + 80), (cx - 13, neck - 30), (cx - 8, neck), 40) + \
        bezier((cx - 8, neck), (cx - 13, neck + 30), (cx - 84, bottom - 80), (cx - 74, bottom), 40)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask((bw, bh), left + right[::-1])
    size = (bw, bh)

    glass = Sheet(bw, bh, seed=542)
    glass.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (246, 242, 255), 170)
    glass.scribble((0, 0, bw, bh), WHITE, alpha=120, gap=7, angle=-0.7, width=1.6)
    # 위 칸: 검정 크레용 + 별 낙서
    surf = top + 34
    black = [(0, surf + 3 * math.sin(0)), *[(x, surf + 3 * math.sin(x / 14)) for x in range(0, bw + 1, 8)],
             (bw, neck + 2), (0, neck + 2)]
    crayon_fill(glass, black, (40, 34, 58), base_alpha=245, gap=4, angle=-0.6, size=size)
    for sx_, sy_, r_ in ((cx + 20, surf + 22, 6), (cx - 30, surf + 40, 4), (cx + 2, surf + 60, 3.5)):
        star_doodle(glass, sx_, sy_, r_, WHITE, 255, 1.4)
    glass.stroke([(cx, neck), (cx + 1, neck + 30), (cx, bottom - 60)], 2.4, (40, 34, 58), 240, amp=0.5)
    # 아래 칸: 빨·초·파 크레용 층
    mound_top = bottom - 62
    mound = bezier((0, mound_top + 10), (cx - 40, mound_top + 8), (cx - 18, mound_top - 10), (cx, mound_top - 10), 20) + \
        bezier((cx, mound_top - 10), (cx + 18, mound_top - 10), (cx + 40, mound_top + 8), (bw, mound_top + 10), 20)[1:]

    def wave(y, a, b, step):
        return [(x, y + 2.5 * math.sin(x / 12 + y)) for x in range(a, b + (1 if step > 0 else -1), step)]
    crayon_fill(glass, mound + wave(bottom - 40, bw, 0, -8), ELEMENT['red'], base_alpha=230, gap=4, angle=-0.5,
                size=size)
    crayon_fill(glass, wave(bottom - 40, 0, bw, 8) + wave(bottom - 20, bw, 0, -8), ELEMENT['green'], base_alpha=230,
                gap=4, angle=-0.5, size=size)
    crayon_fill(glass, wave(bottom - 20, 0, bw, 8) + [(bw, bh), (0, bh)], ELEMENT['blue'], base_alpha=230, gap=4,
                angle=-0.5, size=size)
    sh.masked(glass, inner)

    sketch_line(sh, left, PLUM, 3.0, 240, amp=0.8)
    sketch_line(sh, right, PLUM, 3.0, 240, amp=0.8)
    sh.stroke(bezier((cx - 56, top + 14), (cx - 64, top + 52), (cx - 44, top + 84), (cx - 30, top + 94), 20),
              3.0, WHITE, 240, amp=0.4)
    sh.stroke(bezier((cx - 58, bottom - 84), (cx - 64, bottom - 98), (cx - 56, bottom - 110), (cx - 48, bottom - 116), 12),
              2.4, WHITE, 220, amp=0.4)
    # 기둥: 금빛 색연필
    for x in (cx - 90, cx + 90):
        sketch_line(sh, [(x, top - 4), (x + 1, bottom + 4)], (214, 170, 96), 3.0, 240, amp=0.5)
        for yy in (top + 24, neck, bottom - 24):
            sh.ellipse(x, yy, 3.4, 3.4, 1.4, (214, 170, 96), 255, amp=0.2)
    # 뚜껑·받침: 진주빛 크레용 원반 + 금빛 테두리
    for y in (top - 10, bottom + 10):
        disc = ellipse_points(cx, y, 104, 14, 40)
        crayon_fill(sh, disc, (252, 244, 238), base_alpha=245, gap=4, angle=-0.3, size=size)
        sh.scribble((cx - 104, y, cx + 104, y + 14), (220, 204, 240), alpha=150, gap=4, angle=-0.2, width=1.4,
                    mask=poly_mask(size, disc))
        sketch_line(sh, disc, (214, 170, 96), 2.2, 240, amp=0.5)
    star_doodle(sh, cx, top - 36, 9, (214, 170, 96), 255, 2.0)
    sh.add_glow(WHITE, blur=8, strength=1.2)
    return sh.result(crop=True, margin=12)


def bottle_glow():
    """잉크통 뒤의 따뜻한 빛 + 낙서 강조선(짧은 방사선)."""
    w, h = 380, 440
    sh = Sheet(w, h, seed=551)
    sh.wash(w / 2, h / 2, w * 0.36, h * 0.34, (255, 248, 226), alpha=190, layers=4, edge=0.0, blur=18)
    for k in range(18):
        a = k * 2 * math.pi / 18 + sh.rng.uniform(-0.06, 0.06)
        r0 = 150 + sh.rng.uniform(-6, 6)
        r1 = r0 + sh.rng.uniform(14, 28)
        sh.stroke([(w / 2 + math.cos(a) * r0 * 0.9, h / 2 + math.sin(a) * r0),
                   (w / 2 + math.cos(a) * r1 * 0.9, h / 2 + math.sin(a) * r1)], 2.4, WHITE, 230, amp=0.3)
    return sh.result()


def light_pool():
    sh = Sheet(280, 70, seed=552)
    pool = ellipse_points(140, 35, 104, 14, 40)
    crayon_fill(sh, pool, (255, 250, 236), base_alpha=120, gap=4, angle=-0.2, size=(280, 70))
    return sh.result()


# ================================================================ 버튼 · 설정 UI
def doodle_pill(x0, y0, x1, y1, rng, n=60):
    """손으로 그린 알약 테두리 (조금 삐뚤게)."""
    r = (y1 - y0) / 2
    pts = []
    for i in range(n + 1):
        t = i / n
        if t < 0.5:
            a = math.pi / 2 + t * 2 * math.pi
            px, py = x0 + r + math.cos(a) * r, (y0 + y1) / 2 + math.sin(a) * r
        else:
            a = -math.pi / 2 + (t - 0.5) * 2 * math.pi
            px, py = x1 - r + math.cos(a) * r, (y0 + y1) / 2 + math.sin(a) * r
        pts.append((px, py))
    # 왼쪽 반원 → 아래 직선 → 오른쪽 반원 → 위 직선 순으로 이어 붙인다
    half = n // 2
    left_arc = pts[:half + 1]
    right_arc = pts[half + 1:]
    return left_arc + right_arc + [left_arc[0]]


def button(label, color, seed, hover, size=(260, 84)):
    """손으로 그린 알약 버튼: 흰 크레용 바탕 + 자두빛 두 번 그은 선 + 손글씨.
    hover 면 원소 색 크레용으로 칠해지고 낙서 별이 붙는다."""
    bw, bh = size
    sh = Sheet(bw, bh, seed=seed)
    x0, y0, x1, y1 = 22, 20, bw - 22, bh - 20
    pill = doodle_pill(x0, y0, x1, y1, sh.rng)
    fill = lighter(color, 70) if hover else PAPER_WHITE
    crayon_fill(sh, pill, fill, base_alpha=235 if hover else 215, gap=5, angle=-0.4, size=size)
    sketch_line(sh, pill, PLUM, 2.6, 245, amp=0.8)
    f = hand(34)
    sh.ink_text(label, f, bw / 2 + 8, bh / 2 + 1, PLUM, 255, anchor='mm')
    tw = f.getlength(label)
    dx = bw / 2 + 8 - tw / 2 - 14
    dot = ellipse_points(dx, bh / 2, 5, 5, 14)
    sh.fill_poly(dot, color, 255)
    sh.ellipse(dx, bh / 2, 5, 5, 1.2, PLUM, 230, amp=0.2)
    if hover:
        star_doodle(sh, x1 - 4, y0 + 2, 9, GOLD, 255, 2.2)
        star_doodle(sh, x0 + 8, y1 - 2, 5, GOLD, 255, 1.6)
    sh.add_glow(WHITE, blur=5, strength=1.0 if hover else 0.6)
    return sh.result()


def settings_panel():
    """손으로 그린 쪽지 설정 창: 흰 크레용 종이 + 자두빛 두 번 그은 테두리 + 손글씨. 행 높이는 settings_mode.ROW_Y."""
    sh = Sheet(PANEL_W, PANEL_H, seed=601)
    size = (PANEL_W, PANEL_H)
    x0, y0, x1, y1 = 26, 26, PANEL_W - 26, PANEL_H - 26
    r = 26
    box = bezier((x0 + r, y0), (x0 + 200, y0 - 4), (x1 - 200, y0 + 4), (x1 - r, y0), 30) + \
        bezier((x1 - r, y0), (x1 + 2, y0), (x1 + 2, y0 + 2), (x1, y0 + r), 8)[1:] + \
        bezier((x1, y0 + r), (x1 + 4, y0 + 160), (x1 - 3, y1 - 160), (x1, y1 - r), 30)[1:] + \
        bezier((x1, y1 - r), (x1, y1 + 2), (x1 - 2, y1 + 2), (x1 - r, y1), 8)[1:] + \
        bezier((x1 - r, y1), (x1 - 200, y1 + 4), (x0 + 200, y1 - 3), (x0 + r, y1), 30)[1:] + \
        bezier((x0 + r, y1), (x0 - 2, y1), (x0 - 2, y1 - 2), (x0, y1 - r), 8)[1:] + \
        bezier((x0, y1 - r), (x0 - 4, y1 - 160), (x0 + 3, y0 + 160), (x0, y0 + r), 30)[1:] + \
        bezier((x0, y0 + r), (x0, y0 - 2), (x0 + 2, y0 - 2), (x0 + r, y0), 8)[1:]
    sh.fill_poly([(x + 5, y + 9) for x, y in box], (110, 88, 160), 60)  # 그림자
    crayon_fill(sh, box, PAPER_WHITE, base_alpha=240, gap=6, angle=-0.4, size=size)
    sh.wash(PANEL_W * 0.8, PANEL_H * 0.85, 180, 90, (236, 224, 252), alpha=110, layers=2, blur=10)
    sh.wash(PANEL_W * 0.15, PANEL_H * 0.12, 160, 70, (255, 226, 238), alpha=110, layers=2, blur=10)
    sketch_line(sh, box, PLUM, 3.0, 245, amp=1.0)
    # 테이프 낙서
    for tx, ang in ((x0 + 40, -0.3), (x1 - 40, 0.3)):
        c_, s_ = math.cos(ang), math.sin(ang)
        tape = [(tx + c_ * dx - s_ * dy, y0 + s_ * dx + c_ * dy) for dx, dy in ((-36, -12), (36, -12), (36, 12), (-36, 12))]
        sh.fill_poly(tape, (226, 214, 250), 190)
        sketch_line(sh, tape + [tape[0]], PLUM_SOFT, 1.6, 200, amp=0.4, double=False)
    sh.ink_text('설정', hand(50), PANEL_W / 2, 66, PLUM, 255, anchor='mm')
    sketch_line(sh, [(PANEL_W / 2 - 50 + i * 4, 94 + 2.5 * math.sin(i / 2)) for i in range(26)], GOLD, 2.4, 255,
                amp=0.3)
    star_doodle(sh, PANEL_W / 2 + 70, 50, 9, GOLD, 255, 2.2)
    for i, label in enumerate(SETTING_ROWS):
        y = 150 + i * 70
        sh.ink_text(label, hand(34), 80, y, PLUM, 255, anchor='lm')
        star_doodle(sh, 62, y, 5, PLUM_SOFT, 230, 1.4)
    return sh.result()


SLIDER_STRIPES = [(250, 150, 200), (250, 214, 112), (130, 214, 182), (122, 180, 246), (176, 140, 240)]


def slider_track(filled=False):
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=611 if filled else 612)
    if filled:
        # 무지개 크레용 띠: 구간마다 색을 바꿔 끄적인다
        n = len(SLIDER_STRIPES)
        for k, col in enumerate(SLIDER_STRIPES):
            a, b = 6 + (tw - 12) * k / n, 6 + (tw - 12) * (k + 1) / n
            band = [(a - 2, 12), (b + 2, 12), (b + 2, 24), (a - 2, 24)]
            crayon_fill(sh, band, col, base_alpha=230, gap=3, angle=-1.1, cross=False, size=(tw, th))
        sketch_line(sh, [(6, 12), (tw - 6, 12)], PLUM, 1.6, 200, amp=0.4, double=False)
        sketch_line(sh, [(6, 24), (tw - 6, 24)], PLUM, 1.6, 200, amp=0.4, double=False)
    else:
        sketch_line(sh, [(6, 18), (tw - 6, 18)], PLUM, 2.4, 230, amp=0.8)
        for x in (6, tw - 6):
            sh.stroke([(x, 11), (x, 25)], 2.0, PLUM, 230, amp=0.2)
    return sh.result()


def slider_knob():
    s_ = 44
    sh = Sheet(s_, s_, seed=613)
    disc = ellipse_points(s_ / 2, s_ / 2, 12, 12, 30)
    crayon_fill(sh, disc, PAPER_WHITE, base_alpha=255, gap=3, angle=-0.6, size=(s_, s_))
    sketch_line(sh, disc, PLUM, 2.2, 245, amp=0.4)
    star_doodle(sh, s_ / 2, s_ / 2, 5, GOLD, 255, 1.4)
    return sh.result()


def toggle(on):
    """낙서 체크박스: 켜지면 빨간 크레용 체크, 꺼지면 빈 칸."""
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=621 if on else 622)
    bx = [(18, 12), (46, 11), (47, 40), (17, 41), (18, 12)]
    crayon_fill(sh, bx[:-1], (236, 228, 252) if on else PAPER_WHITE, base_alpha=230, gap=4, size=(tw, th))
    sketch_line(sh, bx, PLUM, 2.4, 245, amp=0.5)
    if on:
        sh.stroke([(22, 26), (30, 36), (52, 6)], 4.2, ELEMENT['red'], 255, amp=0.6)
        sh.stroke([(23, 27), (31, 35), (51, 8)], 1.6, lighter(ELEMENT['red'], 80), 220, amp=0.4)
    sh.ink_text('켜짐' if on else '꺼짐', hand(26), 88, th / 2, PLUM if on else PLUM_SOFT, 255, anchor='mm')
    return sh.result()


# ================================================================ 효과
def bubble(tint, seed):
    """손으로 그린 비눗방울: 삐뚤한 동그라미 + 반사 낙서 + 옅은 크레용 색."""
    sz = 72
    sh = Sheet(sz, sz, seed=seed)
    c, r = sz / 2, 27
    body = ellipse_points(c, c, r, r, 40)
    sh.fill_poly(body, tint, 60)
    sh.scribble((c - r, c - r, c + r, c + r), tint, alpha=120, gap=6, angle=-0.7, width=1.4,
                mask=poly_mask((sz, sz), body))
    sketch_line(sh, ellipse_points(c, c, r, r, 40, 0, 2 * math.pi * 1.05), PLUM_SOFT, 1.8, 230, amp=0.5)
    sh.stroke(ellipse_points(c, c, r - 7, r - 7, 14, math.radians(200), math.radians(60)), 3.0, WHITE, 250, amp=0.2)
    sh.fill_poly(ellipse_points(c + 11, c + 11, 2.2, 2.2, 8), WHITE, 255)
    return sh.result()


def mote(kind, seed):
    """공기 중 낙서 알갱이: 별 / 점 / 작은 동그라미 / 십자 / 하트."""
    s_ = 40
    sh = Sheet(s_, s_, seed=seed)
    c = s_ / 2
    sh.wash(c, c, 9, 9, (255, 250, 236), alpha=150, layers=1, edge=0.0, blur=4)
    if kind == 'pearl':
        star_doodle(sh, c, c, 8, WHITE, 255, 2.0)
    elif kind == 'sky':
        sh.ellipse(c, c, 5, 5, 1.8, WHITE, 255, amp=0.3)
    elif kind == 'lavender':
        sh.fill_poly(ellipse_points(c, c, 3, 3, 10), (226, 214, 255), 255)
        sh.ellipse(c, c, 3, 3, 1.0, PLUM_SOFT, 220, amp=0.1)
    elif kind == 'gold':
        star_doodle(sh, c, c, 7, (255, 220, 130), 255, 2.0)
    else:
        heart(sh, c, c, 6, (255, 170, 200), 255, 1.8)
    return sh.result()


def sparkle():
    s_ = 48
    sh = Sheet(s_, s_, seed=561)
    star_doodle(sh, s_ / 2, s_ / 2, 18, WHITE, 255, 3.0)
    star_doodle(sh, s_ / 2, s_ / 2, 9, GOLD, 255, 2.0)
    return sh.result()


def main():
    save(background(), TITLE, 'background.png')
    save(logo(), TITLE, 'logo.png')
    save(empty(), TITLE, 'logo_glow.png')
    save(ink_bottle(), TITLE, 'ink_bottle.png')
    save(bottle_glow(), TITLE, 'bottle_glow.png')
    save(light_pool(), TITLE, 'light_pool.png')
    for name, label, color, seed in (('start', '시작하기', ELEMENT['red'], 581),
                                     ('settings', '설정', ELEMENT['green'], 583),
                                     ('quit', '끝내기', ELEMENT['blue'], 582)):
        save(button(label, color, seed, False), TITLE, f'button_{name}.png')
        save(button(label, color, seed, True), TITLE, f'button_{name}_hover.png')
    for i, (name, tint) in enumerate((('pearl', (255, 246, 236)), ('pink', (255, 200, 224)),
                                      ('lavender', (210, 196, 255)), ('sky', (186, 216, 255)))):
        save(bubble(tint, 640 + i), TITLE, f'bubble_{name}.png')
    for i, name in enumerate(('pearl', 'sky', 'lavender', 'gold', 'pink')):
        save(mote(name, 660 + i), TITLE, f'mote_{name}.png')
    save(sparkle(), TITLE, 'sparkle.png')

    save(Image.new('RGBA', (16, 16), (92, 72, 146, 255)), SETTINGS, 'dim.png')
    save(settings_panel(), SETTINGS, 'panel.png')
    save(slider_track(), SETTINGS, 'slider_track.png')
    save(slider_track(filled=True), SETTINGS, 'slider_fill.png')
    save(slider_knob(), SETTINGS, 'slider_knob.png')
    save(toggle(True), SETTINGS, 'toggle_on.png')
    save(toggle(False), SETTINGS, 'toggle_off.png')
    save(button('닫기', ELEMENT['magenta'], 631, False, (220, 84)), SETTINGS, 'button_close.png')
    save(button('닫기', ELEMENT['magenta'], 631, True, (220, 84)), SETTINGS, 'button_close_hover.png')


if __name__ == '__main__':
    main()
