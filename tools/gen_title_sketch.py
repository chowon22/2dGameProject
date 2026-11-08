"""타이틀·설정 화면 '스케치북' 버전 이미지 생성.

같은 장면(해를 등진 고목, 길쭉한 나무, 가운데 잉크통)을 스케치북에 투박하게 그린 그림으로.
- 결이 거친 도화지 + 위쪽 스프링
- 굵은 연필 선을 두세 번 겹쳐 긋고, 모서리는 삐져나오거나 덜 닫힌다
- 크레용은 굵게 쓱쓱, 선 밖으로 삐져나오고 종이가 군데군데 비친다

실행:  python tools/gen_title_sketch.py
결과:  image/title_sketch/*.png, image/settings_sketch/*.png  (파일 이름은 다른 그림체와 같다)
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, bezier, ellipse_points  # noqa: E402
from gen_title_images import (W, H, LIGHT, SUN, WHITE, ELEMENT, FONT_PATH, PANEL_W, PANEL_H,  # noqa: E402
                              SETTING_ROWS, save, poly_mask, densify, star_doodle, lighter, darker)
from gen_title_doodle import heart, bird, top_contour, empty  # noqa: E402

TITLE, SETTINGS = 'title_sketch', 'settings_sketch'
PENCIL = (62, 58, 66)          # 연필 선
PENCIL_SOFT = (120, 114, 122)
PAPER = (247, 241, 228)        # 스케치북 도화지
CRAYON = {                     # 크레용 (조금 바랜 색)
    'sky': (150, 190, 236), 'lavender': (186, 166, 226), 'pink': (244, 166, 196), 'yellow': (250, 212, 96),
    'leaf': (120, 178, 120), 'leaf_dark': (88, 146, 104), 'hill': (166, 200, 128), 'brown': (170, 122, 92),
    'mountain': (170, 160, 206), 'white': (255, 255, 255),
}


def hand(size):
    return ImageFont.truetype(FONT_PATH, size)


# ================================================================ 투박한 도구
def rough_line(sh, pts, width=4.0, color=PENCIL, alpha=235, passes=2, amp=2.4, overshoot=6):
    """연필로 두세 번 겹쳐 그은 굵은 선. 끝은 조금씩 삐져나온다."""
    for k in range(passes):
        j = [(x + sh.rng.uniform(-1.8, 1.8), y + sh.rng.uniform(-1.8, 1.8)) for x, y in pts]
        if len(j) >= 2 and overshoot:
            (x0, y0), (x1, y1) = j[0], j[1]
            d = math.hypot(x1 - x0, y1 - y0) or 1
            o = sh.rng.uniform(0, overshoot)
            j[0] = (x0 - (x1 - x0) / d * o, y0 - (y1 - y0) / d * o)
            (xa, ya), (xb, yb) = j[-2], j[-1]
            d = math.hypot(xb - xa, yb - ya) or 1
            o = sh.rng.uniform(0, overshoot)
            j[-1] = (xb + (xb - xa) / d * o, yb + (yb - ya) / d * o)
        w = width * (1.0 if k == 0 else 0.6)
        sh.stroke(j, w, color, alpha if k == 0 else int(alpha * 0.6), amp=amp)


def rough_shape(sh, pts, color=PENCIL, width=4.0, alpha=235):
    """닫힌 모양을 한 바퀴보다 조금 덜/더 돌아 그린다 (삐뚤게 안 맞는 끝)."""
    n = len(pts)
    cut = int(n * sh.rng.uniform(-0.04, 0.06))
    path = pts + pts[1:max(2, cut)] if cut > 0 else pts[:n + cut]
    rough_line(sh, path, width, color, alpha)


def crayon(sh, pts, color, size=(W, H), coverage=0.8, stroke=4.2, gap=7, spill=5, angle=None):
    """선 밖으로 삐져나오는 투박한 크레용 칠. 종이가 군데군데 비친다."""
    m = poly_mask(size, pts)
    if spill:
        m = m.filter(ImageFilter.MaxFilter(spill * 2 + 1))
        m = ImageChops.offset(m, int(sh.rng.uniform(-spill, spill)), int(sh.rng.uniform(-spill, spill)))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = (min(xs) - spill * 2, min(ys) - spill * 2, max(xs) + spill * 2, max(ys) + spill * 2)
    a = angle if angle is not None else sh.rng.uniform(-1.2, -0.3)
    sh.fill_poly(pts, color, int(70 * coverage))
    sh.scribble(box, color, alpha=int(230 * coverage), gap=gap, angle=a, width=stroke, mask=m, amp=2.4)
    sh.scribble(box, darker(color, 0.9), alpha=int(150 * coverage), gap=gap * 1.7, angle=a + 0.9,
                width=stroke * 0.7, mask=m, amp=2.4)


def crayon_mask(sh, mask, color, box, coverage=0.8, stroke=4.2, gap=7):
    f = Sheet(sh.w, sh.h, seed=sh.rng.randint(0, 99999))
    f.fill_poly([(0, 0), (sh.w, 0), (sh.w, sh.h), (0, sh.h)], color, int(70 * coverage))
    a = sh.rng.uniform(-1.2, -0.3)
    f.scribble(box, color, alpha=int(230 * coverage), gap=gap, angle=a, width=stroke, amp=2.4)
    f.scribble(box, darker(color, 0.9), alpha=int(150 * coverage), gap=gap * 1.7, angle=a + 0.9, width=stroke * 0.7,
               amp=2.4)
    sh.masked(f, mask)


def wobbly(points, rng, amp):
    return [(x + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp)) for x, y in points]


# ================================================================ 종이
def sketchbook_paper(w, h, seed=0, spiral=True):
    """결이 거친 도화지: 굵은 얼룩 + 거친 알갱이 + (선택) 위쪽 스프링 구멍."""
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(PAPER, np.float32)
    tooth = rng.normal(0, 6, (h, w)).astype(np.float32)
    tooth_img = Image.fromarray(np.clip(tooth * 8 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    tooth = (np.asarray(tooth_img, np.float32) - 128) / 8
    low = rng.normal(0, 1, (h // 40 + 2, w // 40 + 2)).astype(np.float32)
    low = np.asarray(Image.fromarray(np.clip(low * 30 + 128, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                     np.float32)
    low = (low - 128) / 30 * 5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 40
    arr = base + (tooth + low - vig)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')


def spiral_binding(sh, w, y=20, gap=44):
    """스케치북 위쪽 스프링: 구멍 + 철사 고리."""
    for x in range(int(gap * 0.7), int(w), gap):
        sh.fill_poly(ellipse_points(x, y + 6, 5, 6, 14), (70, 66, 72), 230)
        coil = bezier((x - 8, -6), (x - 12, y - 6), (x - 4, y + 10), (x + 2, y + 6), 16)
        sh.stroke(coil, 4.4, (120, 118, 126), 255, amp=0.2, taper=False)
        sh.stroke(coil[2:-3], 1.6, (230, 230, 236), 230, amp=0.2, taper=False)


# ================================================================ 배경
def kid_tree(sh, x, ground, height, width, color):
    """투박한 길쭉한 나무: 막대 줄기 + 잎 덩어리."""
    top = ground - height
    sh.stroke([(x, ground + 4), (x + sh.rng.uniform(-2, 2), ground - height * 0.25)], 5, CRAYON['brown'], 240, amp=1.2)
    left = bezier((x, ground - height * 0.18), (x - width * 1.2, ground - height * 0.3),
                  (x - width * 0.9, top + height * 0.2), (x, top), 14)
    right = bezier((x, top), (x + width * 0.9, top + height * 0.2), (x + width * 1.2, ground - height * 0.3),
                   (x, ground - height * 0.18), 14)[1:]
    pts = wobbly(left + right, sh.rng, 2.5)
    crayon(sh, pts, color, stroke=4.0, gap=6, spill=4)
    rough_shape(sh, pts, PENCIL, 3.2, 220)
    rough_line(sh, [(x - 3, ground + 4), (x - 3, ground - height * 0.2)], 2.4, PENCIL, 200, passes=1)
    rough_line(sh, [(x + 3, ground + 4), (x + 3, ground - height * 0.2)], 2.4, PENCIL, 200, passes=1)


def kid_cloud(sh, x, y, w, h):
    bumps = []
    n = max(3, int(w / 50))
    for i in range(n):
        bx = x - w / 2 + w * (i + 0.5) / n
        br = h * (0.6 + 0.4 * math.sin(math.pi * (i + 0.5) / n)) * sh.rng.uniform(0.85, 1.15)
        bumps.append((bx, y - br * 0.3, br))
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    for bx, by, br in bumps:
        d.ellipse((bx - br, by - br, bx + br, by + br), fill=255)
    d.rectangle((x - w / 2, y - h * 0.2, x + w / 2, y + h * 0.4), fill=255)
    crayon_mask(sh, m, CRAYON['white'], (x - w / 2 - 40, y - h * 1.4, x + w / 2 + 40, y + h * 0.6), coverage=0.9)
    rough_line(sh, top_contour(m, x - w / 2 - h, x + w / 2 + h, 4), 3.4, PENCIL_SOFT, 220)
    rough_line(sh, [(x - w / 2 + 8, y + h * 0.4), (x + w / 2 - 8, y + h * 0.4)], 3.0, PENCIL_SOFT, 200)


def background():
    base = sketchbook_paper(W, H, seed=21)
    sh = Sheet(W, H, seed=22)

    # 하늘: 위쪽만 하늘색·라벤더 크레용으로 성의 없이 쓱쓱 (종이가 비친다)
    for y0, col in ((40, CRAYON['sky']), (150, CRAYON['lavender']), (250, CRAYON['pink'])):
        band = wobbly([(-30, y0), (W + 30, y0 + 10), (W + 30, y0 + 120), (-30, y0 + 110)], sh.rng, 8)
        crayon(sh, band, col, coverage=0.45, stroke=5, gap=11, spill=0, angle=-0.15)

    for x, y, w, h in ((640, 96, 200, 30), (330, 330, 170, 26), (120, 230, 150, 24)):
        kid_cloud(sh, x, y, w, h)
    for x, y, s in ((380, 110, 10), (410, 96, 8), (436, 116, 9)):
        bird(sh, x, y, s, PENCIL, 230)
    heart(sh, 760, 40, 9, (226, 110, 150), 240, 2.6)
    for x, y in ((90, 70), (480, 46), (1240, 300), (60, 330)):
        star_doodle(sh, x, y, 8, (220, 170, 60), 255, 2.8)

    # 먼 산: 삐뚤한 세모들
    peaks = [(-40, 430, 120, 340), (110, 430, 270, 320), (300, 430, 450, 360), (760, 430, 900, 330),
             (930, 430, 1060, 350), (1100, 430, 1260, 330)]
    for x0, yb, xm, yt in peaks:
        tri = wobbly([(x0, yb), (xm, yt), (xm + (xm - x0), yb)], sh.rng, 3)
        crayon(sh, tri, CRAYON['mountain'], coverage=0.6, stroke=4, gap=8, spill=3)
        rough_line(sh, tri[:2] + [tri[2]], 3.4, PENCIL_SOFT, 220)

    # 거대한 고목: 굵은 줄기 + 큰 뭉게 잎
    tx, ground = SUN[0], 470
    trunk = wobbly([(tx - 60, ground), (tx - 34, ground - 120), (tx - 26, ground - 230), (tx + 26, ground - 230),
                    (tx + 34, ground - 120), (tx + 64, ground)], sh.rng, 3)
    crayon(sh, trunk, CRAYON['brown'], coverage=0.9, stroke=5, gap=6, spill=3, angle=-1.4)
    rough_line(sh, trunk[:3], 4, PENCIL, 235)
    rough_line(sh, trunk[3:], 4, PENCIL, 235)
    blobs = [(0, -300, 150), (-140, -270, 100), (140, -275, 105), (-70, -380, 105), (80, -380, 110),
             (-215, -232, 66), (220, -236, 68), (0, -440, 80)]
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    for bx, by, r in blobs:
        d.ellipse((tx + bx - r, ground + by - r * 0.85, tx + bx + r, ground + by + r * 0.85), fill=255)
    crayon_mask(sh, ImageChops.offset(m.filter(ImageFilter.MaxFilter(9)), 4, -3), CRAYON['leaf'],
                (tx - 330, ground - 560, tx + 330, ground - 120), coverage=0.9, stroke=5, gap=6)
    rough_line(sh, top_contour(m, tx - 300, tx + 300, 5), 4.4, PENCIL, 235)
    for _ in range(9):  # 나무 위 사과 같은 동그라미
        px, py = sh.rng.uniform(tx - 200, tx + 200), sh.rng.uniform(ground - 470, ground - 200)
        if np.asarray(m)[int(py), int(px)]:
            apple = wobbly(ellipse_points(px, py, 8, 8, 12), sh.rng, 1)
            crayon(sh, apple, ELEMENT['red'], coverage=1.0, stroke=3.4, gap=3, spill=2)
            sh.ellipse(px, py, 8, 8, 2.6, PENCIL, 230, amp=0.8)
            sh.stroke([(px, py - 8), (px + 3, py - 14)], 2.2, PENCIL, 230, amp=0.3)

    # 해: 아이 그림처럼 오른쪽 위 모서리에 걸친 해 (고목보다 앞)
    sx, sy, sr = W - 6, 34, 86
    sun = wobbly(ellipse_points(sx, sy, sr, sr, 36, math.pi * 0.5, math.pi * 1.0), sh.rng, 2) + [(sx, sy)]
    crayon(sh, sun, CRAYON['yellow'], coverage=1.0, stroke=5.5, gap=5, spill=5, angle=-0.8)
    rough_line(sh, sun[:-1], 4.2, (200, 150, 60), 240)
    for k in range(7):
        a_ = math.pi * 0.5 + (k + 0.5) * math.pi / 7
        r0, r1 = sr + 14, sr + sh.rng.uniform(34, 52)
        rough_line(sh, [(sx + math.cos(a_) * r0, sy + math.sin(a_) * r0), (sx + math.cos(a_) * r1, sy + math.sin(a_) * r1)],
                   4.2, (226, 176, 60), 240, passes=1, overshoot=3)

    # 언덕 (두 겹)
    hill1 = wobbly(densify([(-30, 480), (220, 456), (480, 476), (700, 470), (960, 456), (1310, 470),
                            (1310, 720), (-30, 720)], 30), sh.rng, 3)
    crayon(sh, hill1, CRAYON['hill'], coverage=0.75, stroke=5, gap=7, spill=3, angle=-0.2)
    rough_line(sh, [p for p in hill1 if p[1] < 700], 4, PENCIL, 230)
    for i in range(16):
        x = 20 + i * 82 + sh.rng.uniform(-14, 14)
        if 520 < x < 770:
            continue
        kid_tree(sh, x, 474 + sh.rng.uniform(-6, 6), sh.rng.uniform(90, 150), sh.rng.uniform(16, 24),
                 CRAYON['leaf'] if i % 2 else CRAYON['leaf_dark'])

    # 잉크통 둘레: 노란 크레용 반짝 선
    lx, ly = LIGHT
    for k in range(16):
        a = k * 2 * math.pi / 16
        r0, r1 = 150, 150 + sh.rng.uniform(16, 30)
        rough_line(sh, [(lx + math.cos(a) * r0 * 0.85, ly + math.sin(a) * r0),
                        (lx + math.cos(a) * r1 * 0.85, ly + math.sin(a) * r1)], 3.6, (236, 190, 70), 230, passes=1,
                   overshoot=2)

    # 가까운 언덕 + 양쪽 큰 나무 + 꽃
    near = wobbly(densify([(-30, 560), (200, 540), (420, 600), (640, 610), (860, 600), (1080, 540), (1310, 556),
                           (1310, 730), (-30, 730)], 30), sh.rng, 3)
    crayon(sh, near, (150, 196, 120), coverage=0.85, stroke=5.5, gap=6, spill=3, angle=-0.25)
    rough_line(sh, [p for p in near if p[1] < 715], 4.4, PENCIL, 235)
    for x, g, hgt, wdt in ((40, 560, 330, 46), (140, 548, 240, 36), (1240, 560, 340, 48), (1140, 550, 250, 38)):
        kid_tree(sh, x, g, hgt, wdt, CRAYON['leaf_dark'])
    flower_cols = [ELEMENT['red'], CRAYON['pink'], CRAYON['yellow'], CRAYON['lavender'], CRAYON['sky']]
    for i in range(30):
        x = sh.rng.uniform(20, W - 20)
        if 520 < x < 760 and sh.rng.random() < 0.6:
            continue
        y = sh.rng.uniform(600, 705)
        sh.stroke([(x, y + 14), (x + sh.rng.uniform(-3, 3), y)], 2.6, (80, 130, 80), 230, amp=0.8)
        petals = wobbly(ellipse_points(x, y, 6, 6, 10), sh.rng, 1.2)
        crayon(sh, petals, flower_cols[i % len(flower_cols)], coverage=1.0, stroke=3, gap=3, spill=2)
        sh.ellipse(x, y, 6, 6, 2.0, PENCIL, 210, amp=1.0)
    for _ in range(26):  # 풀 (V자 낙서)
        x, y = sh.rng.uniform(0, W), sh.rng.uniform(590, 715)
        rough_line(sh, [(x - 5, y - 9), (x, y), (x + 5, y - 10)], 2.4, (80, 130, 80), 220, passes=1, overshoot=0)

    spiral_binding(sh, W)
    base.alpha_composite(sh.result())
    return base.convert('RGB')


# ================================================================ 로고
def logo():
    """투박한 손글씨 로고: 연필로 두 번 그은 테두리 + 선 밖으로 삐져나온 크레용."""
    lw, lh = 560, 320
    sh = Sheet(lw, lh, seed=701)
    ss = sh.ss
    cx = lw / 2
    m_small = sh.text_mask('what are you do', hand(46), cx, 76, anchor='ms')
    m_big = sh.text_mask('Ink', hand(210), cx - 10, 244, anchor='ms').filter(ImageFilter.MaxFilter(9))

    def lay(mask, color, alpha=255, off=(0, 0)):
        m = ImageChops.offset(mask, off[0], off[1])
        if alpha < 255:
            m = m.point(lambda v: v * alpha // 255)
        layer_ = Image.new('RGBA', sh.img.size, tuple(color) + (0,))
        layer_.putalpha(m)
        sh.img.alpha_composite(layer_)

    # 흰 종이 조각 바탕 (스케치북 위에서 글씨가 또렷하게)
    blob = m_big.filter(ImageFilter.MaxFilter(41)).filter(ImageFilter.GaussianBlur(4 * ss))
    lay(blob.point(lambda v: 255 if v > 80 else 0), (255, 252, 244), 210)
    # 'Ink': 글자마다 크레용 색, 선 밖으로 삐져나오게 칠한 뒤 연필 테두리 두 번
    arr = np.asarray(m_big) > 128
    cols = np.where(arr.any(axis=0))[0]
    x0, x1 = cols[0] / ss, cols[-1] / ss
    for k, key in enumerate(('red', 'green', 'blue')):
        a, b = x0 + (x1 - x0) * k / 3, x0 + (x1 - x0) * (k + 1) / 3
        part = Image.new('L', sh.img.size, 0)
        ImageDraw.Draw(part).rectangle([(a - 4) * ss, 0, (b + 4) * ss, lh * ss], fill=255)
        part = ImageChops.multiply(part, m_big)
        spill = ImageChops.offset(part.filter(ImageFilter.MaxFilter(11)), 5 * ss, -4 * ss)
        crayon_mask(sh, spill.resize((lw, lh), Image.BILINEAR), ELEMENT[key], (a - 20, 60, b + 20, 280),
                    coverage=1.0, stroke=5, gap=5)
    edge = ImageChops.subtract(m_big.filter(ImageFilter.MaxFilter(7)), m_big.filter(ImageFilter.MinFilter(3)))
    lay(edge, PENCIL, 255)
    lay(edge, PENCIL, 130, (3 * ss, 2 * ss))
    # 윗줄: 연필 손글씨 (두 번)
    lay(m_small, PENCIL, 255)
    lay(m_small, PENCIL, 110, (2 * ss, 1 * ss))
    # 밑줄과 장식
    rough_line(sh, [(cx - 150, 270), (cx - 40, 264), (cx + 60, 272), (cx + 170, 262)], 4, PENCIL, 235)
    star_doodle(sh, cx + 196, 120, 14, (220, 170, 60), 255, 3.2)
    star_doodle(sh, cx - 200, 150, 9, (220, 170, 60), 255, 2.6)
    heart(sh, cx + 190, 230, 10, (226, 110, 150), 255, 3.0)
    return sh.result(crop=True, margin=10)


# ================================================================ 모래시계
def ink_bottle():
    """투박한 모래시계: 굵은 연필 선, 위 칸 검정 크레용(별 낙서), 아래 칸 빨·초·파 크레용 층."""
    bw, bh = 230, 340
    cx = bw / 2
    sh = Sheet(bw, bh, seed=741)
    size = (bw, bh)
    top, bottom = 58, 282
    neck = (top + bottom) / 2
    left = bezier((cx - 74, top), (cx - 84, top + 80), (cx - 13, neck - 30), (cx - 8, neck), 20) + \
        bezier((cx - 8, neck), (cx - 13, neck + 30), (cx - 84, bottom - 80), (cx - 74, bottom), 20)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask(size, left + right[::-1])

    glass = Sheet(bw, bh, seed=742)
    glass.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (255, 255, 255), 200)
    crayon(glass, [(0, top + 30), (bw, top + 26), (bw, neck + 4), (0, neck + 4)], (40, 36, 48), size=size,
           coverage=1.0, stroke=5, gap=4, spill=0)
    for sx_, sy_, r_ in ((cx + 18, top + 54, 6), (cx - 26, top + 70, 4)):
        star_doodle(glass, sx_, sy_, r_, (255, 236, 150), 255, 2.0)
    glass.stroke([(cx, neck), (cx + 2, neck + 30), (cx - 1, bottom - 60)], 3.2, (40, 36, 48), 240, amp=1.0)
    for y0, y1, key in ((bottom - 64, bottom - 42, 'red'), (bottom - 42, bottom - 21, 'green'), (bottom - 21, bh, 'blue')):
        crayon(glass, [(0, y0), (bw, y0 + 3), (bw, y1 + 2), (0, y1)], ELEMENT[key], size=size, coverage=1.0,
               stroke=5, gap=4, spill=0, angle=-0.3)
    sh.masked(glass, inner)

    rough_line(sh, left, 4.2, PENCIL, 240)
    rough_line(sh, right, 4.2, PENCIL, 240)
    sh.stroke([(cx - 54, top + 20), (cx - 60, top + 54), (cx - 40, top + 86)], 3.4, WHITE, 240, amp=1.0)
    for x in (cx - 90, cx + 90):
        rough_line(sh, [(x, top - 6), (x + 2, bottom + 6)], 4.2, PENCIL, 235)
    for y in (top - 12, bottom + 12):
        box = wobbly([(cx - 102, y - 13), (cx + 102, y - 11), (cx + 104, y + 13), (cx - 100, y + 12)], sh.rng, 2)
        crayon(sh, box, CRAYON['brown'], size=size, coverage=1.0, stroke=4.4, gap=5, spill=3, angle=-1.3)
        rough_shape(sh, box + [box[0]], PENCIL, 4.0, 240)
    return sh.result(crop=True, margin=12)


def bottle_glow():
    """잉크통 뒤 노란 크레용 동그라미 빛 (투박하게)."""
    w, h = 380, 440
    sh = Sheet(w, h, seed=751)
    ring = wobbly(ellipse_points(w / 2, h / 2, 140, 160, 40), sh.rng, 4)
    crayon(sh, ring, (255, 236, 160), size=(w, h), coverage=0.55, stroke=6, gap=10, spill=0, angle=-0.6)
    return sh.result()


def light_pool():
    sh = Sheet(280, 70, seed=752)
    pool = wobbly(ellipse_points(140, 35, 100, 13, 24), sh.rng, 2)
    crayon(sh, pool, (110, 150, 100), size=(280, 70), coverage=0.6, stroke=4, gap=6, spill=0, angle=-0.1)
    return sh.result()


# ================================================================ 버튼 · 설정
def button(label, color, seed, hover, size=(260, 84)):
    """연필로 투박하게 그린 네모 버튼. hover 면 원소 색 크레용으로 쓱쓱 칠한다."""
    bw, bh = size
    sh = Sheet(bw, bh, seed=seed)
    x0, y0, x1, y1 = 24, 20, bw - 24, bh - 20
    box = wobbly([(x0, y0), (x1, y0 + 2), (x1 + 2, y1), (x0 + 2, y1 - 1)], sh.rng, 2)
    if hover:
        crayon(sh, box, lighter(color, 40), size=size, coverage=1.0, stroke=5, gap=5, spill=4, angle=-0.35)
    else:
        sh.fill_poly(box, (255, 253, 246), 230)
    rough_shape(sh, box + [box[0]], PENCIL, 3.8, 240)
    f = hand(36)
    sh.ink_text(label, f, bw / 2 + 8, bh / 2 + 1, PENCIL, 255, anchor='mm')
    tw = f.getlength(label)
    dx = bw / 2 + 8 - tw / 2 - 15
    dot = wobbly(ellipse_points(dx, bh / 2, 6, 6, 12), sh.rng, 1)
    crayon(sh, dot, color, size=size, coverage=1.0, stroke=3, gap=3, spill=2)
    if hover:
        star_doodle(sh, x1 - 2, y0 - 2, 10, (220, 170, 60), 255, 2.8)
    return sh.result()


def settings_panel():
    """스케치북에서 찢어낸 한 장: 위쪽 스프링 구멍 자국, 연필 글씨."""
    sh = Sheet(PANEL_W, PANEL_H, seed=801)
    size = (PANEL_W, PANEL_H)
    page = sketchbook_paper(PANEL_W - 40, PANEL_H - 40, seed=802, spiral=False)
    m = Image.new('L', page.size, 0)
    # 위쪽은 찢긴 지그재그, 나머지는 반듯
    pts = [(0, 18)]
    for x in range(0, PANEL_W - 40, 12):
        pts.append((x, 10 + (8 if (x // 12) % 2 else 0) + sh.rng.uniform(-3, 3)))
    pts += [(PANEL_W - 40, 16), (PANEL_W - 40, PANEL_H - 40), (0, PANEL_H - 40)]
    ImageDraw.Draw(m).polygon(pts, fill=255)
    shadow = Image.new('RGBA', page.size, (70, 60, 80, 0))
    shadow.putalpha(m.filter(ImageFilter.GaussianBlur(6)).point(lambda v: v * 90 // 255))
    canvas = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    canvas.alpha_composite(shadow, (26, 28))
    page.putalpha(m)
    canvas.alpha_composite(page, (20, 20))
    sh.img.alpha_composite(canvas.resize(sh.img.size, Image.BICUBIC))
    for x in range(70, PANEL_W - 50, 44):  # 스프링 구멍
        sh.fill_poly(ellipse_points(x, 48, 5, 6, 12), (140, 132, 136), 220)
    rough_line(sh, [(20, PANEL_H - 20), (PANEL_W - 20, PANEL_H - 20)], 2.0, PENCIL_SOFT, 120, passes=1)
    sh.ink_text('설정', hand(52), PANEL_W / 2, 86, PENCIL, 255, anchor='mm')
    rough_line(sh, [(PANEL_W / 2 - 54, 114), (PANEL_W / 2 + 56, 110)], 3.6, ELEMENT['red'], 235)
    for i, label in enumerate(SETTING_ROWS):
        y = 150 + i * 70
        sh.ink_text(label, hand(34), 80, y, PENCIL, 255, anchor='lm')
        sh.ink_text(label, hand(34), 81.5, y + 1, PENCIL, 90, anchor='lm')
    return sh.result()


def slider_track(filled=False):
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=811 if filled else 812)
    size = (tw, th)
    if filled:
        cols = [ELEMENT['red'], CRAYON['yellow'], ELEMENT['green'], ELEMENT['blue'], CRAYON['lavender']]
        for k, col in enumerate(cols):
            a, b = 6 + (tw - 12) * k / 5, 6 + (tw - 12) * (k + 1) / 5
            crayon(sh, [(a - 3, 11), (b + 3, 12), (b + 3, 25), (a - 3, 24)], col, size=size, coverage=1.0, stroke=4,
                   gap=3, spill=1, angle=-1.2)
    else:
        rough_line(sh, [(8, 18), (tw - 8, 18)], 3.6, PENCIL, 235)
        for x in (8, tw - 8):
            rough_line(sh, [(x, 9), (x, 27)], 3.0, PENCIL, 235, passes=1, overshoot=1)
    return sh.result()


def slider_knob():
    s_ = 44
    sh = Sheet(s_, s_, seed=813)
    disc = wobbly(ellipse_points(s_ / 2, s_ / 2, 12, 12, 20), sh.rng, 1)
    sh.fill_poly(disc, (255, 253, 246), 255)
    rough_shape(sh, disc + [disc[0]], PENCIL, 3.4, 245)
    return sh.result()


def toggle(on):
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=821 if on else 822)
    bx = wobbly([(16, 12), (46, 11), (47, 41), (15, 40)], sh.rng, 1.5)
    sh.fill_poly(bx, (255, 253, 246), 230)
    rough_shape(sh, bx + [bx[0]], PENCIL, 3.4, 240)
    if on:
        rough_line(sh, [(20, 26), (29, 38), (54, 4)], 5, ELEMENT['red'], 255, passes=2, overshoot=3)
    sh.ink_text('켜짐' if on else '꺼짐', hand(28), 90, th / 2, PENCIL if on else PENCIL_SOFT, 255, anchor='mm')
    return sh.result()


# ================================================================ 효과
def bubble(tint, seed):
    sz = 72
    sh = Sheet(sz, sz, seed=seed)
    c, r = sz / 2, 26
    body = wobbly(ellipse_points(c, c, r, r, 24), sh.rng, 1.2)
    sh.fill_poly(body, tint, 70)
    rough_shape(sh, body + body[:3], PENCIL_SOFT, 2.6, 230)
    sh.stroke(ellipse_points(c, c, r - 8, r - 8, 10, math.radians(200), math.radians(60)), 3.6, WHITE, 255, amp=0.4)
    return sh.result()


def mote(kind, seed):
    s_ = 40
    sh = Sheet(s_, s_, seed=seed)
    c = s_ / 2
    if kind in ('pearl', 'gold'):
        star_doodle(sh, c, c, 9, (220, 170, 60) if kind == 'gold' else PENCIL_SOFT, 255, 2.6)
    elif kind == 'pink':
        heart(sh, c, c, 7, (226, 110, 150), 255, 2.4)
    else:
        sh.ellipse(c, c, 5, 5, 2.4, PENCIL_SOFT, 240, amp=0.6)
    return sh.result()


def sparkle():
    s_ = 48
    sh = Sheet(s_, s_, seed=861)
    star_doodle(sh, s_ / 2, s_ / 2, 18, (220, 170, 60), 255, 3.6)
    return sh.result()


def main():
    save(background(), TITLE, 'background.png')
    save(logo(), TITLE, 'logo.png')
    save(empty(), TITLE, 'logo_glow.png')
    save(ink_bottle(), TITLE, 'ink_bottle.png')
    save(bottle_glow(), TITLE, 'bottle_glow.png')
    save(light_pool(), TITLE, 'light_pool.png')
    for name, label, color, seed in (('start', '시작하기', ELEMENT['red'], 881),
                                     ('settings', '설정', ELEMENT['green'], 883),
                                     ('quit', '끝내기', ELEMENT['blue'], 882)):
        save(button(label, color, seed, False), TITLE, f'button_{name}.png')
        save(button(label, color, seed, True), TITLE, f'button_{name}_hover.png')
    for i, (name, tint) in enumerate((('pearl', (255, 250, 240)), ('pink', (255, 206, 224)),
                                      ('lavender', (214, 200, 255)), ('sky', (190, 220, 255)))):
        save(bubble(tint, 840 + i), TITLE, f'bubble_{name}.png')
    for i, name in enumerate(('pearl', 'sky', 'lavender', 'gold', 'pink')):
        save(mote(name, 860 + i), TITLE, f'mote_{name}.png')
    save(sparkle(), TITLE, 'sparkle.png')

    save(Image.new('RGBA', (16, 16), (60, 54, 64, 255)), SETTINGS, 'dim.png')
    save(settings_panel(), SETTINGS, 'panel.png')
    save(slider_track(), SETTINGS, 'slider_track.png')
    save(slider_track(filled=True), SETTINGS, 'slider_fill.png')
    save(slider_knob(), SETTINGS, 'slider_knob.png')
    save(toggle(True), SETTINGS, 'toggle_on.png')
    save(toggle(False), SETTINGS, 'toggle_off.png')
    save(button('닫기', ELEMENT['magenta'], 831, False, (220, 84)), SETTINGS, 'button_close.png')
    save(button('닫기', ELEMENT['magenta'], 831, True, (220, 84)), SETTINGS, 'button_close_hover.png')


if __name__ == '__main__':
    main()
