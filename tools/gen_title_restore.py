"""'되찾은 색' 그림체: 파스텔 그림체를 바탕으로, 세상과 함께 로고도 흑백에서 색을 되찾는다.

- 로고: 'Ink' 가 검정 잉크로 시작하고, 번져 오는 물감이 닿으면 I·n·k 가 차례로 빨강·초록·파랑으로 물든다
  (logo.png = 검정 잉크 바탕, logo_ink_0~2.png = 글자마다 얹는 색 층. 모두 같은 크기·같은 자리)
- 모래시계: 줄기를 빼고, 실행 중에 검정 잉크 방울(drip_black)이 떨어져 아래 칸에서 색 방울(drip_splash_*)로 튄다
- 나머지(배경·물들이기·버튼·비눗방울 …)는 파스텔 그림체 이미지를 그대로 쓴다 (assets 의 FALLBACK)

실행:  python tools/gen_title_restore.py
결과:  image/title_restore/*.png
"""
import os
import sys

from PIL import Image, ImageChops, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, bezier, INK, PLUM, PASTEL, WATERCOLOR  # noqa: E402
import gen_title_pastel as pastel  # noqa: E402
from gen_title_pastel import lay, sparkle_stroke, logo_masks, LOGO_SIZE, WHITE  # noqa: E402

ROOT = pastel.ROOT
OUT = os.path.join(ROOT, 'image', 'title_restore')
# I·n·k 가 되찾는 색 = 모래시계 아래 칸에 쌓인 원소 색
TINTS = (WATERCOLOR['red'], WATERCOLOR['green'], WATERCOLOR['blue'])
SPLASH = {'red': WATERCOLOR['red'], 'green': WATERCOLOR['green'], 'blue': WATERCOLOR['blue']}
DARK_LINE = (40, 36, 46)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved', name, img.size)


def logo_layers():
    """[바탕(검정 Ink), I 색 층, n 색 층, k 색 층] — 크롭 전 같은 크기."""
    lw, lh = LOGO_SIZE
    sh = Sheet(lw, lh, seed=601)
    ss = sh.ss
    m_small, masks, m_ink, (x0, w_small, gap_word, widths, base) = logo_masks(ss)
    outline_of = lambda m: ImageChops.subtract(m.filter(ImageFilter.MaxFilter(13)), m)  # noqa: E731

    # ---- 바탕: 흰 종이 테두리, 보랏빛 펜 'what are you do', 검정 잉크 'Ink'
    halo = ImageChops.lighter(m_small.filter(ImageFilter.MaxFilter(15)), m_ink.filter(ImageFilter.MaxFilter(29)))
    lay(sh, ImageChops.offset(halo, 3 * ss, 5 * ss).filter(ImageFilter.GaussianBlur(5 * ss)), PLUM, 90)
    lay(sh, halo.filter(ImageFilter.GaussianBlur(1.2 * ss)), (255, 253, 250))
    lay(sh, ImageChops.offset(m_small, 3 * ss, 3 * ss), PASTEL['lavender'])
    lay(sh, m_small, PLUM)
    for m, lx, wch in masks:
        small_m = m.resize((lw, lh), Image.BILINEAR)
        fill = Sheet(lw, lh, seed=610 + int(lx))
        fill.fill_poly([(0, 0), (lw, 0), (lw, lh), (0, lh)], INK)
        fill.wash(lx + wch / 2, base - 90, wch * 0.4, 40, (72, 66, 82), alpha=90, layers=3, blur=6)  # 먹 농담
        fill.wash(lx + wch * 0.35, base - 110, wch * 0.16, 16, WHITE, alpha=120, layers=2, blur=3)  # 젖은 윤기
        sh.masked(fill, small_m)
    lay(sh, outline_of(m_ink), DARK_LINE)
    ux0, ux1 = x0 + 8, x0 + w_small - 8
    sh.stroke(bezier((ux0, base + 22), (ux0 + 160, base + 12), (ux1 - 160, base + 34), (ux1, base + 20), 40), 4, PLUM)
    ink_x0 = x0 + w_small + gap_word
    sh.splatter(ink_x0 + sum(widths) + 22, base - 120, 30, INK, count=6, size=(2, 6))  # 튄 먹물
    sh.splatter(ink_x0 - 14, base - 150, 20, INK, count=4, size=(1.5, 4))
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


def drip():
    """떨어지는 검정 잉크 방울 (위가 뾰족한 물방울)."""
    w, h = 16, 22
    sh = Sheet(w, h, seed=651)
    sh.fill_poly([(w / 2, 1), (w / 2 + 5, 11), (w / 2 + 6, 15), (w / 2, 20), (w / 2 - 6, 15), (w / 2 - 5, 11)], INK)
    sh.wash(w / 2 - 2, 13, 1.6, 2.4, WHITE, alpha=170, layers=1, blur=0.4)
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
    (base, *letters), centers = logo_layers()
    save(base, 'logo.png')
    for i, im in enumerate(letters):
        save(im, f'logo_ink_{i}.png')
    print('letter centers (logo 중심 기준, 캔버스 좌표):', [(round(x), round(y)) for x, y in centers])
    save(pastel.ink_bottle(stream=False), 'ink_bottle.png')
    save(drip(), 'drip_black.png')
    for i, (name, c) in enumerate(SPLASH.items()):
        save(splash(c, 660 + i), f'drip_splash_{name}.png')


if __name__ == '__main__':
    main()
