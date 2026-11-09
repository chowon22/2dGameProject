"""처음 파스텔 수채화 타이틀 배경(git cd3721a 의 tools/gen_title_images.background)을 다시 그리는 코드.

그대로 부르면(background()) 처음 배경과 픽셀까지 똑같다. 여기에 두 가지를 고를 수 있게 했다.
- celestial='sun': 달 대신 해, 낮이라 하늘의 별도 뺀다. 달·별을 그리던 난수는 그대로 소모해서
  나머지 그림(나무·구름·동굴)은 똑같이 나온다
- night=True: 밤하늘. 물체는 밤빛으로 어둡게 물들이되 달·동굴 속 빛은 밝게 남기고, 별을 더 띄운다

되찾은 색 그림체(gen_title_restore)가 낮(해)·밤(달) 배경을 만들 때 쓴다.
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, paper, bezier, ellipse_points, PLUM, PASTEL, PAPER  # noqa: E402

W, H = 1280, 720
GROUND = 585  # 땅 높이 (PIL y)
WHITE = (255, 255, 255)
SOFT_PLUM = (150, 128, 170)
MOON = (175, 120)  # 달·해 자리 (PIL 좌표)


def poly_mask(size, pts):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def lumpy(points, amp, rng, freq=0.08):
    """윤곽선을 울퉁불퉁한 바위처럼 만든다."""
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


def sparkle_stroke(sh, x, y, r, color, alpha=230, width=2.2):
    """네 갈래 반짝이."""
    sh.stroke([(x, y - r), (x + r * 0.15, y), (x, y + r)], width, color, alpha, amp=0.2)
    sh.stroke([(x - r, y), (x, y + r * 0.15), (x + r, y)], width, color, alpha, amp=0.2)


# ================================================================ 배경
DAY_SKY = [(0.0, (196, 182, 236)), (0.35, (226, 196, 236)), (0.62, (250, 208, 222)),
           (GROUND / H, (255, 228, 208)), (GROUND / H + 0.001, (220, 240, 222)), (1.0, (238, 244, 226))]
NIGHT_SKY = [(0.0, (30, 27, 70)), (0.35, (50, 41, 96)), (0.62, (80, 60, 116)),
             (GROUND / H, (104, 76, 122)), (GROUND / H + 0.001, (52, 70, 84)), (1.0, (62, 78, 88))]
NIGHT_TINT = np.array((0.44, 0.43, 0.66), np.float32)  # 밤에 물체에 곱하는 빛깔


def sky_gradient(night=False):
    """라벤더 → 분홍 → 복숭아빛 하늘, 땅은 민트빛 (밤이면 남보랏빛). 종이 결을 곱해 수채화 종이처럼."""
    stops = NIGHT_SKY if night else DAY_SKY
    ys = np.linspace(0, 1, H)
    col = np.zeros((H, 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    sky = np.repeat(col[:, None, :], W, axis=1)
    grain = np.asarray(paper(W, H, seed=3).convert('RGB'), np.float32) / np.array(PAPER, np.float32)
    return Image.fromarray(np.clip(sky * grain, 0, 255).astype(np.uint8)).convert('RGBA')


def cloud(sh, x, y, w, h, tint):
    """뭉게구름: 색 번짐 위에 흰 번짐, 윗부분만 펜 선."""
    sh.wash(x, y, w, h, tint, alpha=120, layers=4, blur=6, wobble=0.18)
    for i in range(4):
        cx = x - w * 0.6 + i * w * 0.4
        sh.wash(cx, y - h * 0.15, w * 0.38, h * 0.75, WHITE, alpha=150, layers=3, blur=5)
    for i in range(3):  # 위쪽 혹 세 개만 둥글게
        cx = x - w * 0.45 + i * w * 0.45
        ry = h * (0.75 if i == 1 else 0.55)
        sh.stroke(ellipse_points(cx, y - h * 0.05, w * 0.3, ry, 18, math.pi * 1.1, math.pi * 0.8), 2.6, SOFT_PLUM, 150,
                  amp=0.8)


def leafy_tree(sh, x, ground, height, crown, tint):
    top = ground - height
    cy = top + crown * 0.9
    # 수관 번짐 (벚꽃/민트/라벤더)
    sh.wash(x, cy, crown * 0.98, crown * 0.86, tint, alpha=200, layers=4, blur=4)
    sh.wash(x - crown * 0.3, cy - crown * 0.3, crown * 0.45, crown * 0.35, WHITE, alpha=110, layers=2, blur=5)
    # 줄기
    sh.wash(x, ground - height * 0.25, 14, height * 0.25, PASTEL['peach'], alpha=170, layers=2, blur=2)
    sh.stroke(bezier((x - 12, ground), (x - 8, ground - height * 0.3), (x - 10, cy + 20), (x - 6, cy + crown * 0.4)), 4)
    sh.stroke(bezier((x + 12, ground), (x + 9, ground - height * 0.3), (x + 11, cy + 20), (x + 7, cy + crown * 0.4)), 4)
    sh.stroke([(x - 14, ground), (x - 22, ground + 3)], 3)
    sh.stroke([(x + 14, ground), (x + 24, ground + 2)], 3)
    sh.stroke(bezier((x, cy + crown * 0.45), (x + 12, cy + 10), (x + 28, cy), (x + 40, cy - 12)), 3)
    sh.stroke(bezier((x - 2, cy + crown * 0.35), (x - 14, cy + 4), (x - 22, cy - 6), (x - 34, cy - 20)), 3)
    pts = []
    n = 90
    bumps = sh.rng.randint(7, 9)
    for i in range(n + 4):
        a = 2 * math.pi * i / n
        r = crown * (0.9 + 0.12 * abs(math.sin(a * bumps / 2)))
        pts.append((x + math.cos(a) * r, cy + math.sin(a) * r * 0.82))
    sh.stroke(pts, 4.2)
    # 꽃잎 점들
    for _ in range(10):
        a = sh.rng.uniform(0, 2 * math.pi)
        d = crown * sh.rng.uniform(0.15, 0.75)
        px, py = x + math.cos(a) * d, cy + math.sin(a) * d * 0.7
        sh.wash(px, py, 5, 4, WHITE, alpha=200, layers=1, blur=1)
    for _ in range(4):
        a = sh.rng.uniform(0, 2 * math.pi)
        d = crown * sh.rng.uniform(0.2, 0.6)
        px, py = x + math.cos(a) * d, cy + math.sin(a) * d * 0.7
        sh.stroke(ellipse_points(px, py, 9, 6, 10, sh.rng.uniform(0, 3), 2.4), 2.2, SOFT_PLUM, 200)


def pine_tree(sh, x, ground, height, width, tint):
    sh.stroke([(x - 6, ground), (x - 5, ground - height * 0.2)], 4)
    sh.stroke([(x + 6, ground), (x + 5, ground - height * 0.2)], 4)
    for t in range(3):
        base_y = ground - height * 0.18 - t * height * 0.24
        top_y = base_y - height * (0.36 - t * 0.04)
        hw = width * (1 - t * 0.26)
        tri = poly_mask((W, H), [(x - hw, base_y + 6), (x, top_y), (x + hw, base_y + 6)])
        fill = Sheet(W, H, seed=sh.rng.randint(0, 9999))
        fill.wash(x, (base_y + top_y) / 2 + 6, hw, (base_y - top_y) * 0.6, tint, alpha=210, layers=3, blur=4)
        fill.wash(x - hw * 0.3, (base_y + top_y) / 2, hw * 0.3, (base_y - top_y) * 0.3, WHITE, alpha=90, layers=2)
        sh.masked(fill, tri)
        sh.stroke([(x - hw, base_y), (x - hw * 0.45, (base_y + top_y) / 2 + 4), (x, top_y)], 4)
        sh.stroke([(x, top_y), (x + hw * 0.45, (base_y + top_y) / 2 + 3), (x + hw, base_y)], 4)
        sh.stroke(bezier((x - hw, base_y), (x - hw * 0.4, base_y + 9), (x + hw * 0.4, base_y + 9), (x + hw, base_y), 20),
                  3.4)


def flower(sh, x, y, tint):
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        sh.wash(x + math.cos(a) * 4.5, y + math.sin(a) * 4.5, 3.6, 3.6, tint, alpha=235, layers=1, blur=0.8)
    sh.wash(x, y, 2.2, 2.2, PASTEL['lemon'], alpha=255, layers=1, blur=0.5)


def grass_tuft(sh, x, y, size=1.0):
    for dx, lean in ((-6, -0.5), (0, 0.0), (6, 0.45)):
        hgt = sh.rng.uniform(12, 20) * size
        sh.stroke([(x + dx * size, y), (x + dx * size + lean * hgt * 0.8, y - hgt)], 2.6)


def rock(sh, x, y, rx, ry, tint):
    sh.wash(x, y - ry * 0.5, rx, ry * 0.75, tint, alpha=170, layers=2, blur=2)
    sh.stroke(ellipse_points(x, y - ry * 0.55, rx, ry, 30, math.pi * 0.98, math.pi * 1.04), 3.6)
    sh.stroke([(x - rx * 1.05, y), (x + rx * 1.05, y)], 3)


def _moon(sh, mx, my):
    """초승달과 달무리 (처음 배경 그대로)."""
    sh.wash(mx, my, 110, 100, PASTEL['lemon'], alpha=90, layers=3, blur=10)
    sh.wash(mx, my, 60, 56, (255, 246, 214), alpha=150, layers=3, blur=6)
    moon = poly_mask((W, H), ellipse_points(mx, my, 40, 40, 60))
    bite = poly_mask((W, H), ellipse_points(mx + 18, my - 12, 36, 36, 60))
    moon = ImageChops.subtract(moon, bite)
    mfill = Sheet(W, H, seed=14)
    mfill.wash(mx, my, 44, 44, (255, 244, 196), alpha=255, layers=2, blur=2)
    sh.masked(mfill, moon)
    sh.stroke(ellipse_points(mx, my, 40, 40, 40, math.pi * 0.05, math.pi * 1.55), 3.4)


def sun(seed=914):
    """귀여운 손그림 해: 노란 물감 원판 + 보랏빛 펜 테두리 + 길고 짧은 햇살, 둘레엔 따뜻한 빛 번짐."""
    mx, my = MOON
    sh = Sheet(W, H, seed=seed)
    sh.line = PLUM
    sh.wash(mx, my, 130, 120, PASTEL['lemon'], alpha=110, layers=3, blur=12)
    sh.wash(mx, my, 76, 72, (255, 236, 190), alpha=150, layers=3, blur=8)
    disk = poly_mask((W, H), ellipse_points(mx, my, 38, 38, 60))
    fill = Sheet(W, H, seed=seed + 1)
    fill.wash(mx, my, 44, 44, (255, 214, 120), alpha=255, layers=3, edge=1.2, blur=2)
    fill.wash(mx - 10, my - 10, 18, 14, (255, 246, 210), alpha=220, layers=2, blur=3)
    sh.masked(fill, disk)
    sh.ellipse(mx, my, 38, 38, 3.4, amp=0.8)
    for i in range(12):
        a = i * math.pi / 6 + 0.13
        r0, r1 = 50, (68 if i % 2 == 0 else 60)
        sh.stroke([(mx + math.cos(a) * r0, my + math.sin(a) * r0), (mx + math.cos(a) * r1, my + math.sin(a) * r1)],
                  3.2, amp=0.5)
    return sh


def night_stars(seed=915):
    """밤하늘에 더 띄우는 별 (달 둘레는 비운다)."""
    sh = Sheet(W, H, seed=seed)
    mx, my = MOON
    for _ in range(70):
        x, y = sh.rng.uniform(16, W - 16), sh.rng.uniform(14, 400)
        if math.hypot(x - mx, y - my) < 95:
            continue
        r = sh.rng.random()
        if r < 0.3:
            sh.wash(x, y, 6, 6, (255, 246, 214), alpha=70, layers=1, blur=3)
            sparkle_stroke(sh, x, y, sh.rng.uniform(5, 10), (255, 248, 226), 240, 2.0)
        else:
            sh.wash(x, y, 1.8, 1.8, (255, 250, 236), alpha=sh.rng.randint(160, 240), layers=1, blur=0.5)
    return sh


def night_keep(cx):
    """밤빛을 입히지 않을 곳: 달무리, 동굴 안쪽 빛, 그 빛이 비친 땅 (0~1)."""
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    mx, my = MOON
    d.ellipse((mx - 70, my - 70, mx + 70, my + 70), fill=255)
    d.ellipse((cx - 175, GROUND - 270, cx + 175, GROUND + 10), fill=235)
    d.ellipse((cx - 200, GROUND + 5, cx + 200, GROUND + 70), fill=120)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(28)), np.float32) / 255


def background(celestial='moon', night=False):
    """celestial: 'moon'(처음 그대로) / 'sun'. night: 밤하늘."""
    base = sky_gradient(night)
    sh = Sheet(W, H, seed=11)
    sh.line = PLUM

    # 초승달과 달무리 (해일 때는 같은 난수만 소모하고 버린다 → 나머지 그림이 똑같이 나온다)
    mx, my = MOON
    moon_sheet = sh
    if celestial != 'moon':
        moon_sheet = Sheet(W, H, seed=0)
        moon_sheet.rng, moon_sheet.np_rng, moon_sheet.line = sh.rng, sh.np_rng, PLUM
    _moon(moon_sheet, mx, my)
    if celestial == 'sun':
        sh.img.alpha_composite(sun().img)

    # 구름
    cloud(sh, 420, 150, 120, 36, PASTEL['pink'])
    cloud(sh, 1040, 110, 150, 42, PASTEL['sky'])
    cloud(sh, 700, 70, 80, 22, PASTEL['lavender'])
    cloud(sh, 90, 300, 80, 24, PASTEL['peach'])
    cloud(sh, 1220, 300, 90, 26, PASTEL['pink'])

    # 하늘의 별 (실행 중엔 따로 반짝이가 더해진다). 해가 뜬 낮엔 같은 난수만 소모하고 그리지 않는다
    star_sheet = moon_sheet if celestial == 'sun' else sh
    for _ in range(28):
        x, y = sh.rng.uniform(20, W - 20), sh.rng.uniform(20, 360)
        if math.hypot(x - mx, y - my) < 80:
            continue
        if sh.rng.random() < 0.45:
            sparkle_stroke(star_sheet, x, y, sh.rng.uniform(5, 9), WHITE, 230, 2.0)
        else:
            star_sheet.wash(x, y, 2.2, 2.2, WHITE, alpha=230, layers=1, blur=0.6)

    # 먼 언덕 (라벤더, 민트 두 겹)
    for k, (tint, base_y, alpha) in enumerate(((PASTEL['lavender'], 430, 150), (PASTEL['mint'], 480, 170))):
        hill = [(x, base_y - 40 * math.sin(x / (210 - k * 40) + 0.6 + k) - 16 * math.sin(x / 77 + k))
                for x in range(-20, W + 40, 20)]
        m = poly_mask((W, H), hill + [(W + 40, GROUND + 4), (-20, GROUND + 4)])
        f = Sheet(W, H, seed=15 + k)
        for x in range(0, W + 160, 160):
            f.wash(x, base_y + 50, 140, 90, tint, alpha=alpha, layers=2, blur=6)
        sh.masked(f, m)
        sh.stroke([p for p in hill if abs(p[0] - W / 2) > 300], 2.4, SOFT_PLUM, 170, amp=2)

    # 동굴: 분홍빛 바위 + 빛이 새어 나오는 안쪽
    cx = W / 2
    outer = bezier((cx - 300, GROUND), (cx - 330, GROUND - 250), (cx - 150, GROUND - 390), (cx + 20, GROUND - 375), 60)
    outer += bezier((cx + 20, GROUND - 375), (cx + 190, GROUND - 370), (cx + 330, GROUND - 260), (cx + 300, GROUND), 60)[1:]
    outer = lumpy(outer, 14, sh.rng, 0.11)
    arch = bezier((cx - 215, GROUND), (cx - 235, GROUND - 200), (cx - 120, GROUND - 290), (cx + 10, GROUND - 282), 60)
    arch += bezier((cx + 10, GROUND - 282), (cx + 130, GROUND - 278), (cx + 240, GROUND - 190), (cx + 212, GROUND), 60)[1:]
    arch = lumpy(arch, 7, sh.rng, 0.15)
    rock_fill = Sheet(W, H, seed=12)
    rock_fill.wash(cx - 160, GROUND - 200, 200, 220, PASTEL['pink'], alpha=190, layers=3, blur=6)
    rock_fill.wash(cx + 170, GROUND - 190, 200, 220, PASTEL['lavender'], alpha=190, layers=3, blur=6)
    rock_fill.wash(cx, GROUND - 330, 160, 60, PASTEL['peach'], alpha=170, layers=3, blur=6)
    rock_fill.wash(cx - 120, GROUND - 300, 70, 30, WHITE, alpha=120, layers=2, blur=5)
    sh.masked(rock_fill, poly_mask((W, H), outer))
    glow = Sheet(W, H, seed=13)
    glow.wash(cx, GROUND - 130, 240, 200, (120, 104, 178), alpha=230, layers=4, edge=0.6, blur=6)
    glow.wash(cx, GROUND - 120, 150, 130, PASTEL['sky'], alpha=200, layers=4, blur=8)
    glow.wash(cx, GROUND - 110, 90, 80, PASTEL['mint'], alpha=200, layers=3, blur=8)
    glow.wash(cx, GROUND - 105, 45, 40, (255, 252, 230), alpha=230, layers=3, blur=6)
    sh.masked(glow, poly_mask((W, H), arch))
    sh.stroke(outer, 4.4)
    sh.stroke(arch, 5)
    for (x0, y0, x1, y1) in ((cx - 270, GROUND - 160, cx - 238, GROUND - 120),
                             (cx - 200, GROUND - 330, cx - 160, GROUND - 300),
                             (cx + 60, GROUND - 350, cx + 95, GROUND - 318),
                             (cx + 255, GROUND - 210, cx + 280, GROUND - 160),
                             (cx + 150, GROUND - 330, cx + 175, GROUND - 300)):
        sh.stroke([(x0, y0), ((x0 + x1) / 2 + 6, (y0 + y1) / 2), (x1, y1)], 2.8, SOFT_PLUM, 220)
    for x, ln in ((cx - 90, 40), (cx - 40, 26), (cx + 30, 46), (cx + 95, 30)):
        top = GROUND - 280 + abs(x - cx) * 0.25
        sh.stroke([(x - 9, top), (x, top + ln), (x + 9, top)], 3, WHITE, 220)
    # 동굴 빛 주변 반짝이
    for _ in range(9):
        a = sh.rng.uniform(0, 2 * math.pi)
        d = sh.rng.uniform(60, 150)
        sparkle_stroke(sh, cx + math.cos(a) * d, GROUND - 110 + math.sin(a) * d * 0.6, sh.rng.uniform(4, 8), WHITE, 220)

    # 나무
    leafy_tree(sh, 120, GROUND + 8, 330, 95, PASTEL['pink'])
    pine_tree(sh, 290, GROUND + 4, 300, 75, PASTEL['mint'])
    leafy_tree(sh, 1170, GROUND + 6, 350, 100, PASTEL['lavender'])
    pine_tree(sh, 1010, GROUND + 4, 270, 68, PASTEL['sky'])
    pine_tree(sh, 30, GROUND + 6, 230, 55, PASTEL['lavender'])

    # 덤불
    for bx, by, r, tint in ((420, GROUND, 38, PASTEL['mint']), (865, GROUND, 44, PASTEL['pink']),
                            (205, GROUND, 30, PASTEL['sky']), (1090, GROUND, 32, PASTEL['mint'])):
        sh.wash(bx, by - r * 0.45, r * 0.95, r * 0.6, tint, alpha=220, layers=3, blur=3)
        sh.stroke(ellipse_points(bx, by - 2, r, r * 0.9, 40, math.pi * 1.02, math.pi * 0.96), 3.8)
        sh.stroke(ellipse_points(bx + r * 0.25, by - r * 0.55, r * 0.5, r * 0.4, 20, math.pi * 1.1, math.pi * 0.8), 2.8)

    # 땅
    ground_line = [(x, GROUND + 3 * math.sin(x / 41) + 2 * math.sin(x / 13)) for x in range(-10, W + 20, 16)]
    sh.wash(W / 2, GROUND + 70, W * 0.55, 60, PASTEL['mint'], alpha=110, layers=3, blur=8)
    sh.wash(W / 2, GROUND + 40, 220, 40, PASTEL['lemon'], alpha=110, layers=3, blur=8)  # 동굴 빛이 땅에 비침
    sh.stroke(ground_line, 4.2, amp=1.6)
    for x in range(30, W, 46):
        if abs(x - W / 2) < 240:
            continue
        sh.stroke([(x, GROUND + 26 + (x * 7) % 30), (x + 16, GROUND + 26 + (x * 7) % 30)], 2.2, SOFT_PLUM, 150)
    for x in (70, 180, 360, 470, 800, 930, 1120, 1240, 560, 720):
        grass_tuft(sh, x, GROUND + 2 + sh.rng.uniform(0, 6), sh.rng.uniform(0.8, 1.2))
    tints = list(PASTEL.values())
    for i in range(26):
        x = sh.rng.uniform(20, W - 20)
        if abs(x - W / 2) < 120:
            continue
        flower(sh, x, GROUND + sh.rng.uniform(14, 120), tints[i % len(tints)])
    rock(sh, 360, GROUND + 4, 26, 18, PASTEL['lavender'])
    rock(sh, 960, GROUND + 6, 34, 22, PASTEL['sky'])
    rock(sh, 800, GROUND + 62, 20, 12, PASTEL['peach'])

    layer = sh.result()
    if night:
        # 물체를 밤빛으로 (달무리·동굴 빛은 그대로 밝게)
        arr = np.asarray(layer, np.float32)
        keep = night_keep(cx)[..., None]
        arr[..., :3] *= NIGHT_TINT * (1 - keep) + keep
        layer = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    base.alpha_composite(layer)
    if night:
        base.alpha_composite(night_stars().result())
        glow = Sheet(W, H, seed=916)  # 달빛을 한 겹 더
        glow.wash(mx, my, 150, 140, (255, 240, 190), alpha=45, layers=2, blur=16)
        base.alpha_composite(glow.result())
    return base.convert('RGB')


