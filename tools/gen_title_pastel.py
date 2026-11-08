"""'파스텔' 그림체(처음 만든 파스텔 수채화 타이틀)에 나중에 생긴 부품만 같은 그림체로 그린다.

배경·로고·부제목·잉크통·시작/끝내기 버튼은 처음 버전 이미지를 그대로 쓴다
(git cd3721a 의 image/title/*.png → image/title_pastel/).
처음 버전엔 없던 설정 버튼, 진주 비눗방울, 잉크통 아래 빛 웅덩이만 여기서 만든다.

실행:  python tools/gen_title_pastel.py
결과:  image/title_pastel/button_settings*.png, bubble_pearl.png, light_pool.png
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, font, bezier, ellipse_points, PASTEL, PLUM  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def button(label, fill_color, seed, hover):
    """처음 버전과 같은 종이 쪽지 버튼."""
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


def main():
    save(button('설정', PASTEL['lavender'], 83, False), 'button_settings.png')
    save(button('설정', PASTEL['lavender'], 83, True), 'button_settings_hover.png')
    save(bubble((236, 232, 246), 136), 'bubble_pearl.png')
    save(light_pool(), 'light_pool.png')


if __name__ == '__main__':
    main()
