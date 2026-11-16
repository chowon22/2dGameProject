"""유닛 틀 4종 (PRD 4.1). pico2d 와 무관한 순수 데이터·로직.

틀마다 역할이 떠오르는 귀여운 꼬마 하나: 탱커 = 큰 방패 기사, 근접 딜러 = 칼 든 검사, 원거리 딜러 = 활 든 궁수,
서포터 = 별 지팡이 마법사.
- parts: 부위(머리·몸통·팔·다리 …)마다 타원('e') 또는 다각형('p'). 뒤에 적은 부위가 겹친 곳을 차지한다
- details: 눈·입·방패 무늬·활시위 같은 밑그림 선 (부위는 아님)
- gear: 무기·방패 부위. 몸·손과 GEAR_GAP 넘게 떨어져 있어 따로 움직이기(애니메이션) 쉽다
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


def _bar(p0, p1, w):
    """p0 → p1 굵기 w 막대 (다각형)."""
    (x0, y0), (x1, y1) = p0, p1
    length = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / length * w / 2, (x1 - x0) / length * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def _star(cx, cy, r1, r2, n=5):
    return [(cx + (r1 if i % 2 == 0 else r2) * math.cos(math.radians(-90 + 180 / n * i)),
             cy + (r1 if i % 2 == 0 else r2) * math.sin(math.radians(-90 + 180 / n * i))) for i in range(n * 2)]


def _spiky(cx, cy, r_in, r_out, a0, a1, n):
    """머리 위 삐죽 머리카락: a0 → a1 사이를 안·밖 반지름으로 번갈아."""
    pts = [(cx + r_in * math.cos(math.radians(a0)), cy + r_in * math.sin(math.radians(a0)) + 10)]
    for i in range(n * 2 + 1):
        a = math.radians(a0 + (a1 - a0) * i / (n * 2))
        r = r_out if i % 2 else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append((cx + r_in * math.cos(math.radians(a1)), cy + r_in * math.sin(math.radians(a1)) + 10))
    return pts


def _face(x, y, cheeks=False):
    """꼬마 얼굴: 동그란 눈 둘 + 웃는 입 (+ 볼)."""
    out = [_dot(x - 22, y, 6), _dot(x + 22, y, 6), _arc(x, y + 14, 12, 8, 20, 160, 8)]
    if cheeks:
        out += [_arc(x - 40, y + 14, 10, 6, 0, 360, 10), _arc(x + 40, y + 14, 10, 6, 0, 360, 10)]
    return tuple(out)


# 꼬마 사람 넷: 큰 머리, 작은 몸 (2.5 등신). X 는 사람 가운데 (소품이 오른쪽에 있어 조금 왼쪽으로)
_T, _M, _R, _S = CX - 70, CX - 50, CX - 60, CX - 50
# 무기·방패(gear)는 손·몸에서 GEAR_GAP 넘게 떨어뜨려 둔다 → 나중에 따로 떼어 흔들거나 휘두르는 애니메이션을 붙이기 쉽게
GEAR_GAP = 14

FRAMES = (
    {'id': 'tank', 'name': '탱커', 'stat': '체력', 'look': '큰 방패를 든 꼬마 기사', 'gear': ('shield',),
     'parts': (
         ('leg_l', 'e', _T - 28, 330, 22, 34), ('leg_r', 'e', _T + 28, 330, 22, 34),
         ('body', 'p', [(_T - 58, 178), (_T + 58, 178), (_T + 68, 302), (_T - 68, 302)]),
         ('arm_l', 'e', _T - 78, 234, 20, 40), ('arm_r', 'e', _T + 78, 234, 20, 40),
         ('shield', 'p', [(_T + 122, 160), (_T + 244, 160), (_T + 244, 250), (_T + 183, 330), (_T + 122, 250)]),
         ('head', 'e', _T, 132, 66, 58),
         ('helmet', 'p', _arc(_T, 132, 74, 70, 180, 360, 18) + [(_T + 74, 118), (_T - 74, 118)])),
     'details': _face(_T, 146) + (
         [(_T - 74, 120), (_T + 74, 120)],                                   # 투구 챙
         _arc(_T, 62, 14, 26, 180, 360, 10),                                 # 투구 꼭대기 술
         [(_T + 183, 182), (_T + 183, 292)], [(_T + 146, 222), (_T + 220, 222)],  # 방패 십자
         [(_T - 62, 252), (_T + 62, 252)])},                                 # 허리띠
    {'id': 'melee', 'name': '근접 딜러', 'stat': '공격력', 'look': '칼을 치켜든 꼬마 검사', 'gear': ('weapon', 'guard'),
     'parts': (
         ('leg_l', 'e', _M - 26, 332, 20, 34), ('leg_r', 'e', _M + 26, 332, 20, 34),
         ('body', 'p', [(_M - 46, 180), (_M + 46, 180), (_M + 56, 302), (_M - 56, 302)]),
         ('arm_l', 'e', _M - 66, 236, 18, 40), ('arm_r', 'e', _M + 66, 236, 18, 40),
         ('weapon', 'p', _bar((_M + 132, 262), (_M + 202, 82), 24)),        # 칼날 + 손잡이
         ('guard', 'p', _bar((_M + 118, 213), (_M + 174, 235), 16)),        # 날밑
         ('head', 'e', _M, 132, 64, 58),
         ('hair', 'p', _spiky(_M, 132, 66, 84, 195, 345, 5))),
     'details': _face(_M, 140) + (
         [(_M + 191, 78), (_M + 210, 60), (_M + 213, 86)],                   # 칼끝
         [(_M - 50, 252), (_M + 50, 252)])},                                 # 허리띠
    {'id': 'ranged', 'name': '원거리 딜러', 'stat': '공격력', 'look': '활을 든 꼬마 궁수', 'gear': ('weapon',),
     'parts': (
         ('leg_l', 'e', _R - 26, 332, 20, 34), ('leg_r', 'e', _R + 26, 332, 20, 34),
         ('body', 'p', [(_R - 46, 180), (_R + 46, 180), (_R + 56, 302), (_R - 56, 302)]),
         ('arm_l', 'e', _R - 66, 236, 18, 40),
         ('arm_r', 'e', _R + 80, 214, 34, 14),                              # 활 쪽으로 뻗은 팔
         ('weapon', 'p', _arc(_R + 112, 214, 64, 132, -76, 76, 18) + _arc(_R + 112, 214, 48, 122, 76, -76, 18)),
         ('head', 'e', _R, 132, 64, 58),
         ('hat', 'p', [(_R - 72, 116), (_R + 72, 116), (_R + 30, 62), (_R - 20, 46)])),
     'details': _face(_R, 144) + (
         [(_R + 128, 88), (_R + 128, 340)],                                  # 활시위
         [(_R + 136, 214), (_R + 214, 214)], [(_R + 202, 204), (_R + 218, 214), (_R + 202, 224)],  # 화살
         [(_R + 40, 70), (_R + 86, 36), (_R + 70, 64)],                      # 모자 깃털
         [(_R - 50, 252), (_R + 50, 252)])},
    {'id': 'support', 'name': '서포터', 'stat': '버프량', 'look': '별 지팡이를 든 꼬마 마법사', 'gear': ('weapon', 'star'),
     'parts': (
         ('leg_l', 'e', _S - 26, 350, 20, 22), ('leg_r', 'e', _S + 26, 350, 20, 22),
         ('body', 'p', [(_S - 46, 196), (_S + 46, 196), (_S + 80, 342), (_S - 80, 342)]),
         ('arm_l', 'e', _S - 70, 252, 18, 34), ('arm_r', 'e', _S + 70, 252, 18, 34),
         ('weapon', 'p', _bar((_S + 136, 354), (_S + 152, 136), 13)),       # 지팡이 막대
         ('star', 'p', _star(_S + 154, 104, 34, 15)),
         ('head', 'e', _S, 152, 62, 56),
         ('hat_brim', 'e', _S, 106, 96, 16),
         ('hat', 'p', [(_S - 58, 106), (_S + 58, 106), (_S + 34, 50), (_S + 4, 12), (_S - 22, 40)])),
     'details': _face(_S, 162, cheeks=True) + (
         _star(_S + 6, 72, 12, 5) + [_star(_S + 6, 72, 12, 5)[0]],           # 모자 별
         [(_S - 60, 296), (_S + 60, 296)])},                                 # 옷자락 무늬
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


def gear_names(frame_id):
    """몸에서 떨어져 있는 무기·방패 부위 이름들."""
    return list(get(frame_id)['gear'])


def part_mask(frame_id, size=(PAPER_W, PAPER_H)):
    """(h, w) uint8: 0 = 틀 밖, i = part_names()[i - 1]."""
    img = Image.new('L', size, 0)
    d = ImageDraw.Draw(img)
    sx, sy = size[0] / PAPER_W, size[1] / PAPER_H
    for i, part in enumerate(get(frame_id)['parts'], 1):
        d.polygon([(x * sx, y * sy) for x, y in outline(part)], fill=i)
    return np.asarray(img)
