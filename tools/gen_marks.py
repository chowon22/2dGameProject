"""역할 마크 생성 → image/common/mark_<역할>.png (유닛 발밑·체력바 옆에 붙는 작은 무기 아이콘)

틀의 무기와 같은 모양: 탱커 = 방패, 근접 딜러 = 칼, 원거리 딜러 = 활과 화살, 서포터 = 별 지팡이.
파스텔로 칠하고 보랏빛 펜 선으로 두른 뒤, 어떤 배경 위에서도 보이게 바깥에 흰 테두리를 두른다.
4배 크기로 그려 줄여서 선이 매끈하다.

실행: python tools/gen_marks.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'image', 'common')
S = 48              # 결과 크기
K = 4               # 그릴 때 배율
PLUM = (86, 68, 106, 255)
LINE = 3.2          # 펜 선 굵기 (결과 px)


def P(pts):
    return [(x * K, y * K) for x, y in pts]


def line(d, pts, width=LINE, color=PLUM):
    d.line(P(pts), fill=color, width=round(width * K), joint='curve')
    r = width * K / 2
    for x, y in P([pts[0], pts[-1]]):   # 둥근 끝
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)


def poly(d, pts, fill):
    d.polygon(P(pts), fill=fill)
    line(d, list(pts) + [pts[0]])


def bar(p0, p1, w):
    (x0, y0), (x1, y1) = p0, p1
    n = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / n * w / 2, (x1 - x0) / n * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def star(cx, cy, r1, r2, n=5):
    return [(cx + (r1 if i % 2 == 0 else r2) * math.cos(math.radians(-90 + 180 / n * i)),
             cy + (r1 if i % 2 == 0 else r2) * math.sin(math.radians(-90 + 180 / n * i))) for i in range(n * 2)]


def draw_tank(d):
    shield = [(11, 9), (24, 6), (37, 9), (37, 24), (24, 41), (11, 24)]
    poly(d, shield, (178, 206, 240, 255))
    poly(d, [(15, 12), (24, 10), (33, 12), (33, 23), (24, 35), (15, 23)], (214, 230, 250, 255))
    line(d, [(24, 13), (24, 32)], 2.6)
    line(d, [(17, 20), (31, 20)], 2.6)


def draw_melee(d):
    a = math.radians(-45)
    u = (math.cos(a), math.sin(a))                  # 손잡이 → 칼끝 (오른쪽 위)
    hilt = (12, 36)
    g = (hilt[0] + u[0] * 7, hilt[1] + u[1] * 7)    # 날밑
    tip = (hilt[0] + u[0] * 33, hilt[1] + u[1] * 33)
    blade = bar(g, (tip[0] - u[0] * 5, tip[1] - u[1] * 5), 8.5)
    poly(d, blade[:2] + [tip] + blade[2:], (226, 228, 242, 255))
    line(d, [(g[0] + u[0] * 3, g[1] + u[1] * 3), (tip[0] - u[0] * 7, tip[1] - u[1] * 7)], 1.4, (170, 168, 196, 255))
    p = (-u[1], u[0])
    poly(d, bar((g[0] - p[0] * 8, g[1] - p[1] * 8), (g[0] + p[0] * 8, g[1] + p[1] * 8), 5), (246, 206, 108, 255))
    poly(d, bar((hilt[0] - u[0] * 3, hilt[1] - u[1] * 3), g, 5), (196, 140, 112, 255))


def draw_ranged(d):
    outer = [(17 + 15 * math.cos(math.radians(t)), 24 + 18 * math.sin(math.radians(t))) for t in range(-80, 81, 8)]
    inner = [(17 + 10 * math.cos(math.radians(t)), 24 + 16 * math.sin(math.radians(t))) for t in range(80, -81, -8)]
    poly(d, outer + inner, (210, 160, 120, 255))
    top, bottom = outer[0], outer[-1]
    line(d, [top, bottom], 1.6)                                              # 활시위
    line(d, [(10, 24), (36, 24)], 2.4)                                       # 화살대
    poly(d, [(42, 24), (34, 19), (34, 29)], (150, 210, 170, 255))          # 화살촉
    poly(d, [(12, 24), (7, 19), (10, 24), (7, 29)], (240, 160, 170, 255))  # 깃


def draw_support(d):
    a = math.radians(-60)
    u = (math.cos(a), math.sin(a))
    base = (16, 42)
    head = (base[0] + u[0] * 22, base[1] + u[1] * 22)
    poly(d, bar(base, head, 5), (196, 150, 120, 255))
    poly(d, star(head[0] + 3, head[1] - 4, 13, 6), (250, 214, 100, 255))


DRAW = {'tank': draw_tank, 'melee': draw_melee, 'ranged': draw_ranged, 'support': draw_support}


def mark(role):
    big = Image.new('RGBA', (S * K, S * K), (0, 0, 0, 0))
    DRAW[role](ImageDraw.Draw(big))
    # 바깥 흰 테두리: 알파를 넓혀 흰색으로 깔고 그 위에 그림
    a = big.split()[3].filter(ImageFilter.MaxFilter(2 * K + 1)).filter(ImageFilter.GaussianBlur(K * 0.6))
    halo = Image.new('RGBA', big.size, (255, 252, 247, 0))
    halo.putalpha(a.point(lambda v: min(255, v * 2)))
    halo.alpha_composite(big)
    return halo.resize((S, S), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    for role in DRAW:
        img = mark(role)
        img.save(os.path.join(OUT, f'mark_{role}.png'))
        print('saved common/mark_' + role, img.size)


if __name__ == '__main__':
    main()
