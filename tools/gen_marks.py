"""역할 마크 생성 → image/common/mark_<역할>.png (유닛 발밑에 붙는 작은 동그라미 배지)

탱커 = 방패, 근접 딜러 = 칼, 원거리 딜러 = 활과 화살, 서포터 = 치료 십자.

실행: python tools/gen_marks.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_title_pastel as pastel  # noqa: E402
from sketch import Sheet, ellipse_points, PASTEL, PLUM  # noqa: E402

OUT = os.path.join(pastel.ROOT, 'image', 'common')
S = 48           # 배지 크기
C = S / 2
TINT = {'tank': 'sky', 'melee': 'pink', 'ranged': 'mint', 'support': 'lemon'}


def badge(role, seed):
    sh = Sheet(S, S, seed=seed)
    sh.line = PLUM
    ring = ellipse_points(C, C, C - 4, C - 4)
    sh.fill_poly(ring, (255, 252, 247), 250)
    sh.wash(C, C, C - 8, C - 8, PASTEL[TINT[role]], alpha=170, layers=2, blur=2)
    sh.stroke(ring, 2.6, amp=0.3)
    if role == 'tank':
        shield = [(C - 10, C - 12), (C + 10, C - 12), (C + 10, C + 2), (C, C + 13), (C - 10, C + 2)]
        sh.fill_poly(shield, (196, 214, 240))
        sh.stroke(shield + [shield[0]], 2.6, amp=0.2, taper=False)
        sh.stroke([(C, C - 9), (C, C + 8)], 1.8, amp=0.1)
        sh.stroke([(C - 7, C - 3), (C + 7, C - 3)], 1.8, amp=0.1)
    elif role == 'melee':
        d = (math.cos(math.radians(-50)), math.sin(math.radians(-50)))   # 손잡이 → 칼끝 (오른쪽 위)
        p = (-d[1], d[0])
        hilt = (C - 9, C + 10)
        tip = (hilt[0] + d[0] * 26, hilt[1] + d[1] * 26)
        g = (hilt[0] + d[0] * 6, hilt[1] + d[1] * 6)
        sh.stroke([g, tip], 4.6, amp=0.1, taper=False, color=(170, 180, 200))
        sh.stroke([g, tip], 1.6, amp=0.1, taper=False)
        sh.stroke([(g[0] - p[0] * 7, g[1] - p[1] * 7), (g[0] + p[0] * 7, g[1] + p[1] * 7)], 3.0, amp=0.1, taper=False)
        sh.stroke([(hilt[0] - d[0] * 3, hilt[1] - d[1] * 3), g], 3.4, amp=0.1, taper=False, color=(160, 110, 90))
    elif role == 'ranged':
        bow = ellipse_points(C - 3, C, 9, 14, n=24, start=math.pi / 2, sweep=math.pi)   # 왼쪽으로 휜 활
        sh.stroke(bow, 3.0, amp=0.2, taper=False, color=(150, 104, 80))
        sh.stroke([(C - 3, C - 14), (C - 3, C + 14)], 1.2, amp=0.05, taper=False)          # 활시위
        sh.stroke([(C - 12, C), (C + 12, C)], 1.8, amp=0.05, taper=False)                 # 화살대
        sh.fill_poly([(C + 14, C), (C + 8, C - 4), (C + 8, C + 4)], PLUM)                 # 화살촉
        sh.stroke([(C - 12, C), (C - 15, C - 4)], 1.4, amp=0.05)
        sh.stroke([(C - 12, C), (C - 15, C + 4)], 1.4, amp=0.05)
    else:
        a, w = 12, 4.5   # 치료 십자
        cross = [(C - w, C - a), (C + w, C - a), (C + w, C - w), (C + a, C - w), (C + a, C + w), (C + w, C + w),
                 (C + w, C + a), (C - w, C + a), (C - w, C + w), (C - a, C + w), (C - a, C - w), (C - w, C - w)]
        sh.fill_poly(cross, (120, 196, 140))
        sh.stroke(cross + [cross[0]], 2.2, amp=0.15, taper=False)
    return sh.result()


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, role in enumerate(TINT):
        img = badge(role, 1700 + i)
        img.save(os.path.join(OUT, f'mark_{role}.png'))
        print('saved common/mark_' + role, img.size)


if __name__ == '__main__':
    main()
