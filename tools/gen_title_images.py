"""타이틀·설정 화면 이미지를 PIL로 자동 생성한다 (PRD 9.2 #11: 에셋은 PIL로 자동 생성).

분위기: 밝고 몽환적인 낮. 분홍·라벤더 안개로 통일된 색조, 해를 등진 거대한 고목,
겹겹이 흐려지는 길쭉한 나무 실루엣, 비스듬한 빛줄기, 가운데 빛나는 모래시계 잉크통.
그림은 옅은 색연필 선 + 은은한 크레용 낙서 결. 로고는 얇고 하얀 심플한 글씨 + 빛나는 붓 획 하나.

실행:  python tools/gen_title_images.py
결과:  image/common/*.png, image/title/*.png, image/settings/*.png, image/prepare/*.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, paper, bezier, ellipse_points, INK  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, 'image')
FONT_PATH = os.path.join(ROOT, 'fonts', 'GamjaFlower-Regular.ttf')  # UI 손글씨: 감자꽃체
TITLE_FONT = os.path.join(ROOT, 'fonts', 'Quicksand.ttf')  # 로고: Quicksand (가변 굵기)
UI_FONT = os.path.join(ROOT, 'fonts', 'GowunDodum-Regular.ttf')  # 버튼 한글: 고운돋움 (로고처럼 둥글고 가늘다)
# 폰트 라이선스는 모두 SIL OFL 1.1 (fonts/OFL-*.txt)
W, H = 1280, 720
LIGHT = (640, 400)  # 잉크통(빛의 근원) 위치, PIL 좌표
SUN = (990, 205)    # 고목 뒤의 해

WHITE = (255, 255, 255)
LINE = (92, 78, 134)        # UI 색연필 선 (안개 톤에 어울리는 자두빛 보라)
LINE_SOFT = (150, 134, 190)
GOLD = (250, 200, 90)
# PRD 잉크 4색 (검정 + 빨·초·파) 과 조합색
ELEMENT = {
    'black': (26, 24, 32),
    'red': (236, 84, 74),
    'green': (84, 190, 104),
    'blue': (74, 136, 238),
    'yellow': (246, 204, 64),
    'cyan': (70, 200, 214),
    'magenta': (216, 92, 200),
}
# 빛 입자(밝은 배경에서도 보이게 은은한 색 + 흰 심지) / 붓자국 색
LIGHT_COLORS = {'pearl': (255, 250, 236), 'sky': (150, 200, 255), 'lavender': (196, 176, 255),
                'gold': (255, 214, 120), 'pink': (255, 176, 206)}


def hand(size):
    """동글동글한 손글씨 폰트. 글자는 PNG에 구워 넣으므로 게임 실행엔 폰트가 필요 없다."""
    return ImageFont.truetype(FONT_PATH, size)


def save(img, *parts):
    path = os.path.join(IMAGE, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print('saved', os.path.relpath(path, ROOT), img.size)


def poly_mask(size, pts):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def lighter(c, k=60):
    return tuple(min(255, v + k) for v in c)


def darker(c, k=0.6):
    return tuple(int(v * k) for v in c)


def lumpy(points, amp, rng, freq=0.08):
    """윤곽선을 울퉁불퉁하게."""
    out = []
    ph1, ph2 = rng.uniform(0, 6), rng.uniform(0, 6)
    n = len(points)
    for i, (px, py) in enumerate(points):
        j0, j1 = max(0, i - 1), min(n - 1, i + 1)
        dx, dy = points[j1][0] - points[j0][0], points[j1][1] - points[j0][1]
        ln = math.hypot(dx, dy) or 1
        k = math.sin(i * freq + ph1) * 0.6 + math.sin(i * freq * 2.7 + ph2) * 0.4
        k *= min(1.0, i / 6, (n - 1 - i) / 6)
        out.append((px - dy / ln * amp * k, py + dx / ln * amp * k))
    return out


def densify(pts, step=6):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n)]
    return out + [pts[-1]]


def star_doodle(sh, x, y, r, color, alpha=230, width=2.2):
    """네 갈래 반짝이 낙서."""
    sh.stroke([(x, y - r), (x + r * 0.15, y), (x, y + r)], width, color, alpha, amp=0.2)
    sh.stroke([(x - r, y), (x, y + r * 0.15), (x + r, y)], width, color, alpha, amp=0.2)


def layer(sh, outline, fill, line, gap=8, angle=-0.25, line_alpha=200, scrib_alpha=70, width=3.0):
    """낙서로 채운 풍경 한 겹: 단색 바탕 + 밝은 크레용 끄적임 + 색연필 윤곽."""
    pts = densify(outline)
    sh.fill_poly(pts, fill, 255)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    sh.scribble((min(xs), min(ys), max(xs), max(ys)), lighter(fill, 40), alpha=scrib_alpha, gap=gap, angle=angle,
                width=2.2, mask=poly_mask((W, H), pts))
    top = [p for p in pts if p[1] < H - 2 and -10 < p[0] < W + 10]
    sh.stroke_fast(top, width, line, line_alpha, amp=1.2)


# ================================================================ 배경
def day_sky():
    """라벤더 → 분홍 → 지평선의 흰빛. 고목 뒤의 해와 잉크통 쪽이 하얗게 빛난다."""
    ys = np.linspace(0, 1, H)
    stops = [(0.0, (190, 182, 226)), (0.3, (220, 198, 230)), (0.5, (244, 214, 230)),
             (0.66, (252, 232, 236)), (1.0, (236, 222, 236))]
    col = np.zeros((H, 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys, [s_[0] for s_ in stops], [s_[1][c] for s_ in stops])
    sky = np.repeat(col[:, None, :], W, axis=1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for (gx, gy), rad, k in ((SUN, 260, 0.95), (LIGHT, 230, 0.7)):
        d = np.hypot(xx - gx, yy - gy)
        g = np.exp(-(d / rad) ** 2)[..., None] * k
        sky = sky * (1 - g) + np.array([255, 252, 246], np.float32) * g
    grain = np.asarray(paper(W, H, seed=3).convert('RGB'), np.float32)[..., :1] / 247.0
    return Image.fromarray(np.clip(sky * (0.6 + 0.4 * grain), 0, 255).astype(np.uint8)).convert('RGBA')


def haze(sh, y_top, y_bottom, color=(252, 240, 248), alpha=150):
    """깊이 안개: y_bottom 쪽이 가장 짙고 위로 갈수록 옅어지는 띠."""
    hz = np.zeros((H * sh.ss, W * sh.ss, 4), np.uint8)
    ys = np.arange(H * sh.ss, dtype=np.float32) / sh.ss
    k = np.clip((ys - y_top) / max(1, (y_bottom - y_top)), 0, 1)
    k = np.where(ys > y_bottom, np.clip(1 - (ys - y_bottom) / 80, 0, 1), k) ** 1.3
    hz[..., :3] = color
    hz[..., 3] = (k * alpha).astype(np.uint8)[:, None]
    sh.img.alpha_composite(Image.fromarray(hz, 'RGBA'))


def mist_streak(sh, x, y, w, h, alpha=110):
    """가로로 길게 번진 안개 구름."""
    sh.wash(x, y, w, h, (255, 246, 250), alpha=alpha, layers=3, edge=0.0, blur=12, wobble=0.25)


def tall_tree(sh, cx, ground, height, width, fill, line, line_alpha=110, rim=True):
    """길쭉한 나무 (위가 뾰족한 잎 모양) — 안개 속에서 겹겹이 선다."""
    top = ground - height
    lean = sh.rng.uniform(-6, 6)
    left = bezier((cx, ground), (cx - width * 1.1, ground - height * 0.25),
                  (cx - width * 0.9, top + height * 0.25), (cx + lean, top), 30)
    right = bezier((cx + lean, top), (cx + width * 0.9, top + height * 0.25),
                   (cx + width * 1.1, ground - height * 0.25), (cx, ground), 30)[1:]
    pts = left + right
    sh.fill_poly(pts, fill)
    sh.scribble((cx - width * 1.2, top, cx + width * 1.2, ground), lighter(fill, 26), alpha=70, gap=6, angle=-1.2,
                mask=poly_mask((W, H), pts))
    if rim:  # 해 쪽(오른쪽)에서 받는 빛
        sh.stroke(right[2:-8], 2.6, (255, 244, 240), 150, amp=0.6)
    sh.stroke(pts, 1.8, line, line_alpha, amp=0.8)
    sh.fill_poly([(cx - 3, ground + 6), (cx - 3, ground - 4), (cx + 3, ground - 4), (cx + 3, ground + 6)], darker(fill, 0.85))


def great_tree(sh):
    """해를 등진 거대한 고목. 안개에 반쯤 잠겨 아득하다."""
    tx, ground = SUN[0], 470
    fill, line = (196, 178, 222), (176, 158, 210)
    trunk = bezier((tx - 70, ground), (tx - 40, ground - 90), (tx - 34, ground - 170), (tx - 22, ground - 230), 20) + \
        bezier((tx + 22, ground - 230), (tx + 34, ground - 170), (tx + 40, ground - 90), (tx + 74, ground), 20)
    sh.fill_poly(trunk, fill)
    for bx, by, ex, ey in ((tx - 20, ground - 220, tx - 120, ground - 300), (tx + 18, ground - 224, tx + 130, ground - 296),
                           (tx, ground - 228, tx + 10, ground - 330)):
        sh.stroke([(bx, by), ((bx + ex) / 2 + 8, (by + ey) / 2), (ex, ey)], 16, fill, 255, amp=2, taper=True)
    # 수관: 겹친 둥근 덩어리들
    blobs = [(0, -300, 150), (-140, -270, 105), (140, -275, 110), (-70, -380, 110), (80, -380, 115),
             (-220, -230, 70), (225, -235, 72), (0, -440, 85)]
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    for bx, by, r in blobs:
        d.ellipse((tx + bx - r, ground + by - r * 0.85, tx + bx + r, ground + by + r * 0.85), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.5))
    f = Sheet(W, H, seed=33)
    f.fill_poly([(0, 0), (W, 0), (W, H), (0, H)], fill, 255)
    f.scribble((tx - 320, ground - 560, tx + 320, ground - 120), lighter(fill, 24), alpha=80, gap=7, angle=-0.8, width=2)
    sh.masked(f, m)
    arr = np.asarray(m) > 100
    edge = []
    for px in range(max(0, tx - 300), min(W, tx + 300), 3):
        col = arr[:, px]
        if col.any():
            edge.append((px, int(col.argmax()) + 1))
    sh.stroke_fast(edge, 2.0, line, 120, amp=1.0)
    sh.stroke_fast(trunk[:21], 1.8, line, 110)
    sh.stroke_fast(trunk[21:], 1.8, line, 110)


def light_rays(sh):
    """해에서 비스듬히 내리는 빛줄기 + 잉크통에서 위로 오르는 가는 빛기둥."""
    rays = Sheet(W, H, seed=7)
    sx, sy = SUN
    for k in range(8):
        a = math.pi * 0.62 + (k - 3.5) * 0.09 + rays.rng.uniform(-0.03, 0.03)
        wdt = rays.rng.uniform(0.02, 0.05)
        far = 1200
        rays.fill_poly([(sx, sy), (sx + math.cos(a - wdt) * far, sy + math.sin(a - wdt) * far),
                        (sx + math.cos(a + wdt) * far, sy + math.sin(a + wdt) * far)],
                       (255, 250, 244), rays.rng.randint(26, 46))
    lx, ly = LIGHT
    rays.fill_poly([(lx - 14, ly), (lx - 46, -10), (lx + 46, -10), (lx + 14, ly)], WHITE, 70)
    rays.img = rays.img.filter(ImageFilter.GaussianBlur(18 * rays.ss))
    sh.img.alpha_composite(rays.img)


def flower(sh, x, y, color):
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        sh.wash(x + math.cos(a) * 3.4, y + math.sin(a) * 3.4, 2.6, 2.6, color, alpha=235, layers=1, blur=0.6)
    sh.wash(x, y, 1.6, 1.6, (255, 236, 170), alpha=255, layers=1, blur=0.4)


def grass(sh, x, y, color):
    for dx, lean in ((-5, -0.5), (0, 0.0), (5, 0.45)):
        hgt = sh.rng.uniform(9, 16)
        sh.stroke([(x + dx, y), (x + dx + lean * hgt * 0.8, y - hgt)], 1.8, color, 190)


def bloom(img, radius=28, strength=0.5):
    """밝은 곳이 주변으로 번지는 빛 (스크린 합성)."""
    a = np.asarray(img.convert('RGB'), np.float32) / 255
    bright = np.clip((a - 0.6) / 0.4, 0, 1)
    b_img = Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    b = np.asarray(b_img, np.float32) / 255 * strength
    out = 1 - (1 - a) * (1 - b)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def background():
    base = day_sky()
    sh = Sheet(W, H, seed=11)

    # 하늘의 안개 구름
    for x, y, w, h in ((200, 120, 260, 26), (520, 70, 200, 16), (760, 150, 220, 20), (1180, 90, 160, 16),
                       (360, 250, 240, 18), (1100, 330, 260, 22)):
        mist_streak(sh, x, y, w, h, 120)

    # 아주 먼 산등성이
    far = [(-20, 400), (120, 360), (240, 380), (380, 330), (520, 384), (660, 400), (780, 372), (900, 396),
           (1080, 360), (1200, 380), (1300, 368), (1300, 720), (-20, 720)]
    layer(sh, lumpy(densify(far, 8), 4, sh.rng, 0.15), (222, 206, 234), (206, 190, 226), gap=10, line_alpha=90,
          scrib_alpha=50, width=2.0)
    haze(sh, 300, 420, (252, 242, 248), 150)

    great_tree(sh)
    haze(sh, 220, 470, (252, 242, 248), 120)
    light_rays(sh)

    # 먼 숲 (라벤더빛, 아득하게)
    far_fill, far_line = (200, 184, 224), (184, 168, 216)
    hill = [(-20, 470), (200, 452), (420, 470), (640, 480), (860, 470), (1080, 456), (1300, 466), (1300, 720), (-20, 720)]
    layer(sh, lumpy(densify(hill, 8), 3, sh.rng, 0.2), far_fill, far_line, gap=9, line_alpha=80, scrib_alpha=45,
          width=1.8)
    for i in range(26):
        x = -10 + i * 52 + sh.rng.uniform(-14, 14)
        if 520 < x < 760:
            continue
        tall_tree(sh, x, 472 + sh.rng.uniform(-6, 6), sh.rng.uniform(70, 140), sh.rng.uniform(14, 22),
                  (196 + sh.rng.randint(-6, 6), 180, 222), far_line, 80)
    haze(sh, 400, 520, (252, 242, 248), 140)

    # 가운데 숲 (보랏빛 청록, 조금 더 또렷)
    mid_fill, mid_line = (168, 160, 206), (146, 138, 194)
    mid = [(-20, 540), (160, 520), (360, 540), (640, 556), (920, 540), (1120, 516), (1300, 530), (1300, 720), (-20, 720)]
    layer(sh, lumpy(densify(mid, 8), 3, sh.rng, 0.18), mid_fill, mid_line, gap=8, line_alpha=100, width=2.0)
    for x in list(range(-10, 470, 44)) + list(range(830, 1300, 44)):
        x += sh.rng.uniform(-12, 12)
        tall_tree(sh, x, 540 + sh.rng.uniform(-8, 8), sh.rng.uniform(120, 220), sh.rng.uniform(20, 32),
                  (164 + sh.rng.randint(-8, 8), 156, 204), mid_line, 100)
    haze(sh, 480, 600, (252, 240, 248), 120)

    # 잉크통 둘레 따뜻한 빛
    lx, ly = LIGHT
    sh.wash(lx, ly, 170, 150, (255, 250, 244), alpha=150, layers=3, edge=0.0, blur=26)

    # 가까운 겹: 양쪽 큰 나무 무리 + 가운데 꽃 언덕
    near_fill, near_line = (132, 160, 162), (96, 124, 138)
    mound = bezier((300, 720), (380, 604), (520, 600), (640, 602), 30) + \
        bezier((640, 602), (760, 604), (900, 602), (980, 720), 30)[1:]
    layer(sh, lumpy(densify(mound, 8), 3, sh.rng, 0.2), (186, 200, 196), (130, 150, 160), gap=7, angle=-0.3,
          line_alpha=150, width=2.2)
    left = [(-20, 720), (-20, 470), (80, 470), (180, 510), (260, 590), (330, 720)]
    right = [(1300, 720), (1300, 480), (1200, 476), (1100, 520), (1030, 600), (980, 720)]
    for shape in (left, right):
        layer(sh, lumpy(densify(shape, 8), 3, sh.rng, 0.2), near_fill, near_line, gap=7, angle=-0.3,
              line_alpha=150, width=2.2)
    for x, g, hgt, wdt in ((20, 480, 380, 52), (96, 486, 300, 44), (170, 520, 220, 34), (230, 580, 150, 26),
                           (1262, 488, 400, 56), (1186, 486, 310, 46), (1110, 530, 220, 34), (1050, 600, 150, 26)):
        tall_tree(sh, x, g, hgt, wdt, (124 + sh.rng.randint(-6, 6), 156, 158), near_line, 150)
    # 언덕 위 빛, 풀, 꽃
    sh.stroke_fast(bezier((400, 630), (520, 604), (760, 604), (880, 630), 40), 3.0, (255, 248, 244), 210, amp=1.2)
    petals = [(255, 255, 255), (255, 206, 222), (226, 210, 255), (255, 236, 200)]
    for i in range(54):
        side = sh.rng.random()
        if side < 0.6:
            x = sh.rng.uniform(410, 870)
            y = 616 + abs(x - 640) * 0.08 + sh.rng.uniform(0, 70)
        elif side < 0.8:
            x = sh.rng.uniform(0, 240)
            y = sh.rng.uniform(600, 715)
        else:
            x = sh.rng.uniform(1040, 1280)
            y = sh.rng.uniform(600, 715)
        if sh.rng.random() < 0.6:
            flower(sh, x, y, petals[i % len(petals)])
        else:
            grass(sh, x, y, (92, 118, 128))
    # 공기 중에 떠 있는 빛 알갱이
    for _ in range(80):
        x, y = sh.rng.uniform(0, W), sh.rng.uniform(40, 640)
        r = sh.rng.uniform(1.2, 3.0)
        sh.wash(x, y, r * 2.5, r * 2.5, (255, 248, 240), alpha=90, layers=1, edge=0.0, blur=2)
        sh.wash(x, y, r, r, WHITE, alpha=230, layers=1, edge=0.0, blur=0.5)

    base.alpha_composite(sh.result())
    return bloom(base, radius=30, strength=0.6)


# ================================================================ 로고
def title_font(size, weight):
    f = ImageFont.truetype(TITLE_FONT, size)
    f.set_variation_by_axes([weight])
    return f


def _text_mask(sheet, text, size, weight, x, baseline, spacing=0, anchor_center=True):
    """자간을 조절한 글자 마스크 (시트 크기, ss 배율). 너비(원래 단위)도 함께 돌려준다."""
    ss = sheet.ss
    f = title_font(int(size * ss), weight)
    widths = [f.getlength(ch) for ch in text]
    total = sum(widths) + spacing * ss * (len(text) - 1)
    px = x * ss - (total / 2 if anchor_center else 0)
    m = Image.new('L', sheet.img.size, 0)
    d = ImageDraw.Draw(m)
    for ch, wch in zip(text, widths):
        d.text((px, baseline * ss), ch, font=f, fill=255, anchor='ls')
        px += wch + spacing * ss
    return m, total / ss


def _solid(sheet, mask, color, alpha=255, offset=(0, 0)):
    m = ImageChops.offset(mask, int(offset[0]), int(offset[1]))
    if alpha < 255:
        m = m.point(lambda v: v * alpha // 255)
    lay = Image.new('RGBA', sheet.img.size, tuple(color) + (0,))
    lay.putalpha(m)
    sheet.img.alpha_composite(lay)


def logo():
    """심플한 흰 로고.
    - 윗줄: 자간 넓은 'WHAT ARE YOU DO'
    - 아랫줄: 얇은 'Ink'
    - 'k' 를 비스듬히 가로지르는 빛나는 붓 획 하나 (끝에 잉크 방울)
    - 그 아래 빨·초·파 작은 잉크 점 세 개
    """
    lw, lh = 560, 300
    sh = Sheet(lw, lh, seed=21)
    cx = lw / 2
    m_small, w_small = _text_mask(sh, 'WHAT ARE YOU DO', 28, 400, cx, 70, spacing=9)
    m_big, w_big = _text_mask(sh, 'Ink', 168, 300, cx, 214, spacing=6)
    union = ImageChops.lighter(m_small, m_big)

    # 은은한 그림자(밝은 하늘 위 가독성) + 흰 글씨
    _solid(sh, union.filter(ImageFilter.GaussianBlur(8 * sh.ss)), (120, 96, 168), 120, (0, 3 * sh.ss))
    _solid(sh, union, WHITE)

    # 붓 획: 오른쪽 위에서 왼쪽 아래로, 점점 가늘어지며 'k' 를 지나간다
    x1, y1 = cx + w_big / 2 + 46, 92
    x0, y0 = cx + w_big / 2 - 120, 236
    n = 60
    for i in range(n + 1):
        t = i / n
        x = x1 + (x0 - x1) * t
        y = y1 + (y0 - y1) * t + math.sin(t * math.pi) * 6
        r = 3.4 * (1 - t) ** 0.8 + 0.4
        sh.wash(x, y, r, r, WHITE, alpha=255, layers=1, edge=0.0, blur=0.3)
    sh.wash(x1 + 2, y1 - 4, 4.6, 5.4, WHITE, alpha=255, layers=1, edge=0.0, blur=0.4)  # 붓을 댄 자리의 방울
    star_doodle(sh, x1 + 2, y1 - 4, 14, WHITE, 255, 1.6)

    # 아래쪽 잉크 점 셋
    for k, key in enumerate(('red', 'green', 'blue')):
        dx = cx + (k - 1) * 26
        sh.wash(dx, 252, 5, 5, ELEMENT[key], alpha=255, layers=1, edge=0.1, blur=0.4)
        sh.wash(dx - 1.5, 250.5, 1.4, 1.4, WHITE, alpha=200, layers=1, blur=0.3)

    sh.add_glow((255, 248, 255), blur=6, strength=1.3)
    return sh.result(crop=True, margin=14)


def soft_glow(w, h, color, seed, alpha=170):
    """로고·잉크통 뒤에서 숨 쉬듯 깜빡이는 빛."""
    sh = Sheet(w, h, seed=seed)
    sh.wash(w / 2, h / 2, w * 0.38, h * 0.36, color, alpha=alpha, layers=4, edge=0.0, blur=18)
    sh.wash(w / 2, h / 2, w * 0.2, h * 0.2, WHITE, alpha=130, layers=3, edge=0.0, blur=14)
    return sh.result()


# ================================================================ 컬러 잉크통 (모래시계)
def ink_bottle():
    """모래시계 잉크통 — 투명한 유리, 진주빛 원반 뚜껑, 가는 금빛 기둥.
    위 칸: 별빛이 떠 있는 밤하늘 같은 검정 잉크 / 아래 칸: 서로 스며든 빨·초·파 층."""
    bw, bh = 230, 340
    cx = bw / 2
    sh = Sheet(bw, bh, seed=41)
    ss = sh.ss
    top, bottom = 58, 282
    neck = (top + bottom) / 2
    left = bezier((cx - 74, top), (cx - 84, top + 80), (cx - 13, neck - 30), (cx - 8, neck), 40) + \
        bezier((cx - 8, neck), (cx - 13, neck + 30), (cx - 84, bottom - 80), (cx - 74, bottom), 40)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask((bw, bh), left + right[::-1])
    pearl, gold, lav = (252, 246, 242), (232, 198, 128), (176, 156, 222)

    # ---- 뒤쪽 기둥 (유리 뒤로 비침)
    sh.stroke([(cx, top - 4), (cx, bottom + 4)], 2.4, lighter(lav, 40), 150, amp=0.2, taper=False)

    # ---- 유리 안
    glass = Sheet(bw, bh, seed=42)
    glass.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (244, 240, 255), 90)

    # 위 칸: 깊은 남보라 검정 + 별빛
    surf = top + 34
    black = Sheet(bw, bh, seed=43)
    ys = np.arange(bh * ss, dtype=np.float32)[:, None] / ss
    k = np.clip((ys - surf) / (neck - surf), 0, 1)
    arr = np.zeros((bh * ss, bw * ss, 4), np.uint8)
    for c_, (a, b) in enumerate(zip((70, 60, 110), (26, 22, 40))):
        arr[..., c_] = (a + (b - a) * k).astype(np.uint8)
    arr[..., 3] = np.where((ys >= surf) & (ys <= neck + 2), 255, 0).astype(np.uint8)
    black.img = Image.fromarray(arr, 'RGBA')
    black.draw = ImageDraw.Draw(black.img)
    for _ in range(14):
        sx_, sy_ = black.rng.uniform(cx - 50, cx + 50), black.rng.uniform(surf + 6, neck - 20)
        r_ = black.rng.uniform(0.6, 1.5)
        black.wash(sx_, sy_, r_, r_, WHITE, alpha=230, layers=1, edge=0.0, blur=0.3)
    star_doodle(black, cx + 20, surf + 22, 5, (255, 236, 190), 255, 1.2)
    star_doodle(black, cx - 28, surf + 44, 3.5, WHITE, 255, 1.0)
    glass.img.alpha_composite(black.img)
    # 잉크 표면의 둥근 빛 (메니스커스)
    glass.stroke(ellipse_points(cx, surf, 62, 6, 30, 0, math.pi), 1.8, (150, 136, 200), 220, amp=0.2)
    # 떨어지는 가는 검정 줄기
    glass.stroke([(cx, neck), (cx, bottom - 58)], 2.0, (40, 34, 60), 230, amp=0.15, taper=False)

    # 아래 칸: 빨·초·파가 수채화처럼 서로 스며든 더미
    pile = Sheet(bw, bh, seed=44)
    mound_top = bottom - 62
    # 빨강은 위로 넉넉히 칠한 뒤 더미 모양으로 자른다
    layers_ = ((mound_top - 24, bottom - 40, ELEMENT['red']), (bottom - 40, bottom - 20, ELEMENT['green']),
               (bottom - 20, bh, ELEMENT['blue']))
    for y0, y1, col in layers_:
        soft = lighter(col, 24)
        pile.fill_poly([(0, y0), (bw, y0), (bw, y1 + 4), (0, y1 + 4)], soft, 255)
    pile.img = pile.img.filter(ImageFilter.GaussianBlur(3 * ss))
    pile.draw = ImageDraw.Draw(pile.img)
    mound = bezier((0, mound_top + 8), (cx - 40, mound_top + 6), (cx - 18, mound_top - 12), (cx, mound_top - 12), 20) + \
        bezier((cx, mound_top - 12), (cx + 18, mound_top - 12), (cx + 40, mound_top + 6), (bw, mound_top + 8), 20)[1:] + \
        [(bw, bh), (0, bh)]
    mound_mask = poly_mask((bw, bh), mound).filter(ImageFilter.GaussianBlur(1))
    r_, g_, b_, a_ = pile.img.split()
    pile.img = Image.merge('RGBA', (r_, g_, b_, ImageChops.multiply(a_, mound_mask.resize(pile.img.size))))
    # 아주 은은한 크레용 결과 반짝임
    pile.draw = ImageDraw.Draw(pile.img)
    pile.scribble((0, mound_top - 14, bw, bottom), WHITE, alpha=50, gap=6, angle=-0.4, width=1.4,
                  mask=mound_mask)
    for _ in range(8):
        pile.wash(pile.rng.uniform(cx - 50, cx + 50), pile.rng.uniform(mound_top, bottom - 6), 1.0, 1.0, WHITE,
                  alpha=220, layers=1, blur=0.3)
    glass.img.alpha_composite(pile.img)
    sh.masked(glass, inner)

    # ---- 유리 윤곽: 옅은 보랏빛 바깥선 + 흰 빛 선
    sh.stroke(left, 3.6, lav, 170, amp=0.3)
    sh.stroke(right, 3.6, lav, 170, amp=0.3)
    sh.stroke(left, 2.0, WHITE, 255, amp=0.3)
    sh.stroke(right, 2.0, WHITE, 255, amp=0.3)
    sh.stroke(bezier((cx - 56, top + 14), (cx - 64, top + 52), (cx - 44, top + 84), (cx - 30, top + 94), 20),
              3.0, WHITE, 240, amp=0.3)
    sh.stroke(bezier((cx + 50, top + 22), (cx + 56, top + 40), (cx + 52, top + 56), (cx + 46, top + 66), 10),
              1.6, WHITE, 200, amp=0.2)
    sh.stroke(bezier((cx - 58, bottom - 84), (cx - 64, bottom - 98), (cx - 56, bottom - 110), (cx - 48, bottom - 116), 12),
              2.4, WHITE, 220, amp=0.3)

    # ---- 앞 기둥 둘: 가는 진주빛 막대 + 금빛 마디
    for x in (cx - 90, cx + 90):
        sh.stroke([(x, top - 4), (x, bottom + 4)], 4.2, lav, 120, amp=0.2, taper=False)
        sh.stroke([(x, top - 4), (x, bottom + 4)], 2.6, pearl, 255, amp=0.2, taper=False)
        for yy in (top + 24, neck, bottom - 24):
            sh.wash(x, yy, 3.4, 3.4, gold, alpha=255, layers=1, edge=0.1, blur=0.4)

    # ---- 진주빛 원반 뚜껑·받침 (위아래)
    for y, d in ((top - 8, -1), (bottom + 8, 1)):
        disc = Image.new('L', sh.img.size, 0)
        dd = ImageDraw.Draw(disc)
        dd.ellipse([(cx - 104) * ss, (y - 12) * ss, (cx + 104) * ss, (y + 12) * ss], fill=255)
        dd.rectangle([(cx - 104) * ss, min(y, y + 8 * d) * ss, (cx + 104) * ss, max(y, y + 8 * d) * ss], fill=255)
        dd.ellipse([(cx - 104) * ss, (y + 8 * d - 12) * ss, (cx + 104) * ss, (y + 8 * d + 12) * ss], fill=255)
        lay = Image.new('RGBA', sh.img.size, pearl + (0,))
        lay.putalpha(disc)
        sh.img.alpha_composite(lay)
        # 옆면 그늘과 윗면 빛
        sh.wash(cx, y + 8 * d + 4 * d, 96, 6, (214, 200, 240), alpha=150, layers=1, edge=0.0, blur=2)
        face_y = y if d < 0 else y + 8 * d
        sh.stroke(ellipse_points(cx, face_y - 8 * (d < 0), 100, 10, 40), 1.6, gold, 255, amp=0.2, taper=False)
        sh.stroke(ellipse_points(cx, y + 8 * d * (d < 0) + (8 if d > 0 else 0), 104, 12, 40, 0, math.pi), 1.4,
                  lav, 200, amp=0.2, taper=False)
        sh.wash(cx - 40, face_y - 8 * (d < 0) - 2, 34, 3, WHITE, alpha=200, layers=1, blur=1.5)
    # 뚜껑 위 작은 장식 별
    star_doodle(sh, cx, top - 34, 9, gold, 255, 1.8)
    sh.wash(cx, top - 34, 2.2, 2.2, WHITE, alpha=255, layers=1, blur=0.3)

    sh.add_glow(WHITE, blur=10, strength=1.5)
    return sh.result(crop=True, margin=12)


def light_pool():
    """잉크통 아래 언덕에 비치는 빛."""
    sh = Sheet(280, 70, seed=45)
    sh.wash(140, 35, 110, 16, (255, 252, 230), alpha=200, layers=3, edge=0.0, blur=7)
    return sh.result()


# ================================================================ 버튼 · 설정 UI
def doodle_box(x0, y0, x1, y1, r=14):
    return bezier((x0 + r, y0), (x0 + 80, y0 - 3), (x1 - 80, y0 + 3), (x1 - r, y0), 30) + \
        bezier((x1 - r, y0), (x1 + 2, y0), (x1 + 2, y0 + 2), (x1, y0 + r), 6)[1:] + \
        [(x1 + 1, (y0 + y1) / 2), (x1, y1 - r)] + \
        bezier((x1, y1 - r), (x1, y1 + 1), (x1 - 2, y1 + 1), (x1 - r, y1), 6)[1:] + \
        bezier((x1 - r, y1), (x1 - 80, y1 + 3), (x0 + 80, y1 - 2), (x0 + r, y1), 30)[1:] + \
        bezier((x0 + r, y1), (x0 - 1, y1), (x0 - 1, y1 - 2), (x0, y1 - r), 6)[1:] + \
        [(x0 - 1, (y0 + y1) / 2), (x0, y0 + r)] + \
        bezier((x0, y0 + r), (x0, y0 - 1), (x0 + 2, y0 - 1), (x0 + r + 10, y0 - 1), 6)[1:]


def ui_font(size):
    return ImageFont.truetype(UI_FONT, size)


def _rounded(size, box, r, ss):
    m = Image.new('L', (size[0] * ss, size[1] * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([v * ss for v in box], radius=r * ss, fill=255)
    return m


def _put(sheet, mask, color, alpha=255):
    if alpha < 255:
        mask = mask.point(lambda v: v * alpha // 255)
    lay = Image.new('RGBA', sheet.img.size, tuple(color) + (0,))
    lay.putalpha(mask)
    sheet.img.alpha_composite(lay)


def button(label, color, seed, hover, size=(260, 84), on_paper=False):
    """로고와 같은 결의 버튼: 반투명 유리 알약 + 얇은 흰 테두리 + 흰 글씨.
    hover 면 안쪽이 환해지고 빛이 번지며, 글자 앞 원소 색 점이 또렷해진다.
    on_paper: 흰 설정 창 위에 놓일 버튼이라 테두리·글씨를 자두빛으로."""
    edge = LINE if on_paper else WHITE
    bw, bh = size
    sh = Sheet(bw, bh, seed=seed)
    ss = sh.ss
    box = (22, 20, bw - 22, bh - 20)
    r = (box[3] - box[1]) / 2
    outer = _rounded(size, box, r, ss)
    inner = _rounded(size, (box[0] + 1.6, box[1] + 1.6, box[2] - 1.6, box[3] - 1.6), r - 1.6, ss)
    ring = ImageChops.subtract(outer, inner)

    # 밝은 배경 위에서도 보이도록 자두빛 그림자를 아주 옅게
    _put(sh, outer.filter(ImageFilter.GaussianBlur(6 * ss)), (120, 96, 168), 70 if hover else 50)
    _put(sh, inner, (236, 226, 252) if on_paper else WHITE, (200 if hover else 120) if on_paper else (120 if hover else 46))
    # 위쪽 유리 반사
    shine = _rounded(size, (box[0] + 10, box[1] + 4, box[2] - 10, (box[1] + box[3]) / 2 - 2), r * 0.6, ss)
    _put(sh, shine.filter(ImageFilter.GaussianBlur(2 * ss)), WHITE, 70 if hover else 40)
    _put(sh, ring, edge, 255)

    f = ui_font(26)
    big = ImageFont.truetype(UI_FONT, 26 * ss)
    tw = big.getlength(label) / ss
    tx = bw / 2 + 7
    text = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(text).text((tx * ss, bh / 2 * ss), label, font=big, fill=255, anchor='mm')
    if not on_paper:
        _put(sh, text.filter(ImageFilter.GaussianBlur(3 * ss)), (110, 86, 160), 120)
    _put(sh, text, edge)
    # 글자 앞 원소 색 점 (로고의 빨·초·파 점과 짝)
    dx = tx - tw / 2 - 14
    sh.wash(dx, bh / 2, 4.2, 4.2, color, alpha=255 if hover else 200, layers=1, edge=0.1, blur=0.4)
    sh.wash(dx - 1.2, bh / 2 - 1.2, 1.2, 1.2, WHITE, alpha=210, layers=1, blur=0.3)
    if hover:
        star_doodle(sh, box[2] - 6, box[1] + 2, 8, GOLD if on_paper else WHITE, 255, 1.6)
        star_doodle(sh, box[0] + 10, box[3] - 2, 5, GOLD if on_paper else WHITE, 255, 1.4)
        sh.add_glow((255, 248, 255), blur=8, strength=1.4)
    else:
        sh.add_glow((255, 248, 255), blur=5, strength=0.6)
    return sh.result()


PANEL_W, PANEL_H = 680, 500
SETTING_ROWS = ('배경음', '효과음', '붓자국 효과', '빛 입자 효과')


def _gradient_bar(w, h, ss, colors):
    """왼쪽에서 오른쪽으로 colors 를 이어 그린 가로 그라데이션 (RGBA, ss 크기)."""
    xs = np.linspace(0, 1, w * ss)
    n = len(colors) - 1
    arr = np.zeros((h * ss, w * ss, 4), np.uint8)
    for c in range(3):
        arr[..., c] = np.interp(xs, np.linspace(0, 1, n + 1), [col[c] for col in colors]).astype(np.uint8)[None, :]
    arr[..., 3] = 255
    return Image.fromarray(arr, 'RGBA')


GLASS_GRADIENT = [(250, 150, 200), (250, 214, 112), (130, 214, 182), (122, 180, 246), (176, 140, 240)]


def settings_panel():
    """설정 창 바탕: 반투명 유리 + 얇은 흰 테두리 + 흰 글씨. 행 위치는 settings_mode.ROW_Y 와 맞춘다."""
    sh = Sheet(PANEL_W, PANEL_H, seed=201)
    ss = sh.ss
    box = (24, 24, PANEL_W - 24, PANEL_H - 24)
    outer = _rounded((PANEL_W, PANEL_H), box, 30, ss)
    inner = _rounded((PANEL_W, PANEL_H), (box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2), 28, ss)
    _put(sh, outer.filter(ImageFilter.GaussianBlur(10 * ss)), (90, 70, 150), 90)          # 바깥 그늘
    _put(sh, inner, (236, 228, 255), 120)                                                   # 유리
    tint = Sheet(PANEL_W, PANEL_H, seed=203)
    tint.wash(PANEL_W * 0.2, PANEL_H * 0.15, 220, 140, (255, 214, 236), alpha=70, layers=2, edge=0.0, blur=20)
    tint.wash(PANEL_W * 0.85, PANEL_H * 0.9, 240, 150, (196, 214, 255), alpha=70, layers=2, edge=0.0, blur=20)
    sh.masked(tint, inner.resize((PANEL_W, PANEL_H)))
    shine = _rounded((PANEL_W, PANEL_H), (box[0] + 16, box[1] + 8, box[2] - 16, box[1] + 70), 24, ss)
    _put(sh, shine.filter(ImageFilter.GaussianBlur(6 * ss)), WHITE, 50)                     # 윗면 반사
    _put(sh, ImageChops.subtract(outer, inner), WHITE, 255)                                 # 얇은 흰 테두리
    ring2 = ImageChops.subtract(
        _rounded((PANEL_W, PANEL_H), (box[0] + 8, box[1] + 8, box[2] - 8, box[3] - 8), 22, ss),
        _rounded((PANEL_W, PANEL_H), (box[0] + 9, box[1] + 9, box[2] - 9, box[3] - 9), 21, ss))
    _put(sh, ring2, WHITE, 90)                                                              # 안쪽 가는 선

    def white_text(text, f, x, y, anchor):
        big = ImageFont.truetype(f.path, f.size * ss)
        m = Image.new('L', sh.img.size, 0)
        ImageDraw.Draw(m).text((x * ss, y * ss), text, font=big, fill=255, anchor=anchor)
        _put(sh, m.filter(ImageFilter.GaussianBlur(3 * ss)), (96, 76, 150), 130)
        _put(sh, m, WHITE)

    white_text('설정', ui_font(36), PANEL_W / 2, 66, 'mm')
    sh.stroke([(PANEL_W / 2 - 46, 94), (PANEL_W / 2 + 46, 94)], 1.4, WHITE, 230, amp=0.1)
    star_doodle(sh, PANEL_W / 2 + 62, 52, 8, WHITE, 255, 1.6)
    for i, label in enumerate(SETTING_ROWS):
        white_text(label, ui_font(26), 76, 150 + i * 70, 'lm')
        sh.wash(60, 150 + i * 70, 3, 3, GLASS_GRADIENT[i + 1], alpha=255, layers=1, edge=0.1, blur=0.4)
    sh.add_glow((255, 248, 255), blur=8, strength=0.7)
    return sh.result()


def slider_track(filled=False):
    """슬라이더 막대. 빈 쪽은 가는 흰 선, 채워진 쪽은 무지갯빛 그라데이션 빛 선."""
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=211 if filled else 212)
    ss = sh.ss
    if filled:
        bar = _rounded((tw, th), (6, 14, tw - 6, th - 14), 4, ss)
        grad = _gradient_bar(tw, th, ss, GLASS_GRADIENT)
        glow = Image.new('RGBA', sh.img.size, (0, 0, 0, 0))
        g = grad.copy()
        g.putalpha(bar.filter(ImageFilter.GaussianBlur(4 * ss)).point(lambda v: v * 200 // 255))
        glow.alpha_composite(g)
        grad.putalpha(bar)
        glow.alpha_composite(grad)
        sh.img.alpha_composite(glow)
        core = _rounded((tw, th), (8, 17, tw - 8, th - 17), 1, ss)
        _put(sh, core, WHITE, 200)
    else:
        bar = _rounded((tw, th), (6, 16, tw - 6, th - 16), 2, ss)
        _put(sh, bar.filter(ImageFilter.GaussianBlur(2 * ss)), (96, 76, 150), 70)
        _put(sh, bar, WHITE, 170)
    return sh.result()


def slider_knob():
    s_ = 44
    sh = Sheet(s_, s_, seed=213)
    ss = sh.ss
    m = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(m).ellipse([10 * ss, 10 * ss, 34 * ss, 34 * ss], fill=255)
    _put(sh, m.filter(ImageFilter.GaussianBlur(4 * ss)), (200, 170, 255), 200)
    _put(sh, m, (252, 248, 255))
    sh.ellipse(s_ / 2, s_ / 2, 12, 12, 1.4, (190, 170, 236), 230, amp=0.1)
    sh.wash(s_ / 2 - 4, s_ / 2 - 4, 3, 3, WHITE, alpha=255, layers=1, blur=0.4)
    return sh.result()


def toggle(on):
    """유리 알약 토글. 켜지면 분홍→라벤더 빛으로 물들고 손잡이가 오른쪽으로."""
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=221 if on else 222)
    ss = sh.ss
    box = (10, 10, tw - 10, th - 10)
    outer = _rounded((tw, th), box, 16, ss)
    inner = _rounded((tw, th), (box[0] + 1.6, box[1] + 1.6, box[2] - 1.6, box[3] - 1.6), 14.4, ss)
    _put(sh, outer.filter(ImageFilter.GaussianBlur(4 * ss)), (96, 76, 150), 60)
    if on:
        grad = _gradient_bar(tw, th, ss, [(250, 160, 206), (176, 140, 240)])
        grad.putalpha(inner.point(lambda v: v * 220 // 255))
        sh.img.alpha_composite(grad)
    else:
        _put(sh, inner, WHITE, 50)
    _put(sh, ImageChops.subtract(outer, inner), WHITE, 255)
    kx = tw - 30 if on else 30
    knob = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(knob).ellipse([(kx - 11) * ss, (th / 2 - 11) * ss, (kx + 11) * ss, (th / 2 + 11) * ss], fill=255)
    if on:
        _put(sh, knob.filter(ImageFilter.GaussianBlur(4 * ss)), WHITE, 220)
    _put(sh, knob, WHITE, 255 if on else 170)
    f = ImageFont.truetype(UI_FONT, 17 * ss)
    m = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(m).text(((50 if on else tw - 50) * ss, th / 2 * ss), '켜짐' if on else '꺼짐', font=f, fill=255,
                           anchor='mm')
    _put(sh, m, WHITE, 255 if on else 200)
    return sh.result()


# ================================================================ 효과용 작은 이미지
def mote(color, seed):
    """빛 입자 : 번진 빛 + 밝은 심지."""
    s = 40
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 12, 12, color, alpha=190, layers=2, edge=0.0, blur=5)
    sh.wash(s / 2, s / 2, 4, 4, WHITE, alpha=255, layers=1, edge=0.0, blur=1.2)
    return sh.result()


def sparkle():
    s = 48
    sh = Sheet(s, s, seed=55)
    sh.wash(s / 2, s / 2, 10, 10, (255, 236, 170), alpha=200, layers=2, edge=0.0, blur=5)
    star_doodle(sh, s / 2, s / 2, 18, GOLD, 255, 3.2)
    star_doodle(sh, s / 2, s / 2, 10, WHITE, 255, 2)
    return sh.result()


def ink_drop(color, seed):
    """클릭하면 튀는 원소 색 잉크 얼룩 (크레용 결)."""
    s = 128
    sh = Sheet(s, s, seed=seed)
    blob = []
    for i in range(37):
        a = 2 * math.pi * i / 36
        r = 26 * (1 + 0.18 * math.sin(3 * a + seed) + 0.1 * math.sin(7 * a + seed * 2))
        blob.append((s / 2 + math.cos(a) * r, s / 2 + math.sin(a) * r))
    sh.fill_poly(blob, color, 245)
    sh.scribble((20, 20, s - 20, s - 20), lighter(color, 80), alpha=170, gap=5, width=1.8,
                mask=poly_mask((s, s), blob))
    sh.splatter(s / 2, s / 2, 44, color, count=9, size=(2, 5), alpha=245)
    sh.add_glow(WHITE, blur=4, strength=1.2)
    return sh.result()


def bubble(tint, seed):
    """비눗방울: 거의 투명한 몸통 + 무지갯빛 얇은 테두리 + 흰 반사광."""
    sz = 72
    sh = Sheet(sz, sz, seed=seed)
    ss = sh.ss
    c, r = sz / 2, 28
    body = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(body).ellipse([(c - r) * ss, (c - r) * ss, (c + r) * ss, (c + r) * ss], fill=255)
    _put(sh, body, tint, 60)
    # 가장자리로 갈수록 진해지는 막 (안쪽은 비어 보이게)
    soft = body.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(5 * ss))
    _put(sh, ImageChops.subtract(body, soft), tint, 230)
    sh.ellipse(c, c, r, r, 1.4, (150, 128, 196), 120, amp=0.1)
    # 무지갯빛 테두리: 위는 분홍, 오른쪽 하늘색, 아래 연노랑
    for a0, a1, col in ((200, 320, (255, 190, 220)), (320, 420, (170, 210, 255)), (60, 200, (255, 236, 180))):
        pts = ellipse_points(c, c, r - 1, r - 1, 30, math.radians(a0), math.radians(a1 - a0))
        sh.stroke(pts, 2.4, col, 255, amp=0.1, taper=False)
    sh.stroke(ellipse_points(c, c, r - 7, r - 7, 14, math.radians(200), math.radians(60)), 3.2, WHITE, 240, amp=0.1)
    sh.wash(c + 12, c + 12, 2.4, 2.4, WHITE, alpha=230, layers=1, blur=0.4)
    return sh.result()


# 커서 빛 선 그라데이션: 이 색들을 순서대로 돌며 사이를 보간한다
TRAIL_STOPS = [(250, 150, 200), (255, 186, 146), (250, 214, 112), (130, 214, 182), (122, 180, 246), (176, 140, 240)]
TRAIL_STEPS = 12


def trail_colors():
    out = []
    n = len(TRAIL_STOPS)
    for i in range(TRAIL_STEPS):
        t = i / TRAIL_STEPS * n
        a, b = TRAIL_STOPS[int(t) % n], TRAIL_STOPS[(int(t) + 1) % n]
        f = t - int(t)
        out.append(tuple(int(a[c] + (b[c] - a[c]) * f) for c in range(3)))
    return out


def trail_segment(color, seed):
    """커서 빛 선 조각: 가로로 길쭉, 가운데는 하얗고 가장자리가 color 로 번진다."""
    w, h = 64, 24
    sh = Sheet(w, h, seed=seed)
    ss = sh.ss
    m = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 7 * ss, w * ss, 17 * ss], radius=5 * ss, fill=255)
    _put(sh, m.filter(ImageFilter.GaussianBlur(3 * ss)), color, 255)
    core = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(core).rounded_rectangle([0, 10.5 * ss, w * ss, 13.5 * ss], radius=1.5 * ss, fill=255)
    _put(sh, core, WHITE, 230)
    return sh.result()


def trail_cap(color, seed):
    """빛 선 조각 사이 이음매를 메우는 둥근 점 (같은 색)."""
    s_ = 24
    sh = Sheet(s_, s_, seed=seed)
    ss = sh.ss
    m = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(m).ellipse([7 * ss, 7 * ss, 17 * ss, 17 * ss], fill=255)
    _put(sh, m.filter(ImageFilter.GaussianBlur(3 * ss)), color, 255)
    core = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(core).ellipse([10.5 * ss, 10.5 * ss, 13.5 * ss, 13.5 * ss], fill=255)
    _put(sh, core, WHITE, 230)
    return sh.result()


def cursor_pen():
    """깃펜 커서. 펜촉 끝이 이미지 왼쪽 아래 (6, 58)."""
    s = 64
    sh = Sheet(s, s, seed=61)
    tip = (6, 58)
    feather = bezier((18, 46), (22, 20), (40, 6), (60, 3), 20) + bezier((60, 3), (56, 24), (40, 42), (20, 48), 20)[1:]
    sh.fill_poly(feather, WHITE, 255)
    sh.scribble((16, 2, 62, 50), (200, 186, 255), alpha=200, gap=4, width=1.4, mask=poly_mask((s, s), feather))
    sh.stroke(feather, 2.4, LINE, amp=0.4, taper=False)
    sh.stroke(bezier((20, 46), (30, 34), (44, 18), (58, 5), 16), 1.6, LINE, amp=0.3)
    sh.stroke([(20, 46), tip], 4.0, LINE, amp=0.2)
    sh.wash(tip[0] + 2, tip[1] - 2, 3, 3, ELEMENT['black'], alpha=255, layers=1, blur=0.5)
    sh.add_glow(WHITE, blur=3, strength=1.4)
    return sh.result()


def hint_theme():
    """그림체 바꾸기 안내: 키캡 '←' '→' + 글씨. 어느 그림체 위에서도 보이게 반투명 남보라 바탕.
    화살표는 글꼴에 없을 수 있어 세모로 그린다."""
    w, h = 214, 40
    sh = Sheet(w, h, seed=901)
    ss = sh.ss
    plum = (70, 58, 110)
    _put(sh, _rounded((w, h), (2, 2, w - 2, h - 2), 18, ss), plum, 150)
    for kx, d in ((10, -1), (38, 1)):  # 키캡 두 개
        _put(sh, _rounded((w, h), (kx, 8, kx + 24, 32), 6, ss), WHITE, 235)
        cx, cy = kx + 12, 20
        tri = [(cx + d * 6, cy), (cx - d * 4, cy - 6), (cx - d * 4, cy + 6)]
        m = Image.new('L', sh.img.size, 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in tri], fill=255)
        _put(sh, m, plum)
    f = ImageFont.truetype(UI_FONT, 18 * ss)
    m = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(m).text((70 * ss, 20.5 * ss), '그림체 바꾸기', font=f, fill=255, anchor='lm')
    _put(sh, m, WHITE)
    return sh.result()


def prepare_wip():
    sw, sh_h = 900, 160
    sh = Sheet(sw, sh_h, seed=71)
    sh.ink_text('준비 화면', hand(67), sw / 2, 52, INK, 255, anchor='mm')
    sh.ink_text('틀을 고르고 유닛을 그리는 곳 — 다음 단계에서 만들어요', hand(32), sw / 2, 112,
                (80, 76, 82), 255, anchor='mm')
    sh.ink_text('ESC : 타이틀로', hand(27), sw / 2, 146, (120, 118, 124), 255, anchor='mm')
    return sh.result()


def main():
    save(paper(W, H, seed=5).convert('RGB'), 'common', 'paper.png')
    save(background(), 'title', 'background.png')
    save(logo(), 'title', 'logo.png')
    save(soft_glow(620, 360, (255, 246, 252), 23, alpha=150), 'title', 'logo_glow.png')
    save(ink_bottle(), 'title', 'ink_bottle.png')
    save(soft_glow(380, 440, (255, 248, 220), 43, alpha=210), 'title', 'bottle_glow.png')
    save(light_pool(), 'title', 'light_pool.png')
    for name, label, color, seed in (('start', '시작하기', ELEMENT['red'], 81),
                                     ('settings', '설정', ELEMENT['green'], 83),
                                     ('quit', '끝내기', ELEMENT['blue'], 82)):
        save(button(label, color, seed, False), 'title', f'button_{name}.png')
        save(button(label, color, seed, True), 'title', f'button_{name}_hover.png')
    for i, name in enumerate(LIGHT_COLORS):
        save(mote(LIGHT_COLORS[name], 300 + i), 'title', f'mote_{name}.png')
    save(sparkle(), 'title', 'sparkle.png')
    for i, (name, tint) in enumerate((('pearl', (255, 246, 236)), ('pink', (255, 200, 224)),
                                      ('lavender', (210, 196, 255)), ('sky', (186, 216, 255)))):
        save(bubble(tint, 340 + i), 'title', f'bubble_{name}.png')
    for i, c in enumerate(trail_colors()):
        save(trail_segment(c, 350 + i), 'common', f'trail_segment_{i}.png')
        save(trail_cap(c, 370 + i), 'common', f'trail_cap_{i}.png')
    for i, name in enumerate(('red', 'green', 'blue', 'yellow', 'cyan', 'magenta')):
        save(ink_drop(ELEMENT[name], 90 + i), 'common', f'ink_drop_{name}.png')
    save(cursor_pen(), 'common', 'cursor_pen.png')

    save(Image.new('RGBA', (16, 16), (92, 72, 146, 255)), 'settings', 'dim.png')  # 알파 채널이 있어야 opacify가 먹는다
    save(settings_panel(), 'settings', 'panel.png')
    save(slider_track(), 'settings', 'slider_track.png')
    save(slider_track(filled=True), 'settings', 'slider_fill.png')
    save(slider_knob(), 'settings', 'slider_knob.png')
    save(toggle(True), 'settings', 'toggle_on.png')
    save(toggle(False), 'settings', 'toggle_off.png')
    save(button('닫기', ELEMENT['magenta'], 231, False, (220, 84)), 'settings', 'button_close.png')
    save(button('닫기', ELEMENT['magenta'], 231, True, (220, 84)), 'settings', 'button_close_hover.png')

    save(hint_theme(), 'common', 'hint_theme.png')
    save(prepare_wip(), 'prepare', 'wip_text.png')


if __name__ == '__main__':
    main()
