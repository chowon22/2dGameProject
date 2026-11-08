"""타이틀 화면 이미지를 PIL로 자동 생성한다 (PRD 9.2 #11: 에셋은 PIL로 자동 생성).

타이틀은 '되찾은 세상'을 미리 보여주는 화면이라 파스텔 수채화로 몽환적으로 물들인다.
(여정 중 흑백 세상과 같은 손그림 펜 선을 쓰되, 선 색만 보랏빛으로 부드럽게.)

실행:  python tools/gen_title_images.py
결과:  image/common/*.png, image/title/*.png, image/prepare/*.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from sketch import (Sheet, paper, font, bezier, ellipse_points,  # noqa: E402
                    INK, PLUM, PASTEL, PAPER, WATERCOLOR)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE = os.path.join(ROOT, 'image')
W, H = 1280, 720
GROUND = 585  # 땅 높이 (PIL y)
WHITE = (255, 255, 255)
SOFT_PLUM = (150, 128, 170)


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
def sky_gradient():
    """라벤더 → 분홍 → 복숭아빛 하늘, 땅은 민트빛. 종이 결을 곱해 수채화 종이처럼."""
    stops = [(0.0, (196, 182, 236)), (0.35, (226, 196, 236)), (0.62, (250, 208, 222)),
             (GROUND / H, (255, 228, 208)), (GROUND / H + 0.001, (220, 240, 222)), (1.0, (238, 244, 226))]
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


def background():
    base = sky_gradient()
    sh = Sheet(W, H, seed=11)
    sh.line = PLUM

    # 초승달과 달무리
    mx, my = 175, 120
    sh.wash(mx, my, 110, 100, PASTEL['lemon'], alpha=90, layers=3, blur=10)
    sh.wash(mx, my, 60, 56, (255, 246, 214), alpha=150, layers=3, blur=6)
    moon = poly_mask((W, H), ellipse_points(mx, my, 40, 40, 60))
    bite = poly_mask((W, H), ellipse_points(mx + 18, my - 12, 36, 36, 60))
    moon = ImageChops.subtract(moon, bite)
    mfill = Sheet(W, H, seed=14)
    mfill.wash(mx, my, 44, 44, (255, 244, 196), alpha=255, layers=2, blur=2)
    sh.masked(mfill, moon)
    sh.stroke(ellipse_points(mx, my, 40, 40, 40, math.pi * 0.05, math.pi * 1.55), 3.4)

    # 구름
    cloud(sh, 420, 150, 120, 36, PASTEL['pink'])
    cloud(sh, 1040, 110, 150, 42, PASTEL['sky'])
    cloud(sh, 700, 70, 80, 22, PASTEL['lavender'])
    cloud(sh, 90, 300, 80, 24, PASTEL['peach'])
    cloud(sh, 1220, 300, 90, 26, PASTEL['pink'])

    # 하늘의 별 (실행 중엔 따로 반짝이가 더해진다)
    for _ in range(28):
        x, y = sh.rng.uniform(20, W - 20), sh.rng.uniform(20, 360)
        if math.hypot(x - mx, y - my) < 80:
            continue
        if sh.rng.random() < 0.45:
            sparkle_stroke(sh, x, y, sh.rng.uniform(5, 9), WHITE, 230, 2.0)
        else:
            sh.wash(x, y, 2.2, 2.2, WHITE, alpha=230, layers=1, blur=0.6)

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

    base.alpha_composite(sh.result())
    return base.convert('RGB')


# ================================================================ 로고
def logo():
    """'What are you do' 는 보랏빛 펜 글씨, 'Ink' 는 수채화로 물든 글씨."""
    lw, lh = 1100, 300
    sh = Sheet(lw, lh, seed=21)
    small = font('Inkfree.ttf', 86)
    big = font('segoeprb.ttf', 150)
    line = 'What are you do'
    w_small = small.getlength(line)
    w_big = big.getlength('Ink')
    x0 = (lw - (w_small + 30 + w_big)) / 2
    base_y = 210
    xi = x0 + w_small + 30

    # 글씨 뒤 흰 테두리 (파스텔 배경 위에서도 또렷하게)
    for text, fnt, x in ((line, small, x0), ('Ink', big, xi)):
        m = sh.text_mask(text, fnt, x, base_y, anchor='ls').filter(ImageFilter.MaxFilter(13))
        halo = Image.new('RGBA', sh.img.size, WHITE + (0,))
        halo.putalpha(m.filter(ImageFilter.GaussianBlur(3)))
        sh.img.alpha_composite(halo)

    sh.ink_text(line, small, x0 + 3, base_y + 3, PASTEL['lavender'], 255, anchor='ls')
    sh.ink_text(line, small, x0, base_y, PLUM, 255, anchor='ls')

    fill = Sheet(lw, lh, seed=22)
    keys = ('pink', 'lemon', 'mint', 'sky', 'lavender')
    vivid = {'pink': (240, 128, 166), 'lemon': (246, 200, 92), 'mint': (104, 200, 160),
             'sky': (104, 164, 232), 'lavender': (160, 128, 224)}
    for i, key in enumerate(keys):
        fill.wash(xi + w_big * (0.08 + 0.21 * i), base_y - 62, w_big * 0.17, 95, vivid[key], alpha=255,
                  layers=4, edge=0.8, blur=6)
    for _ in range(8):
        fill.wash(xi + fill.rng.uniform(0, w_big), base_y - fill.rng.uniform(20, 120), 14, 12, WHITE, alpha=110,
                  layers=2)
    sh.masked(fill, sh.text_mask('Ink', big, xi, base_y, anchor='ls').resize((lw, lh), Image.BILINEAR))
    m2 = sh.text_mask('Ink', big, xi, base_y, anchor='ls')
    outline = ImageChops.subtract(m2.filter(ImageFilter.MaxFilter(9)), m2)
    layer = Image.new('RGBA', sh.img.size, PLUM + (0,))
    layer.putalpha(outline)
    sh.img.alpha_composite(layer)

    sh.splatter(xi + w_big + 18, base_y - 120, 34, vivid['sky'], count=6, size=(2, 6))
    sh.splatter(xi - 8, base_y - 140, 22, vivid['pink'], count=4, size=(2, 5))
    sh.splatter(xi + w_big * 0.5, base_y + 22, 40, vivid['mint'], count=5, size=(1.5, 4))
    for (sx, sy, r) in ((xi + w_big + 40, base_y - 160, 12), (x0 - 20, base_y - 90, 9), (xi - 40, base_y - 170, 7)):
        sparkle_stroke(sh, sx, sy, r, (255, 236, 150), 255, 3)
    under = bezier((x0 + 10, base_y + 30), (x0 + 300, base_y + 22), (xi - 60, base_y + 42), (xi - 10, base_y + 28))
    sh.stroke(under, 4.5, PLUM)
    return sh.result(crop=True, margin=10)


def soft_glow(w, h, color, seed, alpha=170):
    """로고·잉크통 뒤에서 숨 쉬듯 깜빡이는 빛."""
    sh = Sheet(w, h, seed=seed)
    sh.wash(w / 2, h / 2, w * 0.4, h * 0.38, color, alpha=alpha, layers=4, edge=0.2, blur=14)
    sh.wash(w / 2, h / 2, w * 0.25, h * 0.22, WHITE, alpha=120, layers=3, edge=0.1, blur=12)
    return sh.result()


def subtitle():
    sw, sh_h = 760, 70
    sh = Sheet(sw, sh_h, seed=31)
    f = font('malgun.ttf', 26)
    m = sh.text_mask('그린 그림으로 싸우고, 빼앗긴 색을 되찾는다', f, sw / 2, sh_h / 2, anchor='mm')
    halo = Image.new('RGBA', sh.img.size, WHITE + (0,))
    halo.putalpha(m.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(4)))
    sh.img.alpha_composite(halo)
    sh.ink_text('그린 그림으로 싸우고, 빼앗긴 색을 되찾는다', f, sw / 2, sh_h / 2, PLUM, 255, anchor='mm')
    return sh.result(crop=True, margin=8)


# ================================================================ 컬러 잉크통 (모래시계)
def ink_bottle():
    """모래시계 모양 컬러 잉크통. 위 칸엔 세상의 색, 아래 칸엔 모인 색이 쌓인다."""
    bw, bh = 220, 320
    cx = bw / 2
    sh = Sheet(bw, bh, seed=41)
    sh.line = PLUM
    top, bottom = 46, 274
    neck = (top + bottom) / 2
    left = bezier((cx - 78, top), (cx - 86, top + 80), (cx - 14, neck - 30), (cx - 9, neck), 40) + \
        bezier((cx - 9, neck), (cx - 14, neck + 30), (cx - 86, bottom - 80), (cx - 78, bottom), 40)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask((bw, bh), left + right[::-1])

    color = Sheet(bw, bh, seed=42)
    color.wash(cx, neck, 80, 130, (236, 240, 255), alpha=150, layers=2)  # 유리 빛
    color.wash(cx - 30, top + 62, 46, 40, WATERCOLOR['red'], alpha=230, layers=4, blur=4)
    color.wash(cx + 32, top + 58, 44, 42, WATERCOLOR['blue'], alpha=230, layers=4, blur=4)
    color.wash(cx, top + 92, 40, 30, WATERCOLOR['green'], alpha=230, layers=4, blur=4)
    color.wash(cx, top + 30, 60, 22, WHITE, alpha=130, layers=2, blur=4)
    color.stroke([(cx, neck - 20), (cx + 1, neck + 4), (cx, bottom - 30)], 3, (180, 120, 200), 230, amp=0.5)
    color.wash(cx - 22, bottom - 16, 34, 16, WATERCOLOR['red'], alpha=220, layers=3)
    color.wash(cx + 20, bottom - 14, 32, 15, WATERCOLOR['blue'], alpha=220, layers=3)
    color.wash(cx, bottom - 24, 22, 12, WATERCOLOR['green'], alpha=220, layers=3)
    sh.masked(color, inner)

    sh.stroke(left, 4.4)
    sh.stroke(right, 4.4)
    sh.stroke(bezier((cx - 58, top + 22), (cx - 66, top + 60), (cx - 40, top + 92), (cx - 26, top + 104), 20),
              4, WHITE, 240, amp=0.6)
    sh.stroke(bezier((cx - 58, bottom - 30), (cx - 64, bottom - 50), (cx - 52, bottom - 70), (cx - 44, bottom - 80), 14),
              3, WHITE, 220, amp=0.6)
    # 뚜껑·받침 (파스텔 나무색)
    for y, d in ((top, -1), (bottom, 1)):
        y0, y1 = (y - 26, y + 2) if d < 0 else (y - 2, y + 26)
        sh.wash(cx, (y0 + y1) / 2, 94, 13, PASTEL['peach'], alpha=240, layers=2, blur=2)
        sh.wash(cx - 40, (y0 + y1) / 2 - 3, 40, 5, WHITE, alpha=120, layers=1, blur=2)
        sh.stroke([(cx - 96, y0), (cx + 96, y0 + 1), (cx + 98, y1), (cx - 95, y1 - 1), (cx - 96, y0 - 2)], 4.2)
        for k in range(5):
            xx = cx - 70 + k * 35
            sh.stroke([(xx, y0 + 7), (xx + 10, y1 - 7)], 1.8, SOFT_PLUM, 160)
    for x in (cx - 88, cx + 88):
        sh.stroke([(x, top + 2), (x + 1, bottom - 2)], 4)
    return sh.result(crop=True, margin=4)


def bottle_shadow():
    sh = Sheet(240, 50, seed=45)
    sh.wash(120, 25, 100, 14, (130, 110, 170), alpha=120, layers=3, edge=0.4, blur=5)
    return sh.result()


# ================================================================ 버튼
def button(label, fill_color, seed, hover):
    """종이 쪽지 모양 버튼. hover 상태면 색이 더 진하게 번지고 반짝인다."""
    bw, bh = 300, 96
    sh = Sheet(bw, bh, seed=seed)
    sh.line = PLUM
    x0, y0, x1, y1 = 18, 16, bw - 18, bh - 16
    r = 14
    box = bezier((x0 + r, y0), (x0 + 80, y0 - 3), (x1 - 80, y0 + 3), (x1 - r, y0), 30) + \
        bezier((x1 - r, y0), (x1 + 2, y0), (x1 + 2, y0 + 2), (x1, y0 + r), 6)[1:] + \
        [(x1 + 1, (y0 + y1) / 2), (x1, y1 - r)] + \
        bezier((x1, y1 - r), (x1, y1 + 1), (x1 - 2, y1 + 1), (x1 - r, y1), 6)[1:] + \
        bezier((x1 - r, y1), (x1 - 80, y1 + 3), (x0 + 80, y1 - 2), (x0 + r, y1), 30)[1:] + \
        bezier((x0 + r, y1), (x0 - 1, y1), (x0 - 1, y1 - 2), (x0, y1 - r), 6)[1:] + \
        [(x0 - 1, (y0 + y1) / 2), (x0, y0 + r)] + \
        bezier((x0, y0 + r), (x0, y0 - 1), (x0 + 2, y0 - 1), (x0 + r + 10, y0 - 1), 6)[1:]
    fill = Sheet(bw, bh, seed=seed + 1)
    rx, ry = (x1 - x0) / 2 + 10, (y1 - y0) / 2 + 10
    fill.wash(bw / 2, bh / 2, rx, ry, (255, 252, 248), alpha=255, layers=2, blur=4, wobble=0.04)
    fill.wash(bw / 2, bh / 2, rx, ry, fill_color, alpha=255 if hover else 150, layers=4, blur=4, wobble=0.05)
    fill.wash(bw / 2 - 70, bh / 2 - 8, 60, 14, WHITE, alpha=130, layers=2)
    sh.masked(fill, poly_mask((bw, bh), box))
    sh.stroke(box, 4.2)
    sh.stroke([(x0 + 24, y1 + 5), (x1 - 6, y1 + 4)], 2.2, SOFT_PLUM, 150)
    if hover:
        sparkle_stroke(sh, x1 - 4, y0 + 2, 9, (255, 236, 150), 255, 2.6)
        sparkle_stroke(sh, x0 + 6, y1 - 4, 6, WHITE, 255, 2.2)
    f = font('malgunbd.ttf', 32)
    sh.ink_text(label, f, bw / 2 + 2, bh / 2 + 2, WHITE, 200, anchor='mm')
    sh.ink_text(label, f, bw / 2, bh / 2, PLUM, 255, anchor='mm')
    return sh.result()


# ================================================================ 효과용 작은 이미지
def ink_drop(color, seed):
    """클릭하면 튀는 잉크 얼룩."""
    s = 128
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 30, 26, color, alpha=240, layers=4, edge=1.6, blur=1.4, wobble=0.22)
    sh.wash(s / 2 - 8, s / 2 - 8, 10, 8, WHITE, alpha=110, layers=2, blur=1.5)
    sh.splatter(s / 2, s / 2, 46, color, count=9, size=(2, 5.5), alpha=240)
    return sh.result()


def brush_dot(color, seed):
    s = 32
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 9, 9, color, alpha=255, layers=3, edge=0.3, blur=1.5, wobble=0.1)
    sh.wash(s / 2 - 2, s / 2 - 2, 3, 3, WHITE, alpha=160, layers=1, blur=1)
    return sh.result()


def bubble(color, seed):
    """떠다니는 비눗방울: 연한 색 번짐 + 가는 테두리 + 하이라이트."""
    s = 64
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 24, 24, color, alpha=110, layers=2, edge=2.2, blur=2, wobble=0.03)
    sh.ellipse(s / 2, s / 2, 24, 24, 1.8, WHITE, 230, amp=0.3)
    sh.stroke(ellipse_points(s / 2, s / 2, 16, 16, 12, math.pi * 1.1, math.pi * 0.35), 3, WHITE, 240, amp=0.2)
    return sh.result()


def sparkle():
    s = 48
    sh = Sheet(s, s, seed=55)
    sh.wash(s / 2, s / 2, 10, 10, (255, 244, 200), alpha=200, layers=2, edge=0.1, blur=4)
    sparkle_stroke(sh, s / 2, s / 2, 18, WHITE, 255, 3)
    sparkle_stroke(sh, s / 2, s / 2, 10, (255, 236, 150), 255, 2)
    return sh.result()


def cursor_pen():
    """깃펜 모양 커서. 펜촉 끝이 이미지 왼쪽 아래 (6, 58)."""
    s = 64
    sh = Sheet(s, s, seed=61)
    sh.line = PLUM
    tip = (6, 58)
    feather = bezier((18, 46), (22, 20), (40, 6), (60, 3), 20) + bezier((60, 3), (56, 24), (40, 42), (20, 48), 20)[1:]
    fill = Sheet(s, s, seed=62)
    fill.wash(38, 26, 22, 22, WHITE, alpha=255, layers=2, blur=1)
    fill.wash(46, 16, 14, 12, PASTEL['pink'], alpha=220, layers=2, blur=1)
    fill.wash(30, 36, 10, 8, PASTEL['sky'], alpha=200, layers=2, blur=1)
    sh.masked(fill, poly_mask((s, s), feather))
    sh.stroke(feather, 2.6, amp=0.4, taper=False)
    sh.stroke(bezier((20, 46), (30, 34), (44, 18), (58, 5), 16), 1.8, amp=0.3)
    sh.stroke([(20, 46), tip], 4.2, amp=0.2)
    sh.wash(tip[0] + 2, tip[1] - 2, 3, 3, PLUM, alpha=255, layers=1, blur=0.5)
    return sh.result()


def prepare_wip():
    sw, sh_h = 900, 160
    sh = Sheet(sw, sh_h, seed=71)
    sh.ink_text('준비 화면', font('malgunbd.ttf', 54), sw / 2, 52, INK, 255, anchor='mm')
    sh.ink_text('틀을 고르고 유닛을 그리는 곳 — 다음 단계에서 만들어요', font('malgun.ttf', 26), sw / 2, 112,
                (80, 76, 82), 255, anchor='mm')
    sh.ink_text('ESC : 타이틀로', font('malgun.ttf', 22), sw / 2, 146, (120, 118, 124), 255, anchor='mm')
    return sh.result()


def main():
    save(paper(W, H, seed=5).convert('RGB'), 'common', 'paper.png')
    save(background(), 'title', 'background.png')
    save(logo(), 'title', 'logo.png')
    save(soft_glow(1000, 340, PASTEL['pink'], 23), 'title', 'logo_glow.png')
    save(subtitle(), 'title', 'subtitle.png')
    save(ink_bottle(), 'title', 'ink_bottle.png')
    save(soft_glow(340, 400, PASTEL['lemon'], 43, alpha=200), 'title', 'bottle_glow.png')
    save(bottle_shadow(), 'title', 'bottle_shadow.png')
    save(button('시작하기', PASTEL['pink'], 81, False), 'title', 'button_start.png')
    save(button('시작하기', PASTEL['pink'], 81, True), 'title', 'button_start_hover.png')
    save(button('끝내기', PASTEL['sky'], 82, False), 'title', 'button_quit.png')
    save(button('끝내기', PASTEL['sky'], 82, True), 'title', 'button_quit_hover.png')
    for i, (name, c) in enumerate(PASTEL.items()):
        vivid = tuple(max(0, int(v * 0.92)) for v in c)
        save(ink_drop(vivid, 90 + i), 'common', f'ink_drop_{name}.png')
        save(brush_dot(c, 110 + i), 'common', f'brush_dot_{name}.png')
        save(bubble(c, 130 + i), 'title', f'bubble_{name}.png')
    save(sparkle(), 'title', 'sparkle.png')
    save(cursor_pen(), 'common', 'cursor_pen.png')
    save(prepare_wip(), 'prepare', 'wip_text.png')


if __name__ == '__main__':
    main()
