"""유닛 틀: 역할 4종 (PRD 4.1) x 체형 3종. pico2d 와 무관한 순수 데이터·로직.

역할마다 귀여운 꼬마 하나: 탱커 = 큰 방패 기사, 근접 딜러 = 칼 든 검사, 원거리 딜러 = 활과 화살 든 궁수,
서포터 = 별 지팡이 마법사. 넷 모두 같은 몸·자세(팔은 옆으로 내림)이고 머리 장식과 무기만 다르다.
체형(BODIES): 작은 / 보통 / 큰 — 사람(머리·장식 포함)을 발 자리를 기준으로 늘이거나 줄인다.

종이는 두 장이다:
- 사람 종이 (PERSON_W x PAPER_H): get(역할, 체형) 의 parts·details
- 무기 종이 (GEAR_W x PAPER_H): get(역할) 의 gear 묶음들 — 체형과 상관없이 같다.
  묶음마다 parts, details, 쥐는 점 pivot(무기 종이 위), 손에 쥐었을 때 그 점이 갈 자리 to(사람 종이 위), 돌리는 각 angle.
  묶음(활과 화살처럼)끼리는 GEAR_GAP 넘게 떨어져 있어 따로 떼어 움직이기 쉽다
- split_gear(): 무기 종이 그림을 묶음별로 나눈다, held(): 무기를 손에 쥐었을 때 사람 종이 위 자리
종이에 깔리는 점선 밑그림은 tools/gen_draw.py 가 이 데이터로 그린다.
part_mask() 는 픽셀마다 어느 부위인지 알려 준다 (그림을 부위 PNG 로 나눌 때, PRD 9.1 #4).
좌표는 각 종이의 왼쪽 위 (0, 0) 기준.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

PERSON_W, GEAR_W, PAPER_H = 280, 200, 390
X = PERSON_W // 2              # 사람 가운데 x
WX = GEAR_W // 2               # 무기 종이 가운데 x
FOOT = 366                     # 발바닥 y — 체형을 늘이고 줄이는 기준
GEAR_GAP = 14

BODIES = ('small', 'medium', 'large')
BODY_NAMES = {'small': '작은', 'medium': '보통', 'large': '큰'}
SHORT_NAMES = {'tank': '탱커', 'melee': '근딜', 'ranged': '원딜', 'support': '서포터'}   # 카드처럼 좁은 곳
BODY_SCALE = {'small': (0.8, 0.8), 'medium': (1.0, 1.0), 'large': (1.22, 1.04)}   # (가로, 세로)


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


# ---------------------------------------------------------------- 사람 (보통 체형 기준)
# 네 역할이 함께 쓰는 몸 (머리는 장식 아래 깔려야 해서 따로)
_BODY = (
    ('leg_l', 'e', X - 26, 332, 20, 34), ('leg_r', 'e', X + 26, 332, 20, 34),
    ('body', 'p', [(X - 46, 180), (X + 46, 180), (X + 56, 302), (X - 56, 302)]),
    ('arm_l', 'e', X - 66, 236, 18, 40), ('arm_r', 'e', X + 66, 236, 18, 40))
_HEAD = ('head', 'e', X, 132, 64, 58)
_BELT = [(X - 50, 252), (X + 50, 252)]

# ---------------------------------------------------------------- 무기 (무기 종이 좌표)
_d = (66 / math.hypot(66, 204), -204 / math.hypot(66, 204))   # 칼: 손잡이 → 칼끝 방향
_p = (-_d[1], _d[0])
_HILT, _END = (WX - 33, 300), (WX + 33, 96)
_gc = (_HILT[0] + _d[0] * 40, _HILT[1] + _d[1] * 40)            # 날밑 가운데
_BOW_X = WX - 60                                               # 활 호의 가운데 (활은 그 오른쪽에 걸친다)
_ARROW_X = WX + 34

ROLES = (
    {'id': 'tank', 'name': '탱커', 'stat': '체력', 'look': '큰 방패를 든 꼬마 기사',
     'deco': (('helmet', 'p', _arc(X, 132, 72, 68, 180, 360, 18) + [(X + 72, 118), (X - 72, 118)]),),
     'deco_details': ([(X - 72, 120), (X + 72, 120)], _arc(X, 64, 14, 26, 180, 360, 10)),   # 투구 챙, 꼭대기 술
     'gear': ({'parts': (('shield', 'p', [(WX - 57, 168), (WX + 57, 168), (WX + 57, 252), (WX, 326),
                                          (WX - 57, 252)]),),
               'details': ([(WX, 188), (WX, 300)], [(WX - 37, 226), (WX + 37, 226)]),       # 방패 십자
               'pivot': (WX - 57, 236), 'to': (X + 80, 240), 'angle': 0.0},)},
    {'id': 'melee', 'name': '근접 딜러', 'stat': '공격력', 'look': '칼을 든 꼬마 검사',
     'deco': (('hair', 'p', _spiky(X, 132, 66, 84, 195, 345, 5)),),
     'deco_details': (),
     'gear': ({'parts': (('blade', 'p', _bar(_HILT, _END, 22)),
                         ('guard', 'p', _bar((_gc[0] - _p[0] * 28, _gc[1] - _p[1] * 28),
                                             (_gc[0] + _p[0] * 28, _gc[1] + _p[1] * 28), 15))),
               'details': ([(_END[0] - _p[0] * 11, _END[1] - _p[1] * 11), (_END[0] + _d[0] * 20, _END[1] + _d[1] * 20),
                            (_END[0] + _p[0] * 11, _END[1] + _p[1] * 11)],),          # 칼끝
               'pivot': (_HILT[0] + _d[0] * 18, _HILT[1] + _d[1] * 18), 'to': (X + 76, 270), 'angle': 0.0},)},
    {'id': 'ranged', 'name': '원거리 딜러', 'stat': '공격력', 'look': '활과 화살을 든 꼬마 궁수',
     'deco': (('hat', 'p', [(X - 72, 116), (X + 72, 116), (X + 30, 62), (X - 20, 46)]),),
     'deco_details': ([(X + 40, 70), (X + 86, 36), (X + 70, 64)],),                  # 모자 깃털
     'gear': ({'parts': (('bow', 'p', _arc(_BOW_X, 214, 56, 120, -76, 76, 18) +
                          _arc(_BOW_X, 214, 42, 110, 76, -76, 18)),),
               'details': ([(_BOW_X + 14, 98), (_BOW_X + 14, 330)],),                    # 활시위
               'pivot': (_BOW_X + 49, 214), 'to': (X + 94, 250), 'angle': 0.0},
              # 화살은 옆으로 눕혀(시계 방향 90도) 활시위에 메긴다
              {'parts': (('arrow', 'p', _bar((_ARROW_X, 318), (_ARROW_X, 128), 8)),
                         ('arrow_tip', 'p', [(_ARROW_X - 11, 132), (_ARROW_X, 104), (_ARROW_X + 11, 132)])),
               'details': ([(_ARROW_X - 9, 314), (_ARROW_X, 302), (_ARROW_X + 9, 314)],),   # 화살 깃
               'pivot': (_ARROW_X, 217), 'to': (X + 164, 250), 'angle': -math.pi / 2})},
    {'id': 'support', 'name': '서포터', 'stat': '버프량', 'look': '별 지팡이를 든 꼬마 마법사',
     'deco': (('hat_brim', 'e', X, 86, 92, 15),
              ('hat', 'p', [(X - 54, 86), (X + 54, 86), (X + 30, 46), (X + 4, 16), (X - 20, 40)])),
     'deco_details': (_star(X + 6, 58, 11, 5) + [_star(X + 6, 58, 11, 5)[0]],),      # 모자 별
     'cheeks': True,
     'gear': ({'parts': (('staff', 'p', _bar((WX - 7, 352), (WX + 7, 142), 13)),
                         ('star', 'p', _star(WX + 9, 110, 32, 14))),
               'details': (),
               'pivot': (WX, 262), 'to': (X + 88, 262), 'angle': 0.0},)},
)
IDS = tuple(r['id'] for r in ROLES)
FRAMES = ROLES   # 역할 목록 (이름·능력치 설명용)


# ---------------------------------------------------------------- 체형 맞추기
def _scaler(body):
    sx, sy = BODY_SCALE[body]
    return lambda p: (X + (p[0] - X) * sx, FOOT + (p[1] - FOOT) * sy)


def _scale_part(part, f, sx, sy):
    if part[1] == 'e':
        name, _, cx, cy, rx, ry = part
        x, y = f((cx, cy))
        return (name, 'e', x, y, rx * sx, ry * sy)
    return (part[0], 'p', [f(q) for q in part[2]])


def _map_detail(d, f, k=1.0):
    if d[0] == 'dot':
        x, y = f((d[1], d[2]))
        return ('dot', x, y, d[3] * k)
    return [f(q) for q in d]


_built = {}


def role(frame_id):
    for r in ROLES:
        if r['id'] == frame_id:
            return r
    raise KeyError(frame_id)


def get(frame_id, body='medium'):
    """역할 + 체형 틀: {'id', 'name', 'stat', 'look', 'body', 'parts', 'details'(사람 종이), 'gear'(무기 묶음)}."""
    body = body if body in BODIES else 'medium'
    key = (frame_id, body)
    if key in _built:
        return _built[key]
    r = role(frame_id)
    sx, sy = BODY_SCALE[body]
    f = _scaler(body)
    parts = [_scale_part(p, f, sx, sy) for p in _BODY + (_HEAD,) + r['deco']]
    details = [_map_detail(d, f, min(sx, sy))
               for d in _face(X, 146, r.get('cheeks', False)) + tuple(r['deco_details']) + (_BELT,)]
    gear = tuple({'parts': g['parts'], 'details': g['details'], 'pivot': g['pivot'], 'to': f(g['to']),
                  'angle': g['angle']} for g in r['gear'])
    _built[key] = {'id': frame_id, 'name': r['name'], 'stat': r['stat'], 'look': r['look'], 'body': body,
                   'parts': tuple(parts), 'details': tuple(details), 'gear': gear}
    return _built[key]


def part_names(frame_id, body='medium'):
    """사람 종이 부위 이름들."""
    return [p[0] for p in get(frame_id, body)['parts']]


def gear_groups(frame_id):
    """무기 묶음들. 묶음마다 따로 떼어 움직인다 (활과 화살처럼)."""
    return list(get(frame_id)['gear'])


def gear_names(frame_id):
    return [p[0] for g in gear_groups(frame_id) for p in g['parts']]


def outline(part, n=72):
    """부위 윤곽 점들 (닫힘, 종이 좌표)."""
    if part[1] == 'e':
        _, _, cx, cy, rx, ry = part
        return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
                for i in range(n + 1)]
    pts = list(part[2])
    return pts + [pts[0]]


def _mask(parts, size):
    img = Image.new('L', size, 0)
    d = ImageDraw.Draw(img)
    for i, part in enumerate(parts, 1):
        d.polygon(outline(part), fill=i)
    return np.asarray(img)


def part_mask(frame_id, body='medium'):
    """사람 종이 (h, w) uint8: 0 = 틀 밖, i = part_names()[i - 1]."""
    return _mask(get(frame_id, body)['parts'], (PERSON_W, PAPER_H))


def gear_mask(frame_id):
    """무기 종이 (h, w) uint8: 0 = 밖, i = 묶음 번호 + 1."""
    out = np.zeros((PAPER_H, GEAR_W), np.uint8)
    for i, g in enumerate(gear_groups(frame_id), 1):
        out[_mask(g['parts'], (GEAR_W, PAPER_H)) > 0] = i
    return out


def fit(rgba, w, h=PAPER_H):
    """그림 배열을 w x h 로 (크기가 다르면 가운데 맞춤으로 자르거나 빈 칸을 붙인다)."""
    sh, sw = rgba.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    ox, oy = (w - sw) // 2, (h - sh) // 2
    sx, sy, dx, dy = max(0, -ox), max(0, -oy), max(0, ox), max(0, oy)
    cw, ch = min(sw - sx, w - dx), min(sh - sy, h - dy)
    out[dy:dy + ch, dx:dx + cw] = rgba[sy:sy + ch, sx:sx + cw]
    return out


def split_gear(rgba, frame_id):
    """무기 종이 그림을 묶음마다 한 장씩으로. 칠한 픽셀은 가장 가까운 묶음으로 간다 (밑그림 밖 선도)."""
    groups = gear_groups(frame_id)
    rgba = fit(rgba, GEAR_W)
    if len(groups) == 1:
        return [rgba]
    m = gear_mask(frame_id)
    ys, xs = np.mgrid[0:PAPER_H, 0:GEAR_W]
    # 묶음 윤곽 점까지의 가장 가까운 거리 (안쪽 픽셀은 거리 0)
    dist = []
    for i, g in enumerate(groups, 1):
        d = np.full((PAPER_H, GEAR_W), np.inf)
        for part in g['parts']:
            for a, b in outline(part, 48):
                d = np.minimum(d, (xs - a) ** 2 + (ys - b) ** 2)
        d[m == i] = 0
        dist.append(d)
    owner = np.argmin(np.stack(dist), axis=0)
    out = []
    for i in range(len(groups)):
        piece = rgba.copy()
        piece[owner != i, 3] = 0
        out.append(piece)
    return out


def held(frame_id, group, p, body='medium'):
    """무기 종이 점 p 를, 그 무기 묶음을 손에 쥐었을 때의 사람 종이 위 자리로 (pivot → to, angle 만큼 돌림).
    angle 은 화면에서 반시계가 + (종이 좌표는 y 가 아래로 커서 식을 그에 맞췄다)."""
    g = get(frame_id, body)['gear'][group]
    dx, dy = p[0] - g['pivot'][0], p[1] - g['pivot'][1]
    c, s = math.cos(g['angle']), math.sin(g['angle'])
    return g['to'][0] + dx * c + dy * s, g['to'][1] - dx * s + dy * c
