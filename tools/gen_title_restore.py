"""'되찾은 색' 그림체: 파스텔 그림체를 바탕으로, 세상과 함께 로고도 흑백에서 색을 되찾는다.

- 로고: 'Ink' 가 'what are you do' 와 같은 보랏빛 펜 색으로 시작하고, 번져 오는 물감이 닿으면
  I·n·k 가 차례로 빨강·초록·파랑으로 물든다 (logo.png = 바탕, logo_ink_0~2.png = 글자마다 얹는 색 층. 같은 크기·자리)
- 모래시계: 가운데를 똑 뗄 수 있는 두 병. 위는 검정 잉크통, 아래는 컬러 잉크통 (PRD 2.1 두 잉크통).
  목의 가는 이음 고리에서 갈라진다. 실행 중에 검정 잉크 방울(drip_black)이 떨어져
  아래 칸에서 색 방울(drip_splash_*)로 튄다
- 배경: 처음 파스텔 배경을 다시 그려(gen_title_bg) 낮은 달 대신 해, 밤 버전(title_restore_night)은 달과 별.
  각각 흑백 배경 + 물들이기 층(dye_*)을 만든다
- 밤 버전 버튼은 밤 배경에 맞게 따로 그린다 (남보랏빛 종이 + 달빛 펜 선 + 크림빛 글씨)
- 나머지(낮 버튼·비눗방울 …)는 파스텔 그림체 이미지를 그대로 쓴다 (assets 의 FALLBACK)

실행:  python tools/gen_title_restore.py
결과:  image/title_restore/*.png, image/title_restore_night/*.png
"""
import math
import os
import sys

import numpy as np

from PIL import Image, ImageChops, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, bezier, INK, PLUM, PASTEL, WATERCOLOR  # noqa: E402
import gen_title_pastel as pastel  # noqa: E402
import gen_title_bg  # noqa: E402
from gen_title_pastel import lay, sparkle_stroke, logo_masks, LOGO_SIZE, WHITE  # noqa: E402

ROOT = pastel.ROOT
OUT = os.path.join(ROOT, 'image', 'title_restore')
NIGHT_OUT = os.path.join(ROOT, 'image', 'title_restore_night')  # 밤 버전: 배경만 다르고 나머지는 낮 것을 쓴다
# I·n·k 가 되찾는 색 = 모래시계 아래 칸에 쌓인 원소 색
TINTS = (WATERCOLOR['red'], WATERCOLOR['green'], WATERCOLOR['blue'])
SPLASH = {'red': WATERCOLOR['red'], 'green': WATERCOLOR['green'], 'blue': WATERCOLOR['blue']}
# 밤 버튼 색: 파스텔은 너무 옅어 남보라 종이에 섞으면 다 보라가 되므로 채도를 올린 색
_NIGHT_BUTTON_VIVID = {'pink': (222, 112, 166), 'sky': (88, 156, 224), 'lavender': (156, 120, 226)}
NIGHT_DESAT = 0.4  # 같은 밝기의 회색 쪽으로 당기는 정도 (클수록 채도가 낮다)


def _desat(c, k=NIGHT_DESAT):
    g = c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114
    return tuple(int(v + (g - v) * k) for v in c)


NIGHT_BUTTON = {k: _desat(v) for k, v in _NIGHT_BUTTON_VIVID.items()}
DARK_LINE = (58, 44, 76)  # 'Ink' 바탕 테두리: 보랏빛 펜보다 한 톤 짙게


def save(img, name, out=OUT):
    os.makedirs(out, exist_ok=True)
    img.save(os.path.join(out, name))
    print('saved', os.path.basename(out) + '/' + name, img.size)


def save_world(col, out, gray=None):
    """컬러 배경 → 흑백 배경 + 물들이기 층. gray 를 주면 그 흑백 배경을 쓴다."""
    save(gray or pastel.gray_background(col), 'background.png', out)
    for i, f in enumerate(pastel.dye_frames(col)):
        save(f, f'dye_{i}.png', out)


NIGHT_DIM = 0.5  # 밤 흑백 = 낮 흑백 밝기 × 이 값 (달·동굴 빛은 그대로)


def night_gray():
    """밤 흑백 배경: 달이 뜬 낮 흑백과 같은 회색 톤을 그대로 어둡게 하고, 달무리·동굴 빛은 밝게, 별은 하얗게."""
    day = np.asarray(pastel.gray_background(gen_title_bg.background('moon')), np.float32)
    keep = gen_title_bg.night_keep(gen_title_bg.W / 2)[..., None]
    out = day * (NIGHT_DIM * (1 - keep) + keep)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    stars = gen_title_bg.night_stars().result()
    r, g, b, a = stars.split()
    gray_l = stars.convert('L')
    img.alpha_composite(Image.merge('RGBA', (gray_l, gray_l, gray_l, a)))
    return img.convert('RGB')


def logo_layers():
    """[바탕(검정 Ink), I 색 층, n 색 층, k 색 층] — 크롭 전 같은 크기."""
    lw, lh = LOGO_SIZE
    sh = Sheet(lw, lh, seed=601)
    ss = sh.ss
    m_small, masks, m_ink, (x0, w_small, gap_word, widths, base) = logo_masks(ss)
    outline_of = lambda m: ImageChops.subtract(m.filter(ImageFilter.MaxFilter(13)), m)  # noqa: E731

    # ---- 바탕: 흰 종이 테두리, 보랏빛 펜 'what are you do', 같은 보랏빛 펜으로 칠한 'Ink' (아직 색이 없다)
    halo = ImageChops.lighter(m_small.filter(ImageFilter.MaxFilter(15)), m_ink.filter(ImageFilter.MaxFilter(29)))
    lay(sh, ImageChops.offset(halo, 3 * ss, 5 * ss).filter(ImageFilter.GaussianBlur(5 * ss)), PLUM, 90)
    lay(sh, halo.filter(ImageFilter.GaussianBlur(1.2 * ss)), (255, 253, 250))
    lay(sh, ImageChops.offset(m_small, 3 * ss, 3 * ss), PASTEL['lavender'])
    lay(sh, m_small, PLUM)
    lay(sh, ImageChops.offset(m_ink, 4 * ss, 4 * ss), PASTEL['lavender'])  # 'what' 과 같은 라벤더 그림자
    for m, lx, wch in masks:
        small_m = m.resize((lw, lh), Image.BILINEAR)
        fill = Sheet(lw, lh, seed=610 + int(lx))
        fill.fill_poly([(0, 0), (lw, 0), (lw, lh), (0, lh)], PLUM)
        fill.wash(lx + wch / 2, base - 90, wch * 0.4, 40, (112, 92, 138), alpha=110, layers=3, blur=6)  # 펜 농담
        fill.wash(lx + wch * 0.35, base - 110, wch * 0.16, 16, WHITE, alpha=110, layers=2, blur=3)  # 윤기
        sh.masked(fill, small_m)
    lay(sh, outline_of(m_ink), DARK_LINE)
    ux0, ux1 = x0 + 8, x0 + w_small - 8
    sh.stroke(bezier((ux0, base + 22), (ux0 + 160, base + 12), (ux1 - 160, base + 34), (ux1, base + 20), 40), 4, PLUM)
    ink_x0 = x0 + w_small + gap_word
    sh.splatter(ink_x0 + sum(widths) + 22, base - 120, 30, PLUM, count=6, size=(2, 6))  # 튄 잉크
    sh.splatter(ink_x0 - 14, base - 150, 20, PLUM, count=4, size=(1.5, 4))
    sparkle_stroke(sh, x0 - 18, base - 86, 9, WHITE, 255, 3)
    layers = [sh]

    # ---- 글자마다 색 층: 수채 물감 + 보랏빛 펜 테두리 + 그 색 물감 방울·반짝이
    for i, ((m, lx, wch), tint) in enumerate(zip(masks, TINTS)):
        ly = Sheet(lw, lh, seed=620 + i)
        small_m = m.resize((lw, lh), Image.BILINEAR)
        spill = Sheet(lw, lh, seed=630 + i)
        spill.wash(lx + wch / 2 + 6, base - 62, wch * 0.62, 78, tint, alpha=110, layers=3, blur=6)
        ly.masked(spill, ImageChops.offset(small_m, 6, 4).filter(ImageFilter.MaxFilter(9)))
        fill = Sheet(lw, lh, seed=640 + i)
        fill.wash(lx + wch / 2, base - 60, wch * 0.7, 86, (255, 252, 248), alpha=255, layers=2, blur=3)
        light = tuple(min(255, int(v * 0.55 + 255 * 0.45)) for v in tint)  # 위는 맑게
        fill.wash(lx + wch / 2, base - 70, wch * 0.7, 90, light, alpha=255, layers=4, edge=1.6, blur=4)
        fill.wash(lx + wch / 2, base - 40, wch * 0.55, 56, tint, alpha=200, layers=3, blur=5)  # 아래로 고인 물감
        fill.wash(lx + wch * 0.35, base - 110, wch * 0.18, 18, WHITE, alpha=150, layers=2, blur=3)
        ly.masked(fill, small_m)
        lay(ly, outline_of(m), PLUM)
        ly.splatter(lx + wch * 0.5, base - 150 + i * 12, 26, tint, count=4, size=(2, 5))
        sparkle_stroke(ly, lx + wch + 6, base - 160 + i * 8, 10, (255, 222, 120), 255, 3)
        layers.append(ly)

    imgs = [layer.result() for layer in layers]
    box = imgs[0].getbbox()
    for im in imgs[1:]:
        b = im.getbbox()
        box = (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    m = 14
    box = (max(0, box[0] - m), max(0, box[1] - m), min(lw, box[2] + m), min(lh, box[3] + m))
    centers = [((lx + wch / 2) - (box[0] + box[2]) / 2, ((box[1] + box[3]) / 2) - (base - 60))
               for _, lx, wch in masks]
    return [im.crop(box) for im in imgs], centers


def split_bottle():
    """가운데를 뗄 수 있는 모래시계: 위 검정 잉크통 + 아래 컬러 잉크통.
    모양·크기는 파스텔 모래시계와 같아서 InkDrip 의 목·바닥 위치가 그대로 맞는다.
    갈라지는 티는 은근하게: 위 뚜껑과 목 고리만 살짝 다른 나무색, 고리 가운데 연한 이음매 선 하나."""
    bw, bh = 240, 320  # 오른쪽 뚜껑이 잘리지 않게 넉넉히
    cx = bw / 2
    sh = Sheet(bw, bh, seed=41)
    sh.line = PLUM
    top, bottom = 46, 274
    neck = (top + bottom) / 2
    upper = bezier((cx - 78, top), (cx - 86, top + 80), (cx - 14, neck - 30), (cx - 9, neck), 40)
    lower = bezier((cx - 9, neck), (cx - 14, neck + 30), (cx - 86, bottom - 80), (cx - 78, bottom), 40)
    mirror = lambda pts: [(2 * cx - x, y) for x, y in pts]  # noqa: E731
    up_mask = pastel.poly_mask((bw, bh), upper + mirror(upper)[::-1])
    low_mask = pastel.poly_mask((bw, bh), lower + mirror(lower)[::-1])
    dark_wood = (214, 186, 170)  # 검정 잉크통 쪽 나무: 파스텔 나무에 회색을 살짝 섞음

    # ---- 위 병: 검정 잉크 / 아래 병: 모인 색
    glass = Sheet(bw, bh, seed=42)
    glass.wash(cx, neck, 80, 130, (236, 240, 255), alpha=150, layers=2)
    surf = top + 40
    pool = [(x, surf + 3 * math.sin(x / 9) + 2 * math.sin(x / 4 + 1)) for x in range(0, bw + 1, 4)]
    ink_fill = Sheet(bw, bh, seed=44)
    ink_fill.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], INK, 250)
    ink_fill.wash(cx + 22, surf + 34, 30, 22, (78, 62, 102), alpha=150, layers=3, blur=4)
    ink_fill.wash(cx - 30, surf + 8, 24, 6, (120, 112, 138), alpha=170, layers=2, blur=2)
    pool_mask = pastel.poly_mask((bw, bh), pool + [(bw, neck + 6), (0, neck + 6)])
    glass.masked(ink_fill, ImageChops.multiply(pool_mask, up_mask))
    glass.wash(cx, top + 30, 60, 22, WHITE, alpha=130, layers=2, blur=4)
    glass.wash(cx - 22, bottom - 16, 34, 16, WATERCOLOR['red'], alpha=220, layers=3)
    glass.wash(cx + 20, bottom - 14, 32, 15, WATERCOLOR['blue'], alpha=220, layers=3)
    glass.wash(cx, bottom - 24, 22, 12, WATERCOLOR['green'], alpha=220, layers=3)
    sh.masked(glass, ImageChops.lighter(up_mask, low_mask))

    for pts in (upper, mirror(upper), lower, mirror(lower)):
        sh.stroke(pts, 4.4)
    sh.stroke(bezier((cx - 58, top + 22), (cx - 66, top + 60), (cx - 40, top + 92), (cx - 26, top + 104), 20),
              4, WHITE, 240, amp=0.6)
    sh.stroke(bezier((cx - 58, bottom - 30), (cx - 64, bottom - 50), (cx - 52, bottom - 70), (cx - 44, bottom - 80), 14),
              3, WHITE, 220, amp=0.6)

    # ---- 뚜껑·받침: 위 병은 먹빛 나무, 아래 병은 파스텔 나무
    for y, d, wood in ((top, -1, dark_wood), (bottom, 1, PASTEL['peach'])):
        y0, y1 = (y - 26, y + 2) if d < 0 else (y - 2, y + 26)
        sh.wash(cx, (y0 + y1) / 2, 94, 13, wood, alpha=240, layers=2, blur=2)
        sh.wash(cx - 40, (y0 + y1) / 2 - 3, 40, 5, WHITE, alpha=120, layers=1, blur=2)
        sh.stroke([(cx - 96, y0), (cx + 96, y0 + 1), (cx + 98, y1), (cx - 95, y1 - 1), (cx - 96, y0 - 2)], 4.2)
        for k in range(5):
            xx = cx - 70 + k * 35
            sh.stroke([(xx, y0 + 7), (xx + 10, y1 - 7)], 1.8, pastel.SOFT_PLUM, 160)

    # ---- 양옆 기둥: 이어진 채 그대로
    for x in (cx - 88, cx + 88):
        sh.stroke([(x, top + 2), (x + 1, bottom - 2)], 4)

    # ---- 목 이음 고리: 가는 띠 하나에 연한 이음매 선만 (여기서 두 병이 갈라진다는 것만 살짝)
    rw, rh = 15, 7
    sh.wash(cx, neck, rw, rh, dark_wood, alpha=235, layers=2, edge=0.3, blur=0.8, wobble=0.04)
    sh.wash(cx - 6, neck - 3, 6, 1.5, WHITE, alpha=130, layers=1, blur=0.8)
    sh.stroke([(cx - rw, neck - rh), (cx + rw, neck - rh + 0.5), (cx + rw + 0.5, neck + rh), (cx - rw, neck + rh - 0.5),
               (cx - rw, neck - rh - 1)], 2.8)
    sh.stroke([(cx - rw + 3, neck), (cx + rw - 3, neck)], 1.2, pastel.SOFT_PLUM, 170, amp=0.3)  # 이음매
    # 목(cx)이 이미지 가로 한가운데 오도록 좌우 대칭으로 자른다 (잉크 방울을 이미지 중심에 그리므로)
    img = sh.result()
    l_, t_, r_, b_ = img.getbbox()
    half = int(max(cx - l_, r_ - cx)) + 4
    return img.crop((int(cx) - half, max(0, t_ - 4), int(cx) + half, min(bh, b_ + 4)))


def drip():
    """떨어지는 검정 잉크 방울: 아래가 둥글고 위로 갈수록 가늘어지는 눈물 모양."""
    w, h = 16, 22
    sh = Sheet(w, h, seed=651)
    cx, cy, r = w / 2, 15, 6.2
    body = [(cx + math.cos(math.pi * i / 20) * r, cy + math.sin(math.pi * i / 20) * r) for i in range(21)]  # 아래 반원
    left = bezier((cx - r, cy), (cx - r, cy - 5), (cx - 1.5, cy - 9), (cx, 1), 12)
    right = [(2 * cx - x, y) for x, y in left[::-1]]
    sh.fill_poly(right + body[::-1][1:] + left[1:], INK)
    sh.fill_poly(body, INK)
    sh.wash(cx - 2.4, cy - 1.5, 1.4, 2.2, WHITE, alpha=180, layers=1, blur=0.4)  # 윤기
    return sh.result()


def splash(color, seed):
    """아래 칸에 닿으며 톡 튀는 색 방울."""
    w, h = 48, 28
    sh = Sheet(w, h, seed=seed)
    sh.wash(w / 2, h - 9, 13, 6, color, alpha=240, layers=3, edge=1.2, blur=1)
    for dx, dy, r in ((-14, -8, 2.6), (13, -9, 2.4), (-6, -14, 2), (7, -15, 1.8)):
        sh.wash(w / 2 + dx, h - 9 + dy, r, r, color, alpha=240, layers=1, blur=0.5)
    return sh.result()


def main():
    save_world(gen_title_bg.background('sun'), OUT)                    # 낮: 달 대신 해
    save_world(gen_title_bg.background('moon', night=True), NIGHT_OUT, night_gray())  # 밤: 달과 별
    for name, label, tint, seed in (('start', '시작하기', 'pink', 81), ('quit', '끝내기', 'sky', 82),
                                    ('settings', '설정', 'lavender', 83)):  # 밤 버튼: 달빛 아래 어스름한 종이
        color = NIGHT_BUTTON[tint]
        save(pastel.button(label, color, seed, False, night=True), f'button_{name}.png', NIGHT_OUT)
        save(pastel.button(label, color, seed, True, night=True), f'button_{name}_hover.png', NIGHT_OUT)
    (base, *letters), centers = logo_layers()
    save(base, 'logo.png')
    for i, im in enumerate(letters):
        save(im, f'logo_ink_{i}.png')
    print('letter centers (logo 중심 기준, 캔버스 좌표):', [(round(x), round(y)) for x, y in centers])
    save(split_bottle(), 'ink_bottle.png')
    save(drip(), 'drip_black.png')
    for i, (name, c) in enumerate(SPLASH.items()):
        save(splash(c, 660 + i), f'drip_splash_{name}.png')


if __name__ == '__main__':
    main()
