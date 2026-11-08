"""타이틀·설정 화면 이미지를 PIL로 자동 생성한다 (PRD 9.2 #11: 에셋은 PIL로 자동 생성).

분위기: 깊은 밤, 안개 낀 겹겹의 실루엣, 가운데 잉크통에서 번지는 빛 — 감성적이고 몽환적인 장면을
크레용 낙서 채우기와 분필처럼 빛나는 손그림 선으로 그린다.

실행:  python tools/gen_title_images.py
결과:  image/common/*.png, image/title/*.png, image/settings/*.png, image/prepare/*.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from PIL import ImageFont  # noqa: E402
from sketch import Sheet, paper, bezier, ellipse_points, INK  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, 'image')
FONT_PATH = os.path.join(ROOT, 'fonts', 'GamjaFlower-Regular.ttf')  # 감자꽃체 (OFL, fonts/OFL.txt)


def hand(size):
    """동글동글한 손글씨 폰트. 글자는 PNG에 구워 넣으므로 게임 실행엔 폰트가 필요 없다."""
    return ImageFont.truetype(FONT_PATH, size)
W, H = 1280, 720
LIGHT = (640, 400)  # 잉크통(빛의 근원) 위치, PIL 좌표

WHITE = (255, 255, 255)
CHALK = (226, 232, 255)        # 분필 선
CHALK_DIM = (150, 160, 220)
GLOW_BLUE = (140, 170, 255)
GOLD = (255, 222, 150)
# PRD 잉크 4색 (검정 + 빨·초·파) 과 조합색
ELEMENT = {
    'black': (24, 22, 30),
    'red': (236, 74, 66),
    'green': (78, 200, 100),
    'blue': (70, 132, 244),
    'yellow': (250, 214, 70),
    'cyan': (80, 220, 230),
    'magenta': (226, 90, 210),
}
MOTE = {'white': (250, 250, 255), 'cyan': (140, 230, 255), 'lavender': (200, 170, 255),
        'gold': GOLD, 'pink': (255, 170, 210)}


def save(img, *parts):
    path = os.path.join(IMAGE, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print('saved', os.path.relpath(path, ROOT), img.size)


def poly_mask(size, pts):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


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


def silhouette(sh, outline, fill, scrib, line, alpha_fill=255, gap=8, angle=-0.22, line_alpha=150):
    """낙서로 채운 실루엣 한 겹: 단색 바탕 + 크레용 끄적임 + 분필 윤곽."""
    pts = densify(outline)
    sh.fill_poly(pts, fill, alpha_fill)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    sh.scribble((min(xs), min(ys), max(xs), max(ys)), scrib, alpha=70, gap=gap, angle=angle, width=2.2,
                mask=poly_mask((W, H), pts))
    top = [p for p in pts if p[1] < H - 2 and -10 < p[0] < W + 10]
    sh.stroke_fast(top, 3.0, line, line_alpha, amp=1.2)


# ================================================================ 배경
def night_sky():
    """깊은 남색 → 보라 → 지평선의 푸른 빛, 가운데 잉크통 쪽이 환하다."""
    ys = np.linspace(0, 1, H)[:, None]
    stops = [(0.0, (10, 12, 36)), (0.35, (30, 30, 84)), (0.62, (70, 70, 150)), (1.0, (40, 40, 100))]
    col = np.zeros((H, 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys[:, 0], [s[0] for s in stops], [s[1][c] for s in stops])
    sky = np.repeat(col[:, None, :], W, axis=1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - LIGHT[0]) / 1.4, yy - LIGHT[1])
    glow = np.exp(-(d / 260) ** 2)[..., None] * np.array([120, 130, 170], np.float32)
    halo = np.exp(-(d / 600) ** 2)[..., None] * np.array([40, 30, 70], np.float32)
    rng = np.random.default_rng(1)
    noise = rng.normal(0, 2.5, (H, W, 1)).astype(np.float32)
    return Image.fromarray(np.clip(sky + glow + halo + noise, 0, 255).astype(np.uint8)).convert('RGBA')


def light_rays(sh):
    """잉크통에서 위로 뻗는 빛기둥과 부채꼴 빛줄기."""
    rays = Sheet(W, H, seed=7)
    lx, ly = LIGHT
    rays.fill_poly([(lx - 26, ly), (lx - 70, -10), (lx + 70, -10), (lx + 26, ly)], (210, 220, 255), 70)
    rays.fill_poly([(lx - 10, ly), (lx - 28, -10), (lx + 28, -10), (lx + 10, ly)], WHITE, 90)
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.22 + rays.rng.uniform(-0.05, 0.05)
        wdt = rays.rng.uniform(0.02, 0.05)
        far = 900
        rays.fill_poly([(lx, ly), (lx + math.cos(a - wdt) * far, ly + math.sin(a - wdt) * far),
                        (lx + math.cos(a + wdt) * far, ly + math.sin(a + wdt) * far)], (200, 210, 255), 34)
    rays.img = rays.img.filter(ImageFilter.GaussianBlur(10 * rays.ss))
    sh.img.alpha_composite(rays.img)


def doodle_tree(sh, x, ground, height, crown, fill, line):
    """동글동글 나무 실루엣 낙서."""
    cy = ground - height + crown
    trunk = [(x - 8, ground), (x - 6, cy), (x + 6, cy), (x + 9, ground)]
    sh.fill_poly(trunk, fill)
    pts = []
    bumps = sh.rng.randint(6, 8)
    for i in range(73):
        a = 2 * math.pi * i / 72
        r = crown * (0.88 + 0.14 * abs(math.sin(a * bumps / 2)))
        pts.append((x + math.cos(a) * r, cy + math.sin(a) * r * 0.85))
    sh.fill_poly(pts, fill)
    sh.scribble((x - crown, cy - crown, x + crown, cy + crown), line, alpha=60, gap=7, angle=-0.9,
                mask=poly_mask((W, H), pts))
    sh.stroke(pts, 2.8, line, 170)
    sh.stroke([(x - 8, ground), (x - 6, cy + crown * 0.5)], 2.4, line, 150)


def pine(sh, x, ground, height, width, fill, line):
    tri = []
    for t in range(3):
        b = ground - height * 0.15 - t * height * 0.25
        tp = b - height * 0.4
        hw = width * (1 - t * 0.25)
        tri = [(x - hw, b), (x, tp), (x + hw, b)]
        sh.fill_poly(tri, fill)
        sh.stroke(tri, 2.8, line, 170)
    sh.fill_poly([(x - 5, ground), (x - 5, ground - height * 0.2), (x + 5, ground - height * 0.2), (x + 5, ground)],
                 fill)


def glow_grass(sh, x, y, color):
    """빛나는 풀잎 끝."""
    for dx, lean in ((-5, -0.5), (0, 0.0), (5, 0.45)):
        hgt = sh.rng.uniform(10, 18)
        tip = (x + dx + lean * hgt * 0.8, y - hgt)
        sh.stroke([(x + dx, y), tip], 2.0, CHALK_DIM, 200)
    sh.wash(x + 2, y - 18, 3, 3, color, alpha=255, layers=1, blur=0.6)


def background():
    base = night_sky()
    sh = Sheet(W, H, seed=11)

    # 밤하늘 낙서 결
    for _ in range(7):
        x, y = sh.rng.uniform(0, W), sh.rng.uniform(0, 300)
        sh.scribble((x - 160, y - 50, x + 160, y + 50), (120, 120, 210), alpha=22, gap=11, angle=-0.3, width=2)
    # 별
    for _ in range(90):
        x, y = sh.rng.uniform(0, W), sh.rng.uniform(0, 420)
        r = sh.rng.choice((0.8, 1.0, 1.2, 1.6))
        sh.wash(x, y, r, r, WHITE, alpha=sh.rng.randint(120, 240), layers=1, blur=0.4)
    for _ in range(10):
        star_doodle(sh, sh.rng.uniform(40, W - 40), sh.rng.uniform(30, 330), sh.rng.uniform(5, 9), CHALK, 220, 1.8)

    # 달: 오른쪽 위, 낙서로 칠한 둥근 달과 달무리
    mx, my, mr = 1120, 112, 40
    sh.wash(mx, my, 150, 150, (130, 140, 230), alpha=70, layers=3, edge=0.1, blur=20)
    sh.wash(mx, my, 75, 75, (210, 215, 255), alpha=110, layers=3, edge=0.1, blur=12)
    moon = ellipse_points(mx, my, mr, mr, 60)
    sh.fill_poly(moon, (240, 242, 255))
    sh.scribble((mx - mr, my - mr, mx + mr, my + mr), (200, 205, 240), alpha=150, gap=5, angle=-0.8, width=1.6,
                mask=poly_mask((W, H), moon))
    sh.ellipse(mx, my, mr, mr, 2.6, WHITE, 240, amp=0.6)

    # 먼 겹: 탁자 바위와 뾰족 바위 (안개에 잠겨 연하다)
    far = [(-20, 470), (60, 445), (120, 436), (140, 385), (232, 378), (250, 432), (330, 446), (420, 428),
           (455, 352), (505, 346), (522, 418), (590, 444), (690, 448), (770, 436), (812, 368), (842, 300),
           (868, 296), (884, 366), (930, 424), (1000, 404), (1040, 336), (1122, 330), (1140, 404), (1220, 430),
           (1300, 440), (1300, 720), (-20, 720)]
    far = lumpy(densify(far, 8), 3, sh.rng, 0.2)
    silhouette(sh, far, (88, 88, 168), (120, 124, 210), CHALK_DIM, gap=9, line_alpha=110)
    sh.wash(W / 2, 470, W * 0.6, 50, (225, 228, 255), alpha=60, layers=3, edge=0.1, blur=16)  # 안개

    light_rays(sh)

    # 가운데 겹: 언덕과 바위 기둥
    mid = [(-20, 522), (80, 500), (160, 520), (196, 472), (212, 418), (236, 470), (300, 528), (420, 546),
           (560, 556), (720, 556), (860, 540), (980, 512), (1036, 452), (1060, 446), (1078, 500), (1160, 520),
           (1300, 506), (1300, 720), (-20, 720)]
    mid = lumpy(densify(mid, 8), 4, sh.rng, 0.18)
    silhouette(sh, mid, (52, 50, 118), (84, 84, 168), CHALK_DIM, gap=8, line_alpha=140)
    sh.wash(W / 2, 560, W * 0.6, 40, (200, 205, 255), alpha=45, layers=3, edge=0.1, blur=14)

    # 잉크통 아래 빛 웅덩이
    lx, ly = LIGHT
    sh.wash(lx, ly, 150, 130, WHITE, alpha=110, layers=3, edge=0.0, blur=24)

    # 가까운 겹: 양쪽 절벽 + 가운데 풀 언덕
    left = [(-20, 720), (-20, 382), (40, 372), (110, 398), (168, 466), (226, 556), (296, 640), (340, 720)]
    right = [(1300, 720), (1300, 402), (1238, 392), (1168, 432), (1108, 522), (1040, 620), (990, 720)]
    mound = bezier((300, 720), (380, 600), (520, 598), (640, 600), 30) + \
        bezier((640, 600), (760, 602), (900, 600), (980, 720), 30)[1:]
    for shape in (mound, left, right):
        silhouette(sh, lumpy(densify(shape, 8), 3, sh.rng, 0.2), (22, 20, 52), (48, 46, 104), CHALK, gap=7,
                   angle=-0.3, line_alpha=170)
    # 언덕 윗면을 비추는 빛
    sh.stroke_fast(bezier((400, 628), (520, 600), (760, 600), (880, 628), 40), 4, (210, 220, 255), 170, amp=1.4)
    # 절벽 위 나무 실루엣
    doodle_tree(sh, 70, 378, 150, 52, (22, 20, 52), CHALK)
    doodle_tree(sh, 150, 412, 110, 36, (22, 20, 52), CHALK)
    pine(sh, 1236, 398, 170, 38, (22, 20, 52), CHALK)
    pine(sh, 1180, 420, 120, 28, (22, 20, 52), CHALK)
    # 빛나는 풀과 꽃
    tips = list(MOTE.values())
    for i in range(34):
        side = sh.rng.random()
        if side < 0.5:
            x = sh.rng.uniform(420, 860)
            y = 612 + abs(x - 640) * 0.06 + sh.rng.uniform(-2, 4)
        elif side < 0.75:
            x = sh.rng.uniform(10, 150)
            y = 380 + (x - 40) * 0.25
        else:
            x = sh.rng.uniform(1140, 1270)
            y = 400 + (1238 - x) * 0.25
        glow_grass(sh, x, y, tips[i % len(tips)])

    base.alpha_composite(sh.result())
    # 화면 가장자리 어둡게 (비네트)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vig = np.clip(((xx / W - 0.5) ** 2 * 1.2 + (yy / H - 0.45) ** 2) * 1.6, 0, 1)
    arr = np.asarray(base.convert('RGB'), np.float32) * (1 - vig[..., None] * 0.55)
    return Image.fromarray(arr.astype(np.uint8))


# ================================================================ 로고
def logo():
    """분필로 쓴 'What are you do' + 빨·초·파 크레용으로 칠한 'Ink', 은은한 빛 번짐."""
    lw, lh = 1000, 280
    sh = Sheet(lw, lh, seed=21)
    small = hand(92)
    big = hand(165)
    line = 'What are you do'
    w_small, w_big = small.getlength(line), big.getlength('Ink')
    x0 = (lw - (w_small + 26 + w_big)) / 2
    base_y = 200
    xi = x0 + w_small + 26

    sh.ink_text(line, small, x0, base_y, CHALK, 255, anchor='ls')

    # 'Ink' 글자를 셋으로 나눠 빨·초·파 크레용 칠
    mask_big = sh.text_mask('Ink', big, xi, base_y, anchor='ls').filter(ImageFilter.MaxFilter(7))
    mask = mask_big.resize((lw, lh), Image.BILINEAR)
    fill = Sheet(lw, lh, seed=22)
    keys = ('red', 'green', 'blue')
    for i, key in enumerate(keys):
        bx0 = xi + w_big * i / 3 - (6 if i else 30)
        bx1 = xi + w_big * (i + 1) / 3 + (6 if i < 2 else 30)
        c = ELEMENT[key]
        fill.fill_poly([(bx0, 0), (bx1, 0), (bx1, lh), (bx0, lh)], c, 255)
        light = tuple(min(255, v + 70) for v in c)
        fill.scribble((bx0, 20, bx1, lh - 20), light, alpha=170, gap=6, angle=-1.0, width=2.4)
    sh.masked(fill, mask)
    outline = ImageChops.subtract(mask_big.filter(ImageFilter.MaxFilter(9)), mask_big)
    layer = Image.new('RGBA', sh.img.size, CHALK + (0,))
    layer.putalpha(outline)
    sh.img.alpha_composite(layer)

    # 밑줄 낙서와 별 낙서
    sh.stroke_fast(bezier((x0 + 6, base_y + 26), (x0 + 260, base_y + 16), (xi - 70, base_y + 36), (xi - 6, base_y + 22)),
                   3.4, CHALK, 230)
    sh.stroke_fast(bezier((x0 + 40, base_y + 38), (x0 + 220, base_y + 30), (xi - 120, base_y + 44), (xi - 40, base_y + 36)),
                   2.0, CHALK_DIM, 200)
    for sx, sy, r in ((xi + w_big + 26, base_y - 140, 13), (x0 - 18, base_y - 80, 9), (xi - 30, base_y - 150, 7),
                      (xi + w_big * 0.5, base_y + 30, 6)):
        star_doodle(sh, sx, sy, r, GOLD, 255, 2.6)
    for key, (sx, sy) in zip(keys, ((xi - 4, base_y - 130), (xi + w_big * 0.6, base_y + 28), (xi + w_big + 14, base_y - 96))):
        sh.splatter(sx, sy, 20, ELEMENT[key], count=4, size=(1.8, 4.5))
    sh.add_glow(GLOW_BLUE, blur=10, strength=0.9)
    return sh.result(crop=True, margin=16)


def soft_glow(w, h, color, seed, alpha=170):
    """로고·잉크통 뒤에서 숨 쉬듯 깜빡이는 빛."""
    sh = Sheet(w, h, seed=seed)
    sh.wash(w / 2, h / 2, w * 0.38, h * 0.36, color, alpha=alpha, layers=4, edge=0.1, blur=18)
    sh.wash(w / 2, h / 2, w * 0.2, h * 0.2, WHITE, alpha=110, layers=3, edge=0.1, blur=14)
    return sh.result()


# ================================================================ 컬러 잉크통 (모래시계)
def ink_bottle():
    """모래시계 잉크통. 위 칸에 빨·초·파가 층층이, 아래 칸에 검정 잉크가 고여 있다."""
    bw, bh = 220, 320
    cx = bw / 2
    sh = Sheet(bw, bh, seed=41)
    top, bottom = 46, 274
    neck = (top + bottom) / 2
    left = bezier((cx - 78, top), (cx - 86, top + 80), (cx - 14, neck - 30), (cx - 9, neck), 40) + \
        bezier((cx - 9, neck), (cx - 14, neck + 30), (cx - 86, bottom - 80), (cx - 78, bottom), 40)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask((bw, bh), left + right[::-1])

    glass = Sheet(bw, bh, seed=42)
    glass.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (200, 214, 255), 70)  # 유리 속 빛

    def band(y0, y1, color):
        """물결 진 경계로 나뉜 잉크 한 층 + 크레용 결."""
        wave_top = [(x, y0 + 3 * math.sin(x / 13 + y0)) for x in range(0, bw + 1, 8)]
        wave_bot = [(x, y1 + 3 * math.sin(x / 13 + y1)) for x in range(bw, -1, -8)]
        pts = wave_top + wave_bot
        glass.fill_poly(pts, color, 255)
        hi = tuple(min(255, v + 80) for v in color) if color != ELEMENT['black'] else (90, 88, 110)
        glass.scribble((0, y0 - 4, bw, y1 + 4), hi, alpha=150, gap=5, angle=-0.5, width=1.8,
                       mask=poly_mask((bw, bh), pts))

    # 위 칸: 빨 / 초 / 파 세 층 (목 쪽이 아래)
    band(top + 24, top + 54, ELEMENT['red'])
    band(top + 54, top + 82, ELEMENT['green'])
    band(top + 82, neck + 2, ELEMENT['blue'])
    # 목에서 떨어지는 검정 줄기
    glass.stroke([(cx, neck), (cx + 1, neck + 30), (cx, bottom - 50)], 3.2, ELEMENT['black'], 255, amp=0.4)
    # 아래 칸: 검정 잉크 더미
    pile = bezier((0, bottom - 34), (cx - 40, bottom - 40), (cx - 16, bottom - 66), (cx, bottom - 64), 20) + \
        bezier((cx, bottom - 64), (cx + 16, bottom - 66), (cx + 40, bottom - 40), (bw, bottom - 34), 20)[1:] + \
        [(bw, bh), (0, bh)]
    glass.fill_poly(pile, ELEMENT['black'], 255)
    glass.scribble((0, bottom - 70, bw, bottom), (90, 88, 110), alpha=150, gap=5, angle=-0.5, width=1.8,
                   mask=poly_mask((bw, bh), pile))
    sh.masked(glass, inner)

    # 유리 윤곽(분필)과 반사광
    sh.stroke(left, 4.0, CHALK)
    sh.stroke(right, 4.0, CHALK)
    sh.stroke(bezier((cx - 56, top + 18), (cx - 64, top + 56), (cx - 42, top + 88), (cx - 28, top + 98), 20),
              3.2, WHITE, 230, amp=0.5)
    sh.stroke(bezier((cx - 58, bottom - 80), (cx - 64, bottom - 96), (cx - 54, bottom - 108), (cx - 46, bottom - 114), 12),
              2.6, WHITE, 200, amp=0.5)
    # 뚜껑·받침: 나무 낙서
    for y, d in ((top, -1), (bottom, 1)):
        y0, y1 = (y - 26, y + 2) if d < 0 else (y - 2, y + 26)
        box = [(cx - 96, y0), (cx + 96, y0 + 1), (cx + 98, y1), (cx - 95, y1 - 1)]
        sh.fill_poly(box, (120, 92, 84), 255)
        sh.scribble((cx - 98, y0, cx + 98, y1), (190, 150, 130), alpha=200, gap=5, angle=-1.1, width=1.8,
                    mask=poly_mask((bw, bh), box))
        sh.stroke(box + [box[0]], 3.6, CHALK)
    for x in (cx - 88, cx + 88):
        sh.stroke([(x, top + 2), (x + 1, bottom - 2)], 3.6, CHALK)
    sh.add_glow((190, 210, 255), blur=9, strength=1.0)
    return sh.result(crop=True, margin=12)


def light_pool():
    """잉크통 아래 언덕에 비치는 빛."""
    sh = Sheet(280, 70, seed=45)
    sh.wash(140, 35, 110, 16, (210, 225, 255), alpha=170, layers=3, edge=0.1, blur=7)
    return sh.result()


# ================================================================ 버튼 · 설정 UI
def chalk_box(sh, x0, y0, x1, y1, r=14):
    return bezier((x0 + r, y0), (x0 + 80, y0 - 3), (x1 - 80, y0 + 3), (x1 - r, y0), 30) + \
        bezier((x1 - r, y0), (x1 + 2, y0), (x1 + 2, y0 + 2), (x1, y0 + r), 6)[1:] + \
        [(x1 + 1, (y0 + y1) / 2), (x1, y1 - r)] + \
        bezier((x1, y1 - r), (x1, y1 + 1), (x1 - 2, y1 + 1), (x1 - r, y1), 6)[1:] + \
        bezier((x1 - r, y1), (x1 - 80, y1 + 3), (x0 + 80, y1 - 2), (x0 + r, y1), 30)[1:] + \
        bezier((x0 + r, y1), (x0 - 1, y1), (x0 - 1, y1 - 2), (x0, y1 - r), 6)[1:] + \
        [(x0 - 1, (y0 + y1) / 2), (x0, y0 + r)] + \
        bezier((x0, y0 + r), (x0, y0 - 1), (x0 + 2, y0 - 1), (x0 + r + 10, y0 - 1), 6)[1:]


def button(label, color, seed, hover, size=(280, 92)):
    """분필로 그린 버튼. hover 면 원소 색 크레용으로 칠해지고 빛난다."""
    bw, bh = size
    sh = Sheet(bw, bh, seed=seed)
    x0, y0, x1, y1 = 18, 16, bw - 18, bh - 16
    box = chalk_box(sh, x0, y0, x1, y1)
    m = poly_mask((bw, bh), box)
    fill = Sheet(bw, bh, seed=seed + 1)
    fill.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (16, 16, 44), 170)
    if hover:
        fill.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], color, 150)
        fill.scribble((0, 0, bw, bh), tuple(min(255, v + 60) for v in color), alpha=200, gap=6, angle=-0.4, width=2.4)
    else:
        fill.scribble((0, 0, bw, bh), (70, 72, 140), alpha=120, gap=8, angle=-0.4, width=2)
    sh.masked(fill, m)
    sh.stroke(box, 3.6, CHALK)
    sh.stroke_fast([(x0 + 22, y1 + 6), (x1 - 8, y1 + 5)], 1.8, CHALK_DIM, 170)
    if hover:
        star_doodle(sh, x1 - 2, y0 + 2, 9, GOLD, 255, 2.4)
    f = hand(37)
    sh.ink_text(label, f, bw / 2, bh / 2, WHITE, 255, anchor='mm')
    if hover:
        sh.add_glow(color, blur=7, strength=0.8)
    return sh.result()


PANEL_W, PANEL_H = 680, 500
SETTING_ROWS = ('배경음', '효과음', '붓자국 효과', '빛 입자 효과')


def settings_panel():
    """설정 창 바탕: 제목과 항목 이름을 미리 써 둔다. 행 위치는 settings_mode.ROW_Y 와 맞춘다."""
    sh = Sheet(PANEL_W, PANEL_H, seed=201)
    box = chalk_box(sh, 20, 20, PANEL_W - 20, PANEL_H - 20, r=22)
    m = poly_mask((PANEL_W, PANEL_H), box)
    fill = Sheet(PANEL_W, PANEL_H, seed=202)
    fill.fill_poly([(0, 0), (PANEL_W, 0), (PANEL_W, PANEL_H), (0, PANEL_H)], (14, 14, 40), 235)
    fill.scribble((0, 0, PANEL_W, PANEL_H), (50, 52, 110), alpha=110, gap=9, angle=-0.5, width=2)
    sh.masked(fill, m)
    sh.stroke(box, 4, CHALK)
    sh.ink_text('설정', hand(50), PANEL_W / 2, 64, WHITE, 255, anchor='mm')
    sh.stroke_fast([(PANEL_W / 2 - 60, 94), (PANEL_W / 2 + 60, 92)], 2.4, GOLD, 230)
    star_doodle(sh, PANEL_W / 2 + 76, 50, 9, GOLD, 255, 2.2)
    f = hand(35)
    for i, label in enumerate(SETTING_ROWS):
        sh.ink_text(label, f, 70, 150 + i * 70, CHALK, 255, anchor='lm')
    sh.add_glow(GLOW_BLUE, blur=10, strength=0.6)
    return sh.result()


def slider_track(fill_color=None):
    """슬라이더 막대. fill_color 가 있으면 채워진 쪽(크레용 칠)."""
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=211 if fill_color else 212)
    pts = chalk_box(sh, 4, 10, tw - 4, th - 10, r=8)
    if fill_color:
        sh.fill_poly(pts, fill_color, 220)
        sh.scribble((0, 0, tw, th), tuple(min(255, v + 70) for v in fill_color), alpha=200, gap=5, angle=-1.0,
                    width=1.8, mask=poly_mask((tw, th), pts))
    else:
        sh.fill_poly(pts, (30, 30, 70), 220)
    sh.stroke(pts, 2.6, CHALK)
    return sh.result()


def slider_knob():
    s = 44
    sh = Sheet(s, s, seed=213)
    pts = ellipse_points(s / 2, s / 2, 12, 12, 30)
    sh.fill_poly(pts, (250, 250, 255))
    sh.scribble((8, 8, s - 8, s - 8), (190, 200, 240), alpha=200, gap=4, width=1.4, mask=poly_mask((s, s), pts))
    sh.ellipse(s / 2, s / 2, 12, 12, 2.6, CHALK_DIM, 255, amp=0.4)
    sh.add_glow(GOLD, blur=4, strength=1.0)
    return sh.result()


def toggle(on):
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=221 if on else 222)
    pts = chalk_box(sh, 6, 8, tw - 6, th - 8, r=16)
    m = poly_mask((tw, th), pts)
    if on:
        sh.fill_poly(pts, ELEMENT['cyan'], 200)
        sh.scribble((0, 0, tw, th), (190, 250, 255), alpha=180, gap=5, angle=-0.9, width=1.8, mask=m)
    else:
        sh.fill_poly(pts, (30, 30, 70), 220)
    sh.stroke(pts, 2.8, CHALK)
    kx = tw - 30 if on else 30
    sh.fill_poly(ellipse_points(kx, th / 2, 13, 13, 24), WHITE if on else (150, 156, 200))
    sh.ellipse(kx, th / 2, 13, 13, 2.2, CHALK_DIM, 255, amp=0.3)
    f = hand(22)
    sh.ink_text('켜짐' if on else '꺼짐', f, 48 if on else tw - 48, th / 2, (20, 30, 60) if on else CHALK, 255,
                anchor='mm')
    if on:
        sh.add_glow(ELEMENT['cyan'], blur=5, strength=0.7)
    return sh.result()


# ================================================================ 효과용 작은 이미지
def mote(color, seed):
    """빛 입자(반딧불) : 번진 빛 + 밝은 심지."""
    s = 40
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 12, 12, color, alpha=170, layers=2, edge=0.05, blur=5)
    sh.wash(s / 2, s / 2, 4, 4, WHITE, alpha=255, layers=1, edge=0.05, blur=1.2)
    return sh.result()


def sparkle():
    s = 48
    sh = Sheet(s, s, seed=55)
    sh.wash(s / 2, s / 2, 10, 10, GOLD, alpha=170, layers=2, edge=0.1, blur=5)
    star_doodle(sh, s / 2, s / 2, 18, WHITE, 255, 3)
    star_doodle(sh, s / 2, s / 2, 10, GOLD, 255, 2)
    return sh.result()


def ink_drop(color, seed):
    """클릭하면 튀는 원소 색 잉크 얼룩 (크레용 결 + 빛)."""
    s = 128
    sh = Sheet(s, s, seed=seed)
    blob = []
    for i in range(37):
        a = 2 * math.pi * i / 36
        r = 26 * (1 + 0.18 * math.sin(3 * a + seed) + 0.1 * math.sin(7 * a + seed * 2))
        blob.append((s / 2 + math.cos(a) * r, s / 2 + math.sin(a) * r))
    sh.fill_poly(blob, color, 245)
    sh.scribble((20, 20, s - 20, s - 20), tuple(min(255, v + 80) for v in color), alpha=170, gap=5, width=1.8,
                mask=poly_mask((s, s), blob))
    sh.splatter(s / 2, s / 2, 44, color, count=9, size=(2, 5), alpha=245)
    sh.add_glow(color, blur=5, strength=0.9)
    return sh.result()


def brush_dot(color, seed):
    s = 32
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 8, 8, color, alpha=200, layers=2, edge=0.1, blur=3)
    sh.wash(s / 2, s / 2, 3, 3, WHITE, alpha=255, layers=1, edge=0.1, blur=1)
    return sh.result()


def cursor_pen():
    """분필로 그린 깃펜 커서. 펜촉 끝이 이미지 왼쪽 아래 (6, 58)."""
    s = 64
    sh = Sheet(s, s, seed=61)
    tip = (6, 58)
    feather = bezier((18, 46), (22, 20), (40, 6), (60, 3), 20) + bezier((60, 3), (56, 24), (40, 42), (20, 48), 20)[1:]
    sh.fill_poly(feather, (40, 40, 90), 230)
    sh.scribble((16, 2, 62, 50), (150, 170, 255), alpha=200, gap=4, width=1.4, mask=poly_mask((s, s), feather))
    sh.stroke(feather, 2.4, CHALK, amp=0.4, taper=False)
    sh.stroke(bezier((20, 46), (30, 34), (44, 18), (58, 5), 16), 1.6, CHALK, amp=0.3)
    sh.stroke([(20, 46), tip], 4.0, WHITE, amp=0.2)
    sh.wash(tip[0] + 2, tip[1] - 2, 3, 3, GOLD, alpha=255, layers=1, blur=0.5)
    sh.add_glow(GLOW_BLUE, blur=3, strength=0.8)
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
    save(soft_glow(1000, 320, (120, 140, 255), 23, alpha=150), 'title', 'logo_glow.png')
    save(ink_bottle(), 'title', 'ink_bottle.png')
    save(soft_glow(380, 440, (190, 205, 255), 43, alpha=200), 'title', 'bottle_glow.png')
    save(light_pool(), 'title', 'light_pool.png')
    for name, label, color, seed in (('start', '시작하기', ELEMENT['red'], 81),
                                     ('settings', '설정', ELEMENT['green'], 83),
                                     ('quit', '끝내기', ELEMENT['blue'], 82)):
        save(button(label, color, seed, False), 'title', f'button_{name}.png')
        save(button(label, color, seed, True), 'title', f'button_{name}_hover.png')
    for i, name in enumerate(MOTE):
        save(mote(MOTE[name], 300 + i), 'title', f'mote_{name}.png')
        save(brush_dot(MOTE[name], 320 + i), 'common', f'brush_dot_{name}.png')
    save(sparkle(), 'title', 'sparkle.png')
    for i, name in enumerate(('red', 'green', 'blue', 'yellow', 'cyan', 'magenta')):
        save(ink_drop(ELEMENT[name], 90 + i), 'common', f'ink_drop_{name}.png')
    save(cursor_pen(), 'common', 'cursor_pen.png')

    save(Image.new('RGBA', (16, 16), (6, 6, 20, 255)), 'settings', 'dim.png')  # 알파 채널이 있어야 opacify가 먹는다
    save(settings_panel(), 'settings', 'panel.png')
    save(slider_track(), 'settings', 'slider_track.png')
    save(slider_track(ELEMENT['blue']), 'settings', 'slider_fill.png')
    save(slider_knob(), 'settings', 'slider_knob.png')
    save(toggle(True), 'settings', 'toggle_on.png')
    save(toggle(False), 'settings', 'toggle_off.png')
    save(button('닫기', ELEMENT['magenta'], 231, False, (220, 84)), 'settings', 'button_close.png')
    save(button('닫기', ELEMENT['magenta'], 231, True, (220, 84)), 'settings', 'button_close_hover.png')

    save(prepare_wip(), 'prepare', 'wip_text.png')


if __name__ == '__main__':
    main()
