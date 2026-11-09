"""'파스텔' 그림체(처음 만든 파스텔 수채화 타이틀)의 부품을 같은 그림체로 그린다.

배경은 처음 버전 컬러 배경(git cd3721a 의 image/title/background.png)을 흑백으로 바꿔 깔고,
모래시계에서부터 색이 번져 나가는 물들이기 층(dye_*.png)을 만든다.
여기서는 한 줄 손글씨 로고, 위 칸이 검정 잉크인 모래시계, 감자꽃 손글씨 쪽지 버튼,
진주 비눗방울, 잉크통 아래 빛 웅덩이, 같은 종이 쪽지 그림체의 설정 창을 그린다.

실행:  python tools/gen_title_pastel.py
결과:  image/title_pastel/*.png, image/settings_pastel/*.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, font, bezier, ellipse_points, paper, PASTEL, PLUM, INK, WATERCOLOR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'fonts')
OUT = os.path.join(ROOT, 'image', 'title_pastel')
WHITE = (255, 255, 255)
SOFT_PLUM = (150, 128, 170)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved', name, img.size)


def poly_mask(size, pts):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def sparkle_stroke(sh, x, y, r, color, alpha=230, width=2.2):
    sh.stroke([(x, y - r), (x + r * 0.15, y), (x, y + r)], width, color, alpha, amp=0.2)
    sh.stroke([(x - r, y), (x, y + r * 0.15), (x + r, y)], width, color, alpha, amp=0.2)


NIGHT_PAPER = (58, 50, 98)       # 밤 버튼 종이: 남보랏빛
NIGHT_TEXT = (226, 218, 236)     # 밤 버튼 글씨: 눈에 띄지 않는 은은한 흰빛


def button(label, fill_color, seed, hover, size=(300, 96), night=False, font_size=40):
    """처음 버전과 같은 종이 쪽지 버튼 (글씨만 감자꽃 손글씨).
    night: 밤 배경용. 달빛 아래 어스름한 종이 — 남보랏빛 종이에 버튼 색을 옅게 섞고,
    펜 선은 낮 버튼과 같은 보랏빛 펜, 글씨는 은은한 흰빛(어두운 그림자). 올리면 색이 밝게 번지고 반짝인다."""
    bw, bh = size
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
    if night:
        k = 0.8 if hover else 0.62  # 버튼 색이 섞이는 정도
        mix = lambda a, b, t: tuple(int(x * (1 - t) + y * t) for x, y in zip(a, b))  # noqa: E731
        tint = mix(NIGHT_PAPER, fill_color, k)
        deep = mix(NIGHT_PAPER, fill_color, k * 0.55)
        light = mix(tint, (255, 250, 240), 0.22)
        fill.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], deep, 255)
        # 물감 얼룩을 여러 겹: 가장자리가 진하게 마른 자국(edge), 농담이 고르지 않게
        rng = fill.rng
        for i in range(4):
            cx_ = x0 + (x1 - x0) * (0.15 + 0.7 * i / 3) + rng.uniform(-14, 14)
            fill.wash(cx_, bh / 2 + rng.uniform(-6, 6), rng.uniform(52, 72), rng.uniform(24, 32), tint,
                      alpha=rng.randint(170, 220), layers=3, edge=1.8, blur=2.5, wobble=0.16)
        # 물이 번져 밝게 빠진 자리 하나 (수채 블룸)
        fill.wash(bw / 2 + rng.uniform(-60, 60), bh / 2 - 4, rng.uniform(26, 36), rng.uniform(12, 16), light,
                  alpha=150 if hover else 110, layers=3, edge=2.2, blur=1.8, wobble=0.2)
    else:
        fill.wash(bw / 2, bh / 2, rx, ry, (255, 252, 248), alpha=255, layers=2, blur=4, wobble=0.04)
        fill.wash(bw / 2, bh / 2, rx, ry, fill_color, alpha=255 if hover else 150, layers=4, blur=4, wobble=0.05)
        fill.wash(bw / 2 - 70, bh / 2 - 8, 60, 14, WHITE, alpha=130, layers=2)
    sh.masked(fill, poly_mask((bw, bh), box))
    sh.stroke(box, 4.2)
    if not night:  # 밤엔 종이 아래 그림자 선이 어두운 땅에 묻혀 지저분해 보여서 뺀다
        sh.stroke([(x0 + 24, y1 + 5), (x1 - 6, y1 + 4)], 2.2, SOFT_PLUM, 150)
    if hover:
        sparkle_stroke(sh, x1 - 4, y0 + 2, 9, (255, 236, 150), 255, 2.6)
        sparkle_stroke(sh, x0 + 6, y1 - 4, 6, WHITE, 255, 2.2)
    f = hand_font(font_size)
    if night:
        sh.ink_text(label, f, bw / 2 + 2, bh / 2 + 4, (34, 28, 60), 140, anchor='mm')  # 옅은 그림자
        text = NIGHT_TEXT
    else:
        sh.ink_text(label, f, bw / 2 + 2, bh / 2 + 4, WHITE, 220, anchor='mm')
        text = PLUM
    sh.ink_text(label, f, bw / 2, bh / 2 + 2, text, 255, anchor='mm')
    sh.ink_text(label, f, bw / 2 + 0.8, bh / 2 + 2, text, 255, anchor='mm')  # 살짝 두껍게
    return sh.result()


def bubble(color, seed):
    s = 64
    sh = Sheet(s, s, seed=seed)
    sh.wash(s / 2, s / 2, 24, 24, color, alpha=110, layers=2, edge=2.2, blur=2, wobble=0.03)
    sh.ellipse(s / 2, s / 2, 24, 24, 1.8, WHITE, 230, amp=0.3)
    sh.stroke(ellipse_points(s / 2, s / 2, 16, 16, 12, math.pi * 1.1, math.pi * 0.35), 3, WHITE, 240, amp=0.2)
    return sh.result()


def light_pool():
    """처음 버전의 잉크통 그림자와 같은 보랏빛 번짐."""
    sh = Sheet(240, 50, seed=45)
    sh.wash(120, 25, 100, 14, (130, 110, 170), alpha=120, layers=3, edge=0.4, blur=5)
    return sh.result()


def ink_bottle(stream=True):
    """처음 버전 모래시계 잉크통과 같은 모양. 위 칸엔 빼앗긴 세상의 검정 잉크, 아래 칸엔 되찾은 색이 쌓인다."""
    bw, bh = 220, 320
    cx = bw / 2
    sh = Sheet(bw, bh, seed=41)
    sh.line = PLUM
    top, bottom = 46, 274
    neck = (top + bottom) / 2
    left = bezier((cx - 78, top), (cx - 86, top + 80), (cx - 14, neck - 30), (cx - 9, neck), 40) +         bezier((cx - 9, neck), (cx - 14, neck + 30), (cx - 86, bottom - 80), (cx - 78, bottom), 40)[1:]
    right = [(2 * cx - x, y) for x, y in left]
    inner = poly_mask((bw, bh), left + right[::-1])

    color = Sheet(bw, bh, seed=42)
    color.wash(cx, neck, 80, 130, (236, 240, 255), alpha=150, layers=2)  # 유리 빛
    # 위 칸: 검정 잉크 (먹 번짐을 겹쳐 진하게, 가장자리는 보랏빛이 살짝 돈다)
    surf = top + 40  # 잉크 수면 (살짝 출렁)
    pool = [(x, surf + 3 * math.sin(x / 9) + 2 * math.sin(x / 4 + 1)) for x in range(0, bw + 1, 4)]
    pool_mask = ImageChops.multiply(poly_mask((bw, bh), pool + [(bw, neck + 6), (0, neck + 6)]), inner)
    ink_fill = Sheet(bw, bh, seed=44)
    ink_fill.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], INK, 250)
    ink_fill.wash(cx + 22, surf + 34, 30, 22, (78, 62, 102), alpha=150, layers=3, blur=4)  # 보랏빛 먹 번짐
    ink_fill.wash(cx - 30, surf + 8, 24, 6, (120, 112, 138), alpha=170, layers=2, blur=2)  # 수면 윤기
    color.masked(ink_fill, pool_mask)
    color.wash(cx, top + 30, 60, 22, WHITE, alpha=130, layers=2, blur=4)
    # 가운데로 떨어지는 줄기: 위는 검정, 아래로 가며 보랏빛 물감이 된다
    if stream:  # 되찾은 색 그림체는 줄기 대신 떨어지는 잉크 방울을 움직여 그린다
        color.stroke([(cx, neck - 20), (cx + 1, neck + 4)], 3, INK, 240, amp=0.5)
        color.stroke([(cx + 1, neck + 4), (cx, bottom - 30)], 3, (180, 120, 200), 230, amp=0.5)
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


def ttf(name, size, variation=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if variation:
        f.set_variation_by_name(variation)
    return f


def lay(sh, mask, color, alpha=255):
    """mask(L, 시트 실제 크기)를 color 로 칠한다."""
    if alpha < 255:
        mask = mask.point(lambda v: v * alpha // 255)
    layer = Image.new('RGBA', sh.img.size, tuple(color) + (0,))
    layer.putalpha(mask)
    sh.img.alpha_composite(layer)


HAND = 'GamjaFlower-Regular.ttf'  # 파스텔 그림체 글씨: 배경 펜 선과 어울리는 둥근 손글씨
INK_TINTS = ((240, 128, 166), (112, 200, 160), (104, 160, 232))  # I·n·k 물감 색 (분홍·민트·하늘)


def hand_font(size):
    return ImageFont.truetype(os.path.join(FONTS, HAND), size)


LOGO_SIZE = (1060, 300)


def logo_masks(ss):
    """한 줄 로고의 글자 마스크 (ss 크기). 파스텔·되찾은 색 로고가 같이 쓴다.
    반환: 'what are you do' 마스크, [(글자 마스크, 왼쪽 x, 폭)] × I·n·k, Ink 전체 마스크, 배치 값."""
    lw, lh = LOGO_SIZE
    size = (lw * ss, lh * ss)
    small = hand_font(int(88 * ss))
    big = hand_font(int(172 * ss))
    line = 'what are you do'
    w_small = small.getlength(line) / ss
    letters = ('I', 'n', 'k')
    widths = [big.getlength(c) / ss for c in letters]
    gap_word, gap_ch = 34, 8
    total = w_small + gap_word + sum(widths) + gap_ch * 2
    x0 = (lw - total) / 2
    base = 196  # 글자 밑선 (PIL y)
    m_small = Image.new('L', size, 0)
    ImageDraw.Draw(m_small).text((x0 * ss, base * ss), line, font=small, fill=255, anchor='ls')
    m_small = m_small.filter(ImageFilter.MaxFilter(3))
    masks = []
    x = x0 + w_small + gap_word
    for ch, wch, dy, ang in zip(letters, widths, (4, -6, 2), (-5, 4, -3)):
        l_, t_, r_, b_ = big.getbbox(ch, anchor='ls')
        cm = Image.new('L', (r_ - l_ + 80, b_ - t_ + 80), 0)
        ImageDraw.Draw(cm).text((40 - l_, 40 - t_), ch, font=big, fill=255, anchor='ls')
        cm = cm.rotate(ang, resample=Image.BICUBIC, expand=True)
        m = Image.new('L', size, 0)
        m.paste(cm, (int((x + wch / 2) * ss - cm.width / 2), int((base + dy + (t_ + b_) / 2 / ss) * ss - cm.height / 2)))
        masks.append((m.filter(ImageFilter.MaxFilter(17)), x, wch))
        x += wch + gap_ch
    m_ink = masks[0][0]
    for m, *_ in masks[1:]:
        m_ink = ImageChops.lighter(m_ink, m)
    return m_small, masks, m_ink, (x0, w_small, gap_word, widths, base)


def logo():
    """한 줄 로고: 보랏빛 펜 손글씨 'what are you do' + 수채 물감으로 칠한 큰 'Ink'.
    배경처럼 펜 선 테두리 + 물감 번짐, 흰 종이 테두리로 또렷하게."""
    lw, lh = LOGO_SIZE
    sh = Sheet(lw, lh, seed=401)
    ss = sh.ss
    m_small, masks, m_ink, (x0, w_small, gap_word, widths, base) = logo_masks(ss)

    # ---- 흰 종이 테두리 + 보랏빛 그늘
    halo = ImageChops.lighter(m_small.filter(ImageFilter.MaxFilter(15)), m_ink.filter(ImageFilter.MaxFilter(29)))
    lay(sh, ImageChops.offset(halo, 3 * ss, 5 * ss).filter(ImageFilter.GaussianBlur(5 * ss)), PLUM, 90)
    lay(sh, halo.filter(ImageFilter.GaussianBlur(1.2 * ss)), (255, 253, 250))

    # ---- 'what are you do': 라벤더 그림자 위에 보랏빛 펜 글씨
    lay(sh, ImageChops.offset(m_small, 3 * ss, 3 * ss), PASTEL['lavender'])
    lay(sh, m_small, PLUM)

    # ---- 'Ink': 글자마다 수채 물감, 살짝 밖으로 번진 물감 + 펜 테두리
    for (m, lx, wch), tint in zip(masks, INK_TINTS):
        small_m = m.resize((lw, lh), Image.BILINEAR)
        spill = Sheet(lw, lh, seed=410 + int(lx))
        spill.wash(lx + wch / 2 + 6, base - 62, wch * 0.62, 78, tint, alpha=110, layers=3, blur=6)
        sh.masked(spill, ImageChops.offset(small_m, 6, 4).filter(ImageFilter.MaxFilter(9)))
        fill = Sheet(lw, lh, seed=420 + int(lx))
        fill.wash(lx + wch / 2, base - 60, wch * 0.7, 86, (255, 252, 248), alpha=255, layers=2, blur=3)
        fill.wash(lx + wch / 2, base - 70, wch * 0.7, 90, tint, alpha=255, layers=4, edge=1.6, blur=4)
        fill.wash(lx + wch / 2, base - 40, wch * 0.5, 50, tuple(int(v * 0.85) for v in tint), alpha=170, layers=3, blur=5)
        fill.wash(lx + wch * 0.35, base - 110, wch * 0.18, 18, WHITE, alpha=150, layers=2, blur=3)
        sh.masked(fill, small_m)
    outline = ImageChops.subtract(m_ink.filter(ImageFilter.MaxFilter(13)), m_ink)  # 굵은 펜 테두리
    lay(sh, outline, PLUM)

    # ---- 장식: 밑줄 물결, 물감 방울, 반짝이
    ux0, ux1 = x0 + 8, x0 + w_small - 8
    sh.stroke(bezier((ux0, base + 22), (ux0 + 160, base + 12), (ux1 - 160, base + 34), (ux1, base + 20), 40), 4, PLUM)
    ink_x0 = x0 + w_small + gap_word
    sh.splatter(ink_x0 - 6, base - 150, 22, INK_TINTS[0], count=4, size=(2, 5))
    sh.splatter(ink_x0 + sum(widths) + 22, base - 120, 30, INK_TINTS[2], count=6, size=(2, 6))
    sh.splatter(ink_x0 + sum(widths) * 0.55, base + 28, 34, INK_TINTS[1], count=5, size=(1.5, 4))
    for (sx, sy, r, c) in ((ink_x0 + sum(widths) + 44, base - 168, 12, (255, 222, 120)),
                           (x0 - 18, base - 86, 9, (255, 222, 120)), (ink_x0 - 30, base - 172, 7, WHITE)):
        sparkle_stroke(sh, sx, sy, r, c, 255, 3)
    return sh.result(crop=True, margin=14)


def soft_glow(w, h, color, seed, alpha=170):
    sh = Sheet(w, h, seed=seed)
    sh.wash(w / 2, h / 2, w * 0.4, h * 0.38, color, alpha=alpha, layers=4, edge=0.2, blur=14)
    sh.wash(w / 2, h / 2, w * 0.25, h * 0.22, WHITE, alpha=120, layers=3, edge=0.1, blur=12)
    return sh.result()


# ================================================================ 설정 창 (settings_mode 와 위치를 맞춘다)
SETTINGS_OUT = os.path.join(ROOT, 'image', 'settings_pastel')
PANEL_W, PANEL_H = 760, 560
ROW0 = 180  # 첫 항목의 패널 y (캔버스 y 460 = 360 + 560/2 - 180)
SETTING_ROWS = (('배경음', 'pink'), ('효과음', 'peach'), ('붓자국 효과', 'mint'), ('빛 입자 효과', 'sky'))


def save_settings(img, name):
    os.makedirs(SETTINGS_OUT, exist_ok=True)
    img.save(os.path.join(SETTINGS_OUT, name))
    print('saved settings_pastel/' + name, img.size)


def wobbly_box(x0, y0, x1, y1, r, rng, amp=2.0):
    """손으로 그린 둥근 네모 (윤곽 점 목록, 닫힘)."""
    pts = []
    for cx_, cy_, a0 in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0),
                         (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        for i in range(9):
            a = a0 + math.pi / 2 * i / 8
            pts.append((cx_ + math.cos(a) * r + rng.uniform(-amp, amp) * 0.3,
                        cy_ + math.sin(a) * r + rng.uniform(-amp, amp) * 0.3))
    return pts + [pts[0]]


def thick_text(sh, text, f, x, y, color, anchor='mm'):
    """손글씨를 살짝 두껍게 (두 번 겹쳐 찍기)."""
    sh.ink_text(text, f, x, y, color, 255, anchor=anchor)
    sh.ink_text(text, f, x + 0.7, y, color, 255, anchor=anchor)


def settings_panel():
    """수채화 종이 쪽지 창: 크림색 종이에 파스텔 번짐, 보랏빛 펜 테두리 두 줄, 손글씨 항목 이름.
    행 높이는 settings_mode.ROW_Y (패널 y = ROW0 + i*70) 와 같다."""
    sh = Sheet(PANEL_W, PANEL_H, seed=501)
    sh.line = PLUM
    box = (26, 26, PANEL_W - 26, PANEL_H - 26)
    outline = wobbly_box(*box, 26, sh.rng)
    shadow = Sheet(PANEL_W, PANEL_H, seed=502)
    shadow.fill_poly([(x + 6, y + 8) for x, y in outline], (120, 96, 150), 90)
    sh.img.alpha_composite(shadow.img.filter(ImageFilter.GaussianBlur(8 * sh.ss)))
    paper_ = Sheet(PANEL_W, PANEL_H, seed=503)
    paper_.fill_poly([(0, 0), (PANEL_W, 0), (PANEL_W, PANEL_H), (0, PANEL_H)], (255, 251, 246), 250)
    paper_.wash(150, 110, 200, 120, PASTEL['pink'], alpha=110, layers=3, blur=10)
    paper_.wash(620, 440, 240, 140, PASTEL['sky'], alpha=110, layers=3, blur=10)
    paper_.wash(660, 130, 130, 90, PASTEL['lemon'], alpha=90, layers=3, blur=10)
    paper_.wash(120, 470, 140, 90, PASTEL['mint'], alpha=90, layers=3, blur=10)
    sh.masked(paper_, poly_mask((PANEL_W, PANEL_H), outline))
    sh.stroke(outline, 4.4)
    sh.stroke(wobbly_box(box[0] + 12, box[1] + 12, box[2] - 12, box[3] - 12, 18, sh.rng), 1.8, SOFT_PLUM, 170,
              amp=0.8)
    # 제목
    title_f = hand_font(52)
    sh.ink_text('설정', title_f, PANEL_W / 2 + 2, 92, WHITE, 230, anchor='mm')
    thick_text(sh, '설정', title_f, PANEL_W / 2, 90, PLUM)
    sh.stroke(bezier((PANEL_W / 2 - 60, 122), (PANEL_W / 2 - 20, 116), (PANEL_W / 2 + 20, 126), (PANEL_W / 2 + 60, 119)),
              3, PLUM)
    sparkle_stroke(sh, PANEL_W / 2 + 78, 74, 10, (255, 222, 120), 255, 2.8)
    sparkle_stroke(sh, PANEL_W / 2 - 80, 102, 6, (255, 222, 120), 255, 2.2)
    # 항목: 물감 점 + 손글씨, 사이사이 연한 연필 줄
    row_f = hand_font(36)
    for i, (label, tint) in enumerate(SETTING_ROWS):
        y = ROW0 + i * 70
        sh.wash(72, y, 10, 9, PASTEL[tint], alpha=255, layers=3, edge=1.2, blur=1)
        sh.ellipse(72, y, 9, 8, 2, PLUM, 230, amp=0.4)
        thick_text(sh, label, row_f, 96, y + 2, PLUM, anchor='lm')
        if i < len(SETTING_ROWS) - 1:
            sh.stroke([(70, y + 35), (PANEL_W - 70, y + 35)], 1.4, SOFT_PLUM, 90, amp=1.0)
    return sh.result()


def rounded_bar(tw, th):
    bar = Image.new('L', (tw, th), 0)
    ImageDraw.Draw(bar).rounded_rectangle((8, 11, tw - 8, th - 11), radius=7, fill=255)
    return bar


def slider_track(filled=False):
    """펜으로 그린 홈 + 채운 쪽은 분홍→라벤더 수채 물감 띠."""
    tw, th = 300, 36
    sh = Sheet(tw, th, seed=511 if filled else 512)
    sh.line = PLUM
    tmp = Sheet(tw, th, seed=513)
    if filled:
        stops = [PASTEL[k] for k in ('pink', 'peach', 'lemon', 'mint', 'sky', 'lavender')]
        for k in range(14):
            c = stops[int(k / 13 * (len(stops) - 1) + 0.5)]
            tmp.wash(14 + k * (tw - 28) / 13, th / 2, 16, 8, tuple(int(v * 0.9) for v in c), alpha=240,
                     layers=2, edge=1.0, blur=1.5, wobble=0.1)
        sh.masked(tmp, rounded_bar(tw, th))
        sh.stroke([(14, th / 2 - 3), (tw - 14, th / 2 - 3)], 1.6, WHITE, 160, amp=0.4)
    else:
        tmp.fill_poly([(0, 0), (tw, 0), (tw, th), (0, th)], (255, 252, 248), 255)
        sh.masked(tmp, rounded_bar(tw, th))
        sh.stroke([(14, 11), (tw - 14, 11.5)], 2.4, PLUM, 230, amp=0.6)
        sh.stroke([(14, th - 11), (tw - 14, th - 11.5)], 2.4, PLUM, 230, amp=0.6)
        sh.stroke(ellipse_points(14, th / 2, 6, 7, 10, math.pi / 2, math.pi), 2.4, PLUM, 230, amp=0.3)
        sh.stroke(ellipse_points(tw - 14, th / 2, 6, 7, 10, -math.pi / 2, math.pi), 2.4, PLUM, 230, amp=0.3)
    return sh.result()


def slider_knob():
    """손잡이: 크림색 동그라미 + 펜 테두리 + 반짝."""
    s_ = 44
    sh = Sheet(s_, s_, seed=521)
    sh.wash(s_ / 2 + 1, s_ / 2 + 2, 13, 13, (120, 96, 150), alpha=90, layers=2, blur=2)
    sh.wash(s_ / 2, s_ / 2, 13, 13, (255, 252, 246), alpha=255, layers=2, edge=0.2, blur=0.6, wobble=0.04)
    sh.wash(s_ / 2, s_ / 2, 12, 12, PASTEL['lavender'], alpha=120, layers=2, blur=1)
    sh.ellipse(s_ / 2, s_ / 2, 13, 13, 2.6, PLUM, 255, amp=0.3)
    sh.wash(s_ / 2 - 4, s_ / 2 - 4, 3, 3, WHITE, alpha=255, layers=1, blur=0.4)
    return sh.result()


def toggle(on):
    """종이 알약 토글: 켜지면 분홍 물감이 번지고 동그라미가 오른쪽, 꺼지면 크림색에 왼쪽."""
    tw, th = 130, 52
    sh = Sheet(tw, th, seed=531 if on else 532)
    sh.line = PLUM
    outline = wobbly_box(12, 10, tw - 12, th - 10, 16, sh.rng, 1.2)
    fill = Sheet(tw, th, seed=533)
    fill.fill_poly([(0, 0), (tw, 0), (tw, th), (0, th)], (255, 252, 248), 255)
    if on:
        fill.wash(tw / 2, th / 2, 52, 18, (240, 150, 184), alpha=230, layers=3, edge=1.2, blur=2)
        fill.wash(tw / 2 - 20, th / 2 - 6, 18, 4, WHITE, alpha=140, layers=1, blur=1.5)
    sh.masked(fill, poly_mask((tw, th), outline))
    sh.stroke(outline, 3)
    kx = tw - 32 if on else 32
    sh.wash(kx, th / 2, 11, 11, WHITE, alpha=255, layers=2, edge=0.2, blur=0.6, wobble=0.04)
    sh.ellipse(kx, th / 2, 11, 11, 2.4, PLUM, 255, amp=0.3)
    sh.ink_text('켜짐' if on else '꺼짐', hand_font(24), 50 if on else tw - 48, th / 2 + 1,
                PLUM if on else SOFT_PLUM, 255, anchor='mm')
    if on:
        sparkle_stroke(sh, tw - 10, 9, 6, (255, 222, 120), 255, 2)
    return sh.result()


# ================================================================ 물들이기 (흑백 → 색)
DYE_FRAMES = 10
DYE_FROM = (640, 720 - 262)  # 모래시계 자리 (PIL 좌표)에서부터 색이 번진다


def color_background():
    """처음 버전 컬러 배경 (git cd3721a)."""
    import io
    import subprocess
    raw = subprocess.run(['git', 'show', 'cd3721a:image/title/background.png'], cwd=ROOT,
                         capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(raw)).convert('RGB')


def gray_background(col):
    """색을 빼앗긴 세상: 물체마다 다른 회색으로 칠한 흑백 동화 그림.
    색마다 다른 회색으로 바꾸면 보랏빛 펜 선은 저절로 짙은 먹색이 되어 컬러 그림과 굵기가 같다.
    어두운 곳(동굴 안)엔 연필 빗금을 더한다."""
    w, h = col.size
    lum_img = col.convert('L')

    # 그늘 정도 (넓게 흐린 밝기) → 두 단계 빗금
    soft = np.asarray(lum_img.filter(ImageFilter.GaussianBlur(4)), np.float32)
    tone = np.clip((240 - soft) / 80, 0, 1)  # 옅은 먹 번짐용
    dark = np.clip((182 - soft) / 60, 0, 1)  # 빗금은 하늘보다 어두운 곳에만
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(93)
    wob = np.asarray(Image.fromarray((rng.random((h // 20 + 1, w // 20 + 1)) * 255).astype(np.uint8))
                     .resize((w, h), Image.BICUBIC), np.float32) / 255
    def stripes(u, gap, width):
        ph = (u + wob * 3) % gap
        return np.clip(1 - np.abs(ph - gap / 2) / width, 0, 1)
    hatch1 = stripes(xx + yy * 0.9, 8.0, 1.1) * np.clip(dark / 0.3, 0, 1)
    hatch2 = stripes(xx - yy * 1.1, 10.0, 1.0) * np.clip((dark - 0.45) / 0.3, 0, 1)
    breakup = np.asarray(Image.fromarray((rng.random((h // 5 + 1, w // 5 + 1)) * 255).astype(np.uint8))
                         .resize((w, h), Image.BICUBIC), np.float32) / 255
    hatch = np.clip(hatch1 + hatch2, 0, 1) * (0.45 + 0.55 * breakup) * 0.5
    wash = tone * 0.14                                                 # 아주 옅은 먹 번짐

    # 물체마다 다른 회색: 파스텔 색은 밝기가 비슷해 그냥 흑백으로 바꾸면 한 가지 회색이 된다.
    # 파랑을 빼고 빨강·초록으로 밝기를 매긴 뒤 대비를 키워, 하늘·라벤더는 짙게 · 분홍·레몬은 옅게 갈라 놓는다.
    rgb = np.asarray(col, np.float32)
    g = rgb[..., 0] * 0.62 + rgb[..., 1] * 0.38
    g = 250 - (250 - g) * 1.6
    g = np.asarray(Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.4)),
                   np.float32)
    grain = np.asarray(paper(w, h, seed=97).convert('L'), np.float32) / 244  # 도화지 결
    gray = np.clip(g * grain, 40, 255)[..., None] * np.array((1.0, 0.985, 0.965), np.float32)

    ink = np.array((46, 42, 52), np.float32)
    k = np.clip(wash * 0.5 + hatch, 0, 1)[..., None]
    out = gray * (1 - k) + ink * k
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def dye_frames(col):
    """모래시계에서부터 수채 물감이 번져 나가는 단계별 색 층. 끝은 울퉁불퉁하고 진한 물 자국이 진다."""
    w, h = col.size
    rgb = np.asarray(col, np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(91)
    noise = np.asarray(Image.fromarray((rng.random((h // 24 + 1, w // 24 + 1)) * 255).astype(np.uint8))
                       .resize((w, h), Image.BICUBIC), np.float32) / 255
    fine = np.asarray(Image.fromarray((rng.random((h // 6 + 1, w // 6 + 1)) * 255).astype(np.uint8))
                      .resize((w, h), Image.BICUBIC), np.float32) / 255
    dist = np.hypot(xx - DYE_FROM[0], (yy - DYE_FROM[1]) * 1.25) * (0.75 + 0.4 * noise + 0.12 * fine)
    far = dist.max() * 1.02
    frames = []
    for i in range(DYE_FRAMES):
        r = far * ((i + 1) / DYE_FRAMES) ** 1.15
        m = np.clip((r - dist) / (16 + 26 * i / DYE_FRAMES), 0, 1)
        last = i == DYE_FRAMES - 1
        rim = 0 if last else np.exp(-((dist - r + 4) / 7) ** 2)
        out = np.zeros((h, w, 4), np.float32)
        out[..., :3] = rgb * (1 - rim * 0.18)[..., None] if not last else rgb
        out[..., 3] = np.clip(m + rim * 0.5, 0, 1) * 255
        frames.append(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA'))
    return frames


def main():
    col = color_background()
    save(gray_background(col), 'background.png')
    for i, f in enumerate(dye_frames(col)):
        save(f, f'dye_{i}.png')
    save(logo(), 'logo.png')
    save(soft_glow(1060, 300, (255, 250, 240), 302, alpha=190), 'logo_glow.png')
    save(ink_bottle(), 'ink_bottle.png')
    save(button('시작하기', PASTEL['pink'], 81, False), 'button_start.png')
    save(button('시작하기', PASTEL['pink'], 81, True), 'button_start_hover.png')
    save(button('끝내기', PASTEL['sky'], 82, False), 'button_quit.png')
    save(button('끝내기', PASTEL['sky'], 82, True), 'button_quit_hover.png')
    save(button('설정', PASTEL['lavender'], 83, False), 'button_settings.png')
    save(button('설정', PASTEL['lavender'], 83, True), 'button_settings_hover.png')
    save(bubble((236, 232, 246), 136), 'bubble_pearl.png')
    save(light_pool(), 'light_pool.png')
    save_settings(Image.new('RGBA', (16, 16), (120, 96, 150, 255)), 'dim.png')  # 알파 채널이 있어야 opacify가 먹는다
    save_settings(settings_panel(), 'panel.png')
    save_settings(slider_track(), 'slider_track.png')
    save_settings(slider_track(filled=True), 'slider_fill.png')
    save_settings(slider_knob(), 'slider_knob.png')
    save_settings(toggle(True), 'toggle_on.png')
    save_settings(toggle(False), 'toggle_off.png')
    save_settings(button('닫기', PASTEL['peach'], 541, False, (220, 84)), 'button_close.png')
    save_settings(button('닫기', PASTEL['peach'], 541, True, (220, 84)), 'button_close_hover.png')


if __name__ == '__main__':
    main()
