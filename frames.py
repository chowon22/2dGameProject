"""유닛 틀 4종 (PRD 4.1). pico2d 와 무관한 순수 데이터·로직.

틀마다 귀여운 생물 하나: 탱커 = 바위 거북, 근접 딜러 = 고양이, 원거리 딜러 = 아기 새, 서포터 = 토끼.
- parts: 부위(머리·몸통·팔·다리 …)마다 타원('e') 또는 다각형('p'). 뒤에 적은 부위가 겹친 곳을 차지한다
- details: 눈·코·등껍질 무늬 같은 밑그림 선 (부위는 아님)
종이에 깔리는 점선 밑그림은 tools/gen_draw.py 가 이 데이터로 그린다 (image/draw/guide_<id>.png).
part_mask() 는 픽셀마다 어느 부위인지 알려 준다 (그림을 부위 PNG 로 나눌 때, PRD 9.1 #4).
좌표는 종이(PAPER_W x PAPER_H)의 왼쪽 위 (0, 0) 기준.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

PAPER_W, PAPER_H = 760, 390
CX = PAPER_W // 2


def _arc(cx, cy, rx, ry, a0, a1, n=12):
    """각도 a0 → a1 (도, 화면 좌표라 아래가 +y) 호 위의 점들."""
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _dot(x, y, r=5):
    return ('dot', x, y, r)


FRAMES = (
    {'id': 'tank', 'name': '탱커', 'stat': '체력', 'creature': '바위 거북',
     'parts': (
         ('tail', 'e', CX - 190, 284, 34, 18),
         ('leg_l', 'e', CX - 112, 322, 46, 42), ('leg_r', 'e', CX + 92, 322, 46, 42),
         ('body', 'e', CX - 10, 222, 172, 118),
         ('head', 'e', CX + 200, 232, 60, 52)),
     'details': (
         _arc(CX - 10, 222, 172, 40, 180, 360, 20),                       # 등껍질 아래 테두리
         [(CX - 70, 150), (CX - 30, 120), (CX + 20, 120), (CX + 55, 150), (CX + 20, 182), (CX - 30, 182),
          (CX - 70, 150)],                                                # 가운데 육각 무늬
         [(CX - 70, 150), (CX - 130, 160)], [(CX + 55, 150), (CX + 115, 160)],
         [(CX - 30, 182), (CX - 50, 222)], [(CX + 20, 182), (CX + 40, 222)],
         _dot(CX + 218, 220), _arc(CX + 222, 244, 16, 10, 20, 160, 8))},  # 눈, 웃는 입
    {'id': 'melee', 'name': '근접 딜러', 'stat': '공격력', 'creature': '고양이',
     'parts': (
         ('tail', 'p', _arc(CX + 92, 268, 84, 76, 100, -10, 14) + _arc(CX + 92, 268, 68, 60, -10, 100, 14)),
         ('leg_l', 'e', CX - 44, 350, 38, 24), ('leg_r', 'e', CX + 44, 350, 38, 24),
         ('body', 'e', CX, 268, 80, 86),
         ('arm_l', 'e', CX - 98, 232, 34, 40), ('arm_r', 'e', CX + 98, 232, 34, 40),
         ('ear_l', 'p', [(CX - 80, 100), (CX - 66, 26), (CX - 20, 66)]),
         ('ear_r', 'p', [(CX + 80, 100), (CX + 66, 26), (CX + 20, 66)]),
         ('head', 'e', CX, 122, 86, 66)),
     'details': (
         _dot(CX - 30, 116), _dot(CX + 30, 116),
         _arc(CX - 8, 140, 8, 6, 0, 180, 6), _arc(CX + 8, 140, 8, 6, 0, 180, 6),        # ㅅ 입
         [(CX - 52, 138), (CX - 96, 130)], [(CX - 52, 146), (CX - 96, 152)],            # 수염
         [(CX + 52, 138), (CX + 96, 130)], [(CX + 52, 146), (CX + 96, 152)],
         [(CX - 108, 220), (CX - 108, 240)], [(CX + 108, 220), (CX + 108, 240)])},      # 주먹 손가락 금
    {'id': 'ranged', 'name': '원거리 딜러', 'stat': '공격력', 'creature': '아기 새',
     'parts': (
         ('tail', 'p', [(CX - 112, 250), (CX - 196, 222), (CX - 186, 252), (CX - 200, 280), (CX - 110, 280)]),
         ('leg_l', 'e', CX - 34, 342, 14, 30), ('leg_r', 'e', CX + 24, 342, 14, 30),
         ('body', 'e', CX - 4, 222, 124, 112),
         ('crest', 'p', [(CX + 8, 100), (CX + 2, 52), (CX + 24, 86), (CX + 40, 50), (CX + 44, 98)]),
         ('beak', 'p', [(CX + 112, 150), (CX + 172, 168), (CX + 110, 186)]),
         ('arm_l', 'e', CX - 54, 240, 64, 40),
         ('head', 'e', CX + 50, 158, 70, 60)),
     'details': (
         _dot(CX + 76, 150, 6), _arc(CX + 66, 178, 14, 8, 0, 180, 6),     # 눈, 볼
         _arc(CX - 54, 240, 46, 22, 20, 160, 10))},                       # 날개 깃
    {'id': 'support', 'name': '서포터', 'stat': '버프량', 'creature': '토끼',
     'parts': (
         ('tail', 'e', CX + 82, 318, 24, 24),
         ('leg_l', 'e', CX - 50, 352, 42, 18), ('leg_r', 'e', CX + 50, 352, 42, 18),
         ('body', 'e', CX, 278, 80, 78),
         ('arm_l', 'e', CX - 74, 258, 24, 34), ('arm_r', 'e', CX + 74, 258, 24, 34),
         ('ear_l', 'e', CX - 34, 66, 22, 60), ('ear_r', 'e', CX + 34, 66, 22, 60),
         ('head', 'e', CX, 162, 74, 60)),
     'details': (
         [(CX - 34, 36), (CX - 34, 96)], [(CX + 34, 36), (CX + 34, 96)],   # 귀 안쪽
         _dot(CX - 28, 156), _dot(CX + 28, 156),
         [(CX - 6, 174), (CX, 180), (CX + 6, 174)],                       # 코
         _arc(CX - 50, 184, 12, 7, 0, 360, 10), _arc(CX + 50, 184, 12, 7, 0, 360, 10))},  # 볼
)
IDS = tuple(f['id'] for f in FRAMES)


def get(frame_id):
    for f in FRAMES:
        if f['id'] == frame_id:
            return f
    raise KeyError(frame_id)


def part_names(frame_id):
    return [p[0] for p in get(frame_id)['parts']]


def outline(part, n=72):
    """부위 윤곽 점들 (닫힘, 종이 좌표)."""
    if part[1] == 'e':
        _, _, cx, cy, rx, ry = part
        return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
                for i in range(n + 1)]
    pts = list(part[2])
    return pts + [pts[0]]


def part_mask(frame_id, size=(PAPER_W, PAPER_H)):
    """(h, w) uint8: 0 = 틀 밖, i = part_names()[i - 1]."""
    img = Image.new('L', size, 0)
    d = ImageDraw.Draw(img)
    sx, sy = size[0] / PAPER_W, size[1] / PAPER_H
    for i, part in enumerate(get(frame_id)['parts'], 1):
        d.polygon([(x * sx, y * sy) for x, y in outline(part)], fill=i)
    return np.asarray(img)
