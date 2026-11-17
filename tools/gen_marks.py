"""역할 마크 생성 → image/common/mark_<역할>.png (카드 이름 자리·유닛 발밑·체력바 옆에 붙는 작은 무기 그림)

틀 고르기 카드의 밑그림과 같은 손그림: 보랏빛 펜 선(살짝 떨림) + 옅은 수채 물감.
탱커 = 방패, 근접 딜러 = 칼, 원거리 딜러 = 활과 화살, 서포터 = 별 지팡이.

실행: python tools/gen_marks.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sketch import Sheet, PASTEL, PLUM  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'image', 'common')
S = 64                      # 결과 크기 (쓰는 곳에서 28~34px 로 줄여 그린다)
PEN = 4.2                   # 펜 굵기 (줄였을 때 다른 그림 선 굵기와 비슷하게)
PAPER = (255, 252, 247)


def bar(p0, p1, w):
    (x0, y0), (x1, y1) = p0, p1
    n = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / n * w / 2, (x1 - x0) / n * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def star(cx, cy, r1, r2, n=5):
    return [(cx + (r1 if i % 2 == 0 else r2) * math.cos(math.radians(-90 + 180 / n * i)),
             cy + (r1 if i % 2 == 0 else r2) * math.sin(math.radians(-90 + 180 / n * i))) for i in range(n * 2)]


def shape(sh, pts, tint, alpha=210):
    """종이색 바탕 + 수채 물감 + 펜 윤곽."""
    sh.fill_poly(pts, PAPER, 235)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    layer = Sheet(S, S, seed=sh.rng.randint(0, 9999))
    layer.wash(cx, cy, (max(xs) - min(xs)) / 2 + 4, (max(ys) - min(ys)) / 2 + 4, tint, alpha=alpha, layers=3, blur=2)
    sh.img.alpha_composite(_clip(layer.img, pts, sh.ss))
    sh.stroke(list(pts) + [pts[0], pts[1]], PEN, amp=0.5, taper=False)


def _clip(img, pts, ss):
    from PIL import Image, ImageDraw
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    out = img.copy()
    a = out.split()[3]
    from PIL import ImageChops
    out.putalpha(ImageChops.multiply(a, m))
    return out


def tank(sh):
    shape(sh, [(14, 13), (32, 8), (50, 13), (50, 33), (32, 56), (14, 33)], PASTEL['sky'])
    sh.stroke([(32, 17), (32, 46)], 3.0, amp=0.4)
    sh.stroke([(21, 27), (43, 27)], 3.0, amp=0.4)


def melee(sh):
    a = math.radians(-50)
    u = (math.cos(a), math.sin(a))
    p = (-u[1], u[0])
    hilt = (17, 50)
    g = (hilt[0] + u[0] * 9, hilt[1] + u[1] * 9)
    tip = (hilt[0] + u[0] * 47, hilt[1] + u[1] * 47)
    b = bar(g, (tip[0] - u[0] * 7, tip[1] - u[1] * 7), 11)
    shape(sh, b[:2] + [tip] + b[2:], PASTEL['lavender'])
    shape(sh, bar((g[0] - p[0] * 11, g[1] - p[1] * 11), (g[0] + p[0] * 11, g[1] + p[1] * 11), 7), PASTEL['lemon'])
    shape(sh, bar((hilt[0] - u[0] * 4, hilt[1] - u[1] * 4), g, 7), PASTEL['peach'])


def ranged(sh):
    outer = [(22 + 19 * math.cos(math.radians(t)), 32 + 25 * math.sin(math.radians(t))) for t in range(-80, 81, 8)]
    inner = [(22 + 12 * math.cos(math.radians(t)), 32 + 22 * math.sin(math.radians(t))) for t in range(80, -81, -8)]
    shape(sh, outer + inner, PASTEL['peach'])
    sh.stroke([outer[0], outer[-1]], 2.2, amp=0.2, taper=False)             # 활시위
    sh.stroke([(12, 32), (50, 32)], 3.0, amp=0.3)                            # 화살대
    shape(sh, [(57, 32), (46, 25), (46, 39)], PASTEL['mint'])               # 화살촉
    sh.stroke([(14, 32), (8, 25)], 2.6, amp=0.2)                             # 깃
    sh.stroke([(14, 32), (8, 39)], 2.6, amp=0.2)


def support(sh):
    a = math.radians(-62)
    u = (math.cos(a), math.sin(a))
    base = (22, 57)
    head = (base[0] + u[0] * 30, base[1] + u[1] * 30)
    shape(sh, bar(base, head, 7), PASTEL['peach'])
    shape(sh, star(head[0] + 3, head[1] - 6, 17, 8), PASTEL['lemon'], alpha=240)


DRAW = {'tank': tank, 'melee': melee, 'ranged': ranged, 'support': support}


def mark(role, seed):
    sh = Sheet(S, S, seed=seed)
    sh.line = PLUM
    DRAW[role](sh)
    return sh.result()


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, role in enumerate(DRAW):
        img = mark(role, 1800 + i)
        img.save(os.path.join(OUT, f'mark_{role}.png'))
        print('saved common/mark_' + role, img.size)


if __name__ == '__main__':
    main()
