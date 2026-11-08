"""타이틀·설정 화면 '잉크(수묵)' 버전 이미지 생성.

잉크가 주제인 게임이라, 수묵화에 물감 잉크를 떨어뜨린 듯한 몽환적인 장면으로 그린다.
- 한지 위 먹의 농담으로 겹겹이 그린 산, 그 사이 안개, 아래는 산이 비치는 잔잔한 물
- 가운데 잉크통 뒤에서 빨·초·파 잉크가 물속에 퍼지듯 연기처럼 피어오른다
- 붉은 먹의 해, 붓으로 그린 새, 먹 튐
- 붓글씨 로고 + 붉은 낙관, 먹 붓질 버튼, 족자 설정 창

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
from gen_title_images import (W, H, LIGHT, WHITE, ELEMENT, ROOT, PANEL_W, PANEL_H, SETTING_ROWS,  # noqa: E402
                              save, poly_mask, densify, lighter, darker, lumpy)
from gen_title_doodle import empty  # noqa: E402

TITLE, SETTINGS = 'title_ink', 'settings_ink'
BRUSH_FONT = os.path.join(ROOT, 'fonts', 'NanumBrushScript-Regular.ttf')  # 나눔손글씨 붓 (OFL)
SUMI = (22, 22, 28)            # 먹
HANJI = (244, 238, 224)        # 한지
VERMILION = (206, 70, 58)      # 붉은 먹(낙관·해)
HORIZON = 560                  # 물가 (PIL y)
INK_COLORS = {'red': (226, 74, 70), 'green': (60, 170, 110), 'blue': (60, 120, 220)}


def brush(size):
    return ImageFont.truetype(BRUSH_FONT, size)


# ================================================================ 먹 도구
def hanji(w, h, seed=0):
    """한지: 따뜻한 미색 + 섬유 결(가늘고 긴 얼룩) + 잔 알갱이."""
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(HANJI, np.float32)
    fine = rng.normal(0, 3.0, (h, w)).astype(np.float32)
    fib = Image.new('L', (w, h), 128)
    d = ImageDraw.Draw(fib)
    r = random.Random(seed)
    for _ in range(int(w * h / 900)):
        x, y = r.uniform(0, w), r.uniform(0, h)
        a = r.uniform(0, math.pi)
        ln = r.uniform(6, 26)
        d.line([(x, y), (x + math.cos(a) * ln, y + math.sin(a) * ln)], fill=r.choice((110, 146)), width=1)
    fib = (np.asarray(fib.filter(ImageFilter.GaussianBlur(0.6)), np.float32) - 128) / 6
    low = rng.normal(0, 1, (h // 50 + 2, w // 50 + 2)).astype(np.float32)
    low = np.asarray(Image.fromarray(np.clip(low * 30 + 128, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                     np.float32)
    low = (low - 128) / 30 * 4
    arr = base + (fine + fib + low)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')


def wash_layer(size, mask, color, strength, fade=None, edge=0.5, seed=0, ss=1):
    """먹 번짐 한 겹 (RGBA). mask 안을 칠하되,
    - 가장자리는 번진 듯 흐리고(블러 + 잡음 문턱) 경계선이 살짝 진하다(물 마른 자국)
    - fade 가 있으면 능선(위쪽)에서 아래로 갈수록 옅어진다 (수묵 산의 농담)"""
    w, h = size
    rng = np.random.default_rng(seed)
    m = np.asarray(mask.filter(ImageFilter.GaussianBlur(4 * ss)), np.float32) / 255
    noise = np.asarray(Image.fromarray((rng.random((h // 6 + 1, w // 6 + 1)) * 255).astype(np.uint8))
                       .resize((w, h), Image.BICUBIC), np.float32) / 255
    m = np.clip((m - 0.25 * noise) / 0.75, 0, 1)
    a = m.copy()
    if fade:
        top = np.argmax(np.asarray(mask) > 128, axis=0).astype(np.float32)
        has = (np.asarray(mask) > 128).any(axis=0)
        top[~has] = h
        ys = np.arange(h, dtype=np.float32)[:, None]
        a *= np.exp(-np.clip(ys - top[None, :], 0, None) / fade)
    soft = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3 * ss)),
                      np.float32) / 255
    a = a * (1 - edge * 0.3) + np.clip(m - soft, 0, 1) * edge * 2.2
    grain = 0.85 + 0.15 * rng.random((h, w), dtype=np.float32)
    a = np.clip(a * grain * strength, 0, 1)
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = color
    out[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def ink_wash(sh, pts, color, strength, fade=None, edge=0.5):
    m = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(m).polygon([(x * sh.ss, y * sh.ss) for x, y in pts], fill=255)
    sh.img.alpha_composite(wash_layer(sh.img.size, m, color, strength, fade and fade * sh.ss, edge,
                                      sh.rng.randint(0, 9999), sh.ss))


def mist(sh, y, height, alpha=200):
    """산 사이 안개: 한지색으로 길게 덮는다."""
    sh.wash(W / 2, y, W * 0.7, height, HANJI, alpha=alpha, layers=3, edge=0.0, blur=16, wobble=0.2)


def brush_stroke(sh, pts, width, color, alpha=255, dry=0.5):
    """붓 한 획: 처음 눌렀다 끝으로 갈수록 가늘어지고, 끝은 마른 붓처럼 갈라진다."""
    s = sh.ss
    lay = Sheet(sh.w, sh.h, seed=sh.rng.randint(0, 99999), ss=s)
    pts = densify(pts, 1.5)
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / max(1, n - 1)
        r = width / 2 * (min(1.0, t * 6 + 0.55) * (1 - t ** 2.2 * 0.85))
        lay.draw.ellipse(((x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s), fill=tuple(color) + (alpha,))
    if dry > 0:  # 마른 붓 결: 획 방향을 따라 가는 틈
        a = np.asarray(lay.img.split()[3], np.float32)
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        h_, w_ = a.shape
        yy, xx = np.mgrid[0:h_, 0:w_].astype(np.float32)
        across = (-math.sin(ang) * xx + math.cos(ang) * yy) / s
        along = (math.cos(ang) * xx + math.sin(ang) * yy) / s
        streak = np.sin(across * 1.7 + np.sin(across * 0.37) * 3) * 0.5 + 0.5
        start = math.cos(ang) * x0 + math.sin(ang) * y0
        length = math.hypot(x1 - x0, y1 - y0) or 1
        tail = np.clip(((along - start) / length - 0.45) / 0.55, 0, 1)
        a *= 1 - dry * tail * (streak > 0.55)
        lay.img.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    sh.img.alpha_composite(lay.img)


def _flow(x, y, seed):
    """부드러운 흐름장 각도 (사인 겹침으로 만든 가짜 노이즈)."""
    return (math.sin(x * 0.011 + seed) * 1.3 + math.sin(y * 0.017 - seed * 0.7) * 1.1 +
            math.sin((x + y) * 0.007 + seed * 1.9) * 0.9)


def ink_plume(sh, x0, y0, color, length, spread, seed, particles=160):
    """물속에 퍼지는 잉크 연기: 입자 수백 개가 흐름장을 따라 오르며 가는 실 자국을 남긴다."""
    r = random.Random(seed)
    lay = Sheet(sh.w, sh.h, seed=seed, ss=sh.ss)
    for _ in range(particles):
        x, y = x0 + r.gauss(0, 10), y0 + r.gauss(0, 6)
        vx, vy = r.uniform(-1.2, 1.2), -r.uniform(1.4, 2.6)
        off = r.uniform(-140, 140)  # 가닥마다 조금씩 다른 흐름을 타서 흩어진다
        pts = [(x, y)]
        steps = int(length / 2.2 * r.uniform(0.6, 1.1))
        for k in range(steps):
            a = _flow(x + off, y - off * 0.5, seed)
            t = k / steps
            vx = vx * 0.92 + math.cos(a) * spread * (0.2 + t)
            vy = vy * 0.92 + (math.sin(a) * 0.35 * spread - 0.24)
            x += vx
            y += vy
            pts.append((x, y))
        if len(pts) > 3:
            lay.stroke(pts, r.uniform(0.8, 2.2), color, r.randint(18, 46), amp=0.3)
    lay.img = lay.img.filter(ImageFilter.GaussianBlur(1.2 * sh.ss))
    sh.img.alpha_composite(lay.img)
    sh.wash(x0, y0 - 6, 26, 18, color, alpha=110, layers=2, edge=0.3, blur=6)


def splatter(sh, x, y, spread, color, count=10):
    for _ in range(count):
        a = sh.rng.uniform(0, 2 * math.pi)
        d = spread * sh.rng.uniform(0.2, 1.2)
        r = sh.rng.uniform(1, 4.5)
        sh.wash(x + math.cos(a) * d, y + math.sin(a) * d, r, r, color, alpha=230, layers=1, edge=0.6, blur=0.5)


def ridge(x0, x1, base, peaks, rng, step=10):
    """수묵 산 능선: (중심x, 높이, 폭) 봉우리들을 겹친 윤곽."""
    pts = []
    for x in range(int(x0), int(x1) + 1, step):
        y = base
        for px, hgt, wd in peaks:
            y = min(y, base - hgt * math.exp(-((x - px) / wd) ** 2 * 2.2) ** 0.8)
        pts.append((x, y + rng.uniform(-2, 2)))
    return pts + [(x1, H + 10), (x0, H + 10)]


def pine(sh, x, y, size, color):
    """붓으로 그린 소나무: 굽은 줄기 한 획 + 가지 끝마다 뭉게진 먹 잎."""
    trunk = [(x, y), (x + size * 0.18, y - size * 0.35), (x - size * 0.08, y - size * 0.7), (x + size * 0.1, y - size)]
    brush_stroke(sh, trunk, size * 0.11, color, 245, dry=0.35)
    clumps = [(x + size * 0.1, y - size, 0.42), (x - size * 0.35, y - size * 0.72, 0.32),
              (x + size * 0.42, y - size * 0.58, 0.3), (x - size * 0.2, y - size * 0.4, 0.24)]
    for cx_, cy_, k in clumps:
        if abs(cx_ - x) > size * 0.15:
            brush_stroke(sh, [(x + (cx_ - x) * 0.1, cy_ + 6), (cx_, cy_ + 2)], size * 0.05, color, 230, dry=0.2)
        for _ in range(6):
            ox, oy = sh.rng.uniform(-1, 1) * size * k, sh.rng.uniform(-0.35, 0.25) * size * k
            sh.wash(cx_ + ox, cy_ + oy, size * k * 0.42, size * k * 0.22, color, alpha=170, layers=1, edge=1.4,
                    blur=1.2, wobble=0.35)


# ================================================================ 배경
def background():
    base = hanji(W, H, seed=31)
    sh = Sheet(W, H, seed=32)
    rng = sh.rng

    # 하늘: 아주 옅은 먹 (색은 나중에 '물들이기' 층이 입힌다)
    sh.wash(W / 2, 40, W * 0.7, 140, (180, 182, 190), alpha=60, layers=3, edge=0.1, blur=30)

    # 붉은 먹의 해
    sx, sy = 1040, 150
    sh.wash(sx, sy, 58, 58, VERMILION, alpha=200, layers=3, edge=1.2, blur=3, wobble=0.04)
    sh.wash(sx, sy, 120, 120, (240, 170, 150), alpha=40, layers=2, edge=0.0, blur=20)

    # 먼 산 (옅은 먹, 능선에서 아래로 옅어짐)
    far = ridge(-20, W + 20, 470, [(120, 210, 90), (300, 150, 110), (980, 240, 100), (1160, 190, 90),
                                     (760, 120, 120)], rng)
    ink_wash(sh, far, (120, 124, 140), 0.45, fade=90, edge=0.5)
    mist(sh, 450, 50, 210)
    # 가운데 산
    mid = ridge(-20, W + 20, 540, [(60, 300, 80), (230, 200, 90), (420, 110, 80), (880, 130, 90), (1090, 280, 90),
                                     (1250, 220, 70)], rng)
    ink_wash(sh, mid, (70, 72, 86), 0.65, fade=110, edge=0.7)
    mist(sh, 520, 40, 200)

    # 잉크 연기: 잉크통 뒤에서 빨·초·파가 피어오른다
    lx, ly = LIGHT
    for k, (key, dx, ln, spread) in enumerate((('red', -40, 360, 0.55), ('green', 0, 420, 0.5),
                                                ('blue', 40, 360, 0.6))):
        ink_plume(sh, lx + dx, ly + 30, INK_COLORS[key], ln, spread, 900 + k * 7)
    # 잉크통 둘레 흰 빛
    sh.wash(lx, ly, 150, 140, (255, 252, 244), alpha=170, layers=3, edge=0.0, blur=26)

    # 가까운 절벽 (짙은 먹) + 소나무
    left = [(-20, H + 10), (-20, 300), (40, 280), (110, 330), (150, 420), (210, 470), (240, 560), (300, 600),
            (330, H + 10)]
    right = [(W + 20, H + 10), (W + 20, 330), (1230, 310), (1170, 360), (1130, 450), (1080, 500), (1050, 560),
             (1000, 600), (980, H + 10)]
    for shape in (left, right):
        ink_wash(sh, lumpy(densify(shape, 10), 6, rng, 0.2), SUMI, 0.9, fade=200, edge=1.0)
    for x, y, s_ in ((60, 300, 120), (120, 344, 80), (1220, 330, 130), (1150, 376, 86)):
        pine(sh, x, y, s_, SUMI)
    # 붓 획 바위 결
    for pts in (((150, 430), (190, 470), (205, 520)), ((1120, 460), (1090, 500), (1080, 540))):
        brush_stroke(sh, list(pts), 8, (40, 40, 48), 200, dry=0.7)

    # 새 (붓)
    for x, y, s_ in ((420, 120, 12), (450, 100, 9), (480, 128, 10), (860, 80, 8)):
        brush_stroke(sh, [(x - s_, y - s_ * 0.3), (x - s_ * 0.3, y), (x, y + s_ * 0.2)], 3.2, SUMI, 240, dry=0)
        brush_stroke(sh, [(x, y + s_ * 0.2), (x + s_ * 0.3, y), (x + s_, y - s_ * 0.4)], 3.2, SUMI, 240, dry=0)


    # ---- 물: 위쪽 장면을 뒤집어 흐리게 비추고, 가로 물결을 붓으로
    scene = base.copy()
    scene.alpha_composite(sh.result())
    top = scene.crop((0, HORIZON - 260, W, HORIZON))
    refl = top.transpose(Image.FLIP_TOP_BOTTOM).resize((W, H - HORIZON), Image.BICUBIC)
    arr = np.asarray(refl, np.float32)
    rows = arr.shape[0]
    for y in range(rows):  # 물결에 따라 줄마다 살짝 밀기
        arr[y] = np.roll(arr[y], int(4 * math.sin(y * 0.45)), axis=0)
    paper_ = np.asarray(hanji(W, rows, seed=33).convert('RGBA'), np.float32)
    k = (np.linspace(0.55, 0.85, rows)[:, None, None])
    arr = arr * (1 - k) + paper_ * k
    arr[..., :3] = arr[..., :3] * np.array([0.96, 0.98, 1.02])
    water = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    scene.alpha_composite(water, (0, HORIZON))
    ws = Sheet(W, H, seed=34)
    ws.stroke([(-10, HORIZON), (W + 10, HORIZON + 2)], 2.4, (90, 92, 106), 150, amp=1.0)
    for i in range(14):
        y = HORIZON + 14 + i * 11 + ws.rng.uniform(-3, 3)
        x = ws.rng.uniform(80, W - 380)
        brush_stroke(ws, [(x, y), (x + ws.rng.uniform(120, 320), y + ws.rng.uniform(-2, 2))], ws.rng.uniform(2, 4),
                     (110, 112, 128), 120, dry=0.7)
    scene.alpha_composite(ws.result())
    return scene.convert('RGB')


# ================================================================ 물들이기
DYE_FRAMES = 12
DYE_SIZE = (640, 360)  # 색 층은 부드러워서 절반 크기로 만들어 두 배로 늘려 그린다


def dye_frames():
    """잉크통에서부터 색이 물감처럼 번져 나가는 단계별 색 층 (투명 RGBA, 점점 넓어진다).
    번지는 가장자리는 물감이 마르며 남는 진한 테두리처럼 살짝 진하다."""
    w, h = DYE_SIZE
    sx, sy = w / W, h / H
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # 지역별 물감 색 (하늘 위쪽 하늘색 → 분홍 노을 → 산 라벤더·청록 → 물빛)
    ys = yy / h
    stops = [(0.0, (130, 176, 236)), (0.28, (236, 160, 196)), (0.5, (190, 160, 226)), (0.72, (96, 180, 160)),
             (0.78, (110, 170, 230)), (1.0, (90, 150, 220))]
    col = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        col[..., c] = np.interp(ys, [a for a, _ in stops], [b[c] for _, b in stops])
    for (bx, by, br, bc) in ((LIGHT[0], LIGHT[1], 170, (250, 210, 120)), (1040, 150, 150, (246, 150, 120)),
                             (80, 380, 200, (70, 150, 110)), (1220, 400, 200, (70, 150, 110))):
        d = np.hypot(xx - bx * sx, yy - by * sy) / (br * sx)
        k = np.exp(-d ** 2)[..., None]
        col = col * (1 - k) + np.array(bc, np.float32) * k
    # 번짐 거리장: 잉크통에서의 거리 + 울퉁불퉁한 잡음
    rng = np.random.default_rng(77)
    noise = np.asarray(Image.fromarray((rng.random((h // 18 + 1, w // 18 + 1)) * 255).astype(np.uint8))
                       .resize((w, h), Image.BICUBIC), np.float32) / 255
    fine = np.asarray(Image.fromarray((rng.random((h // 5 + 1, w // 5 + 1)) * 255).astype(np.uint8))
                      .resize((w, h), Image.BICUBIC), np.float32) / 255
    dist = np.hypot(xx - LIGHT[0] * sx, (yy - LIGHT[1] * sy) * 1.25) * (0.75 + 0.5 * noise + 0.12 * fine)
    far = dist.max() * 1.02
    frames = []
    for i in range(DYE_FRAMES):
        r = far * ((i + 1) / DYE_FRAMES) ** 1.15
        feather = 10 + 26 * (i / DYE_FRAMES)
        m = np.clip((r - dist) / feather, 0, 1)
        rim = np.exp(-((dist - r) / 7) ** 2) * (i < DYE_FRAMES - 1)
        alpha = m * 0.42 + rim * 0.28
        rgb = col * (1 - rim[..., None] * 0.35)
        out = np.zeros((h, w, 4), np.uint8)
        out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
        frames.append(Image.fromarray(out, 'RGBA'))
    return frames


# ================================================================ 로고
def logo():
    """붓글씨 로고: 번진 먹 'Ink' + 뒤로 퍼진 빨·초·파 잉크 + 'what are you do' + 붉은 낙관 '잉크'."""
    lw, lh = 640, 250
    sh = Sheet(lw, lh, seed=1001)
    ss = sh.ss
    cx = lw / 2
    # 글자 뒤 물감 번짐
    for k, (key, dx, dy) in enumerate((('red', -110, 10), ('green', 0, -10), ('blue', 110, 6))):
        sh.wash(cx + dx, 120 + dy, 70, 56, INK_COLORS[key], alpha=110, layers=3, edge=0.9, blur=8, wobble=0.3)
    big = sh.text_mask('Ink', brush(230), cx - 14, 186, anchor='ms').filter(ImageFilter.MaxFilter(9))
    small = sh.text_mask('what are you do', brush(52), cx + 6, 230, anchor='ms').filter(ImageFilter.MaxFilter(3))

    def lay(mask, color, alpha=255):
        if alpha < 255:
            mask = mask.point(lambda v: v * alpha // 255)
        layer_ = Image.new('RGBA', sh.img.size, tuple(color) + (0,))
        layer_.putalpha(mask)
        sh.img.alpha_composite(layer_)
    # 먹 번짐 테두리 (물기 머금은 한지)
    lay(big.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(5 * ss)), (90, 90, 104), 130)
    sh.img.alpha_composite(wash_layer(sh.img.size, big, SUMI, 1.0, edge=0.8, seed=1002, ss=ss))
    lay(big, SUMI, 220)
    lay(small, SUMI, 240)
    # 먹 튐
    splatter(sh, cx + 150, 60, 20, SUMI, 7)
    splatter(sh, cx - 170, 170, 14, SUMI, 5)
    # 붉은 낙관 (도장)
    px, py, pw = cx + 210, 168, 50
    seal = [(px - pw / 2, py - pw / 2), (px + pw / 2, py - pw / 2 + 1), (px + pw / 2 - 1, py + pw / 2),
            (px - pw / 2 + 1, py + pw / 2 - 1)]
    ink_wash(sh, seal, VERMILION, 0.95, edge=0.4)
    t = Image.new('L', sh.img.size, 0)
    ImageDraw.Draw(t).text((px * ss, (py - 11) * ss), '잉', font=brush(28 * ss), fill=255, anchor='mm')
    ImageDraw.Draw(t).text((px * ss, (py + 12) * ss), '크', font=brush(28 * ss), fill=255, anchor='mm')
    lay(t, HANJI, 245)
    sh.add_glow((255, 252, 244), blur=6, strength=1.4)
    return sh.result(crop=True, margin=10)


# ================================================================ 모래시계
def ink_bottle():
    """붓으로 그린 모래시계: 위 칸 번진 먹, 아래 칸 물기 있게 스며든 빨·초·파."""
    bw, bh = 230, 340
    cx = bw / 2
    sh = Sheet(bw, bh, seed=1101)
    ss = sh.ss
    top, bottom = 58, 282
    neck = (top + bottom) / 2
    left = bezier((cx - 74, top), (cx - 84, top + 80), (cx - 13, neck - 30), (cx - 8, neck), 30) + \
        bezier((cx - 8, neck), (cx - 13, neck + 30), (cx - 84, bottom - 80), (cx - 74, bottom), 30)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask((bw, bh), left + right[::-1])

    glass = Sheet(bw, bh, seed=1102)
    glass.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], (250, 248, 240), 190)
    m_black = Image.new('L', glass.img.size, 0)
    ImageDraw.Draw(m_black).polygon([(0, (top + 32) * ss), (bw * ss, (top + 28) * ss), (bw * ss, (neck + 4) * ss),
                                     (0, (neck + 4) * ss)], fill=255)
    glass.img.alpha_composite(wash_layer(glass.img.size, m_black, SUMI, 2.2, edge=1.0, seed=1103, ss=ss))  # 진한 먹
    glass.stroke([(cx, neck), (cx + 1, neck + 30), (cx, bottom - 58)], 2.4, SUMI, 230, amp=0.4)
    for y0, y1, key in ((bottom - 64, bottom - 42, 'red'), (bottom - 44, bottom - 20, 'green'),
                        (bottom - 22, bh, 'blue')):
        m = Image.new('L', glass.img.size, 0)
        ImageDraw.Draw(m).polygon([(0, y0 * ss), (bw * ss, (y0 + 3) * ss), (bw * ss, y1 * ss), (0, y1 * ss)], fill=255)
        glass.img.alpha_composite(wash_layer(glass.img.size, m, INK_COLORS[key], 0.95, edge=0.9,
                                             seed=1104 + y0, ss=ss))
    sh.masked(glass, inner)
    for side in (left, right):
        brush_stroke(sh, side, 5.5, SUMI, 245, dry=0.25)
    sh.stroke([(cx - 54, top + 18), (cx - 62, top + 52), (cx - 42, top + 86)], 3.0, WHITE, 230, amp=0.4)
    for x in (cx - 90, cx + 90):
        brush_stroke(sh, [(x, top - 6), (x + 1, bottom + 6)], 5, (60, 50, 46), 235, dry=0.4)
    for y in (top - 12, bottom + 12):
        brush_stroke(sh, [(cx - 104, y + 2), (cx, y - 1), (cx + 106, y + 1)], 22, (60, 48, 42), 245, dry=0.55)
    splatter(sh, cx + 80, top + 10, 18, SUMI, 5)
    sh.add_glow((255, 252, 244), blur=9, strength=1.4)
    return sh.result(crop=True, margin=12)


def bottle_glow():
    w, h = 380, 440
    sh = Sheet(w, h, seed=1151)
    sh.wash(w / 2, h / 2, w * 0.36, h * 0.34, (255, 252, 240), alpha=200, layers=4, edge=0.0, blur=18)
    return sh.result()


def light_pool():
    """물 위 동심원 물결."""
    sh = Sheet(280, 70, seed=1152)
    for k, (rx, ry, a) in enumerate(((50, 7, 170), (82, 11, 130), (114, 15, 90))):
        sh.stroke(ellipse_points(140, 35, rx, ry, 40), 2.0, (90, 92, 110), a, amp=0.3, taper=False)
    return sh.result()


# ================================================================ 버튼 · 설정
def button(label, color, seed, hover, size=(260, 84)):
    """먹 붓질 한 획 버튼: 한지색 붓글씨. hover 면 원소 색 잉크 붓질로."""
    bw, bh = size
    sh = Sheet(bw, bh, seed=seed)
    stroke_col = color if hover else (34, 34, 42)
    brush_stroke(sh, [(26, bh / 2 + 3), (bw / 2, bh / 2 - 2), (bw - 22, bh / 2 + 1)], 46, stroke_col, 240, dry=0.55)
    if hover:
        splatter(sh, bw - 30, bh / 2 - 22, 12, color, 5)
    f = brush(46)
    sh.ink_text(label, f, bw / 2, bh / 2 + 2, HANJI, 255, anchor='mm')
    sh.add_glow((255, 252, 244), blur=5, strength=1.3 if hover else 0.8)
    return sh.result()


def settings_panel():
    """족자: 한지 화면 + 위아래 먹색 축 + 붓글씨."""
    sh = Sheet(PANEL_W, PANEL_H, seed=1201)
    page = hanji(PANEL_W - 80, PANEL_H - 60, seed=1202)
    shadow = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((46, 36, PANEL_W - 34, PANEL_H - 24), fill=(40, 36, 40, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    canvas = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(page, (40, 30))
    sh.img.alpha_composite(canvas.resize(sh.img.size, Image.BICUBIC))
    sh.wash(PANEL_W * 0.78, PANEL_H * 0.75, 160, 110, INK_COLORS['blue'], alpha=40, layers=2, edge=0.6, blur=12)
    sh.wash(PANEL_W * 0.2, PANEL_H * 0.3, 130, 90, INK_COLORS['red'], alpha=34, layers=2, edge=0.6, blur=12)
    for y in (30, PANEL_H - 30):  # 축
        brush_stroke(sh, [(18, y), (PANEL_W / 2, y - 1), (PANEL_W - 18, y)], 18, (54, 42, 38), 250, dry=0.2)
        for x in (12, PANEL_W - 12):
            sh.wash(x, y, 9, 11, (54, 42, 38), alpha=255, layers=1, edge=0.4, blur=0.6)
    sh.ink_text('설정', brush(64), PANEL_W / 2, 78, SUMI, 255, anchor='mm')
    brush_stroke(sh, [(PANEL_W / 2 - 60, 104), (PANEL_W / 2 + 64, 101)], 6, VERMILION, 230, dry=0.6)
    for i, label in enumerate(SETTING_ROWS):
        y = 150 + i * 70
        sh.ink_text(label, brush(44), 80, y, SUMI, 255, anchor='lm')
    return sh.result()


def slider_track(filled=False):
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=1211 if filled else 1212)
    if filled:
        grad = [INK_COLORS['red'], (220, 150, 60), INK_COLORS['green'], INK_COLORS['blue']]
        n = len(grad)
        for k, col in enumerate(grad):
            a, b = 8 + (tw - 16) * k / n, 8 + (tw - 16) * (k + 1) / n
            brush_stroke(sh, [(a - 6, 18), (b + 6, 18)], 12, col, 230, dry=0.2)
    else:
        brush_stroke(sh, [(8, 19), (tw / 2, 17), (tw - 8, 19)], 5, (60, 60, 70), 220, dry=0.6)
    return sh.result()


def slider_knob():
    s_ = 44
    sh = Sheet(s_, s_, seed=1213)
    sh.wash(s_ / 2, s_ / 2, 11, 11, SUMI, alpha=245, layers=2, edge=1.2, blur=0.8, wobble=0.12)
    sh.wash(s_ / 2 - 3, s_ / 2 - 3, 3, 3, (255, 252, 244), alpha=230, layers=1, blur=0.4)
    return sh.result()


def toggle(on):
    """켜짐: 붉은 낙관 도장 / 꺼짐: 붓으로 그린 빈 원(일원상)."""
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=1221 if on else 1222)
    cx_, cy_ = 32, th / 2
    if on:
        seal = [(cx_ - 17, cy_ - 17), (cx_ + 17, cy_ - 16), (cx_ + 16, cy_ + 17), (cx_ - 16, cy_ + 16)]
        ink_wash(sh, seal, VERMILION, 0.95, edge=0.5)
        sh.ink_text('印', ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 20), cx_, cy_, HANJI, 245, anchor='mm')
    else:
        pts = ellipse_points(cx_, cy_, 15, 15, 40, math.pi * 0.6, math.pi * 1.8)
        brush_stroke(sh, pts, 5, SUMI, 230, dry=0.6)
    sh.ink_text('켜짐' if on else '꺼짐', brush(36), 90, th / 2 + 1, SUMI if on else (110, 108, 116), 255, anchor='mm')
    return sh.result()


# ================================================================ 효과
def bubble(tint, seed):
    """물방울처럼 맺힌 옅은 잉크 방울."""
    sz = 72
    sh = Sheet(sz, sz, seed=seed)
    sh.wash(sz / 2, sz / 2, 22, 22, tint, alpha=90, layers=2, edge=2.0, blur=2.5, wobble=0.06)
    sh.stroke(ellipse_points(sz / 2, sz / 2, 15, 15, 12, math.radians(200), math.radians(60)), 2.8, WHITE, 230, amp=0.2)
    return sh.result()


def mote(color, seed):
    s_ = 40
    sh = Sheet(s_, s_, seed=seed)
    sh.wash(s_ / 2, s_ / 2, 6, 6, color, alpha=230, layers=1, edge=1.2, blur=1.0, wobble=0.2)
    return sh.result()


def sparkle():
    s_ = 48
    sh = Sheet(s_, s_, seed=1261)
    splatter(sh, s_ / 2, s_ / 2, 14, SUMI, 7)
    sh.wash(s_ / 2, s_ / 2, 5, 5, SUMI, alpha=240, layers=1, edge=1.0, blur=0.5)
    return sh.result()


def main():
    save(background(), TITLE, 'background.png')
    for i, f in enumerate(dye_frames()):
        save(f, TITLE, f'dye_{i}.png')
    save(logo(), TITLE, 'logo.png')
    save(empty(), TITLE, 'logo_glow.png')
    save(ink_bottle(), TITLE, 'ink_bottle.png')
    save(bottle_glow(), TITLE, 'bottle_glow.png')
    save(light_pool(), TITLE, 'light_pool.png')
    for name, label, color, seed in (('start', '시작하기', INK_COLORS['red'], 1081),
                                     ('settings', '설정', INK_COLORS['green'], 1083),
                                     ('quit', '끝내기', INK_COLORS['blue'], 1082)):
        save(button(label, color, seed, False), TITLE, f'button_{name}.png')
        save(button(label, color, seed, True), TITLE, f'button_{name}_hover.png')
    for i, (name, tint) in enumerate((('pearl', (120, 124, 140)), ('pink', INK_COLORS['red']),
                                      ('lavender', (130, 110, 200)), ('sky', INK_COLORS['blue']))):
        save(bubble(tint, 1240 + i), TITLE, f'bubble_{name}.png')
    for i, (name, c) in enumerate((('pearl', SUMI), ('sky', INK_COLORS['blue']), ('lavender', (120, 100, 190)),
                                   ('gold', (220, 150, 60)), ('pink', INK_COLORS['red']))):
        save(mote(c, 1250 + i), TITLE, f'mote_{name}.png')
    save(sparkle(), TITLE, 'sparkle.png')

    save(Image.new('RGBA', (16, 16), (30, 30, 38, 255)), SETTINGS, 'dim.png')
    save(settings_panel(), SETTINGS, 'panel.png')
    save(slider_track(), SETTINGS, 'slider_track.png')
    save(slider_track(filled=True), SETTINGS, 'slider_fill.png')
    save(slider_knob(), SETTINGS, 'slider_knob.png')
    save(toggle(True), SETTINGS, 'toggle_on.png')
    save(toggle(False), SETTINGS, 'toggle_off.png')
    save(button('닫기', VERMILION, 1231, False, (220, 84)), SETTINGS, 'button_close.png')
    save(button('닫기', VERMILION, 1231, True, (220, 84)), SETTINGS, 'button_close_hover.png')


if __name__ == '__main__':
    main()
