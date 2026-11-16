"""유닛 틀: 역할 4종 (PRD 4.1) x 체형 3종. pico2d 와 무관한 순수 데이터·로직.

역할마다 귀여운 꼬마 하나: 탱커 = 큰 방패 기사, 근접 딜러 = 칼 든 검사, 원거리 딜러 = 활과 화살 든 궁수,
서포터 = 별 지팡이 마법사. 넷 모두 같은 몸·자세(팔은 옆으로 내림)이고 머리 장식과 무기만 다르다.
체형(BODIES): 작은 / 보통 / 큰 — 사람·무기·종이 크기가 함께 바뀐다.

종이는 여러 장이다 (get(역할, 체형)):
- 사람 종이: 'size' (w, h), 'parts'·'details'
- 무기 종이: 'gear' 의 묶음마다 한 장 (방패 / 칼 / 활 / 화살 / 지팡이 — 원딜은 활과 화살 두 장).
  묶음마다 이름 'name', 종이 'size', 'parts', 'details', 쥐는 점 'pivot'(그 무기 종이 위),
  손에 쥐었을 때 그 점이 갈 자리 'to'(사람 종이 위), 돌리는 각 'angle'(화면에서 반시계 +)
held(): 무기 종이 점이 손에 쥐었을 때 사람 종이 어디로 가는지.
종이에 깔리는 점선 밑그림은 tools/gen_draw.py 가 이 데이터로 그린다.
part_mask() 는 픽셀마다 어느 부위인지 알려 준다 (그림을 부위 PNG 로 나눌 때, PRD 9.1 #4).
좌표는 각 종이의 왼쪽 위 (0, 0) 기준.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

# 보통 체형 기준 크기
PERSON_W, PAPER_H = 280, 390
X = PERSON_W // 2              # 사람 가운데 x
FOOT = 366                     # 발바닥 y (종이 아래에서 24)
FOOT_MARGIN = PAPER_H - FOOT

BODIES = ('small', 'medium', 'large')
BODY_NAMES = {'small': '작은', 'medium': '보통', 'large': '큰'}
SHORT_NAMES = {'tank': '탱커', 'melee': '근딜', 'ranged': '원딜', 'support': '서포터'}   # 카드처럼 좁은 곳
BODY_SCALE = {'small': (0.8, 0.8), 'medium': (1.0, 1.0), 'large': (1.22, 1.04)}   # 사람 (가로, 세로)
GEAR_SCALE = {'small': 0.8, 'medium': 1.0, 'large': 1.15}                       # 무기 (가로세로 같이)
PAPER_SCALE = {'small': (0.8, 0.8), 'medium': (1.0, 1.0), 'large': (1.22, 1.0)}   # 종이 (큰 체형은 화면 높이 때문에 세로 그대로)


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
_BODY = (
    ('leg_l', 'e', X - 26, 332, 20, 34), ('leg_r', 'e', X + 26, 332, 20, 34),
    ('body', 'p', [(X - 46, 180), (X + 46, 180), (X + 56, 302), (X - 56, 302)]),
    ('arm_l', 'e', X - 72, 240, 25, 50), ('arm_r', 'e', X + 72, 240, 25, 50))   # 팔: 그릴 자리가 넉넉하게
_HEAD = ('head', 'e', X, 132, 64, 58)
_BELT = [(X - 50, 252), (X + 50, 252)]

# ---------------------------------------------------------------- 무기 (보통 체형 기준, 묶음마다 자기 종이 좌표)
_SW = 120                                                      # 칼 종이 폭
_d = (66 / math.hypot(66, 204), -204 / math.hypot(66, 204))   # 칼: 손잡이 → 칼끝 방향
_p = (-_d[1], _d[0])
_HILT, _END = (_SW / 2 - 33, 300), (_SW / 2 + 33, 96)
_gc = (_HILT[0] + _d[0] * 40, _HILT[1] + _d[1] * 40)            # 날밑 가운데
_BW = 100                                                      # 활 종이 폭
_BOW = 15                                                      # 활 호의 가운데 (활은 그 오른쪽에 걸친다)
_AW = 70                                                       # 화살 종이 폭
_A = _AW / 2
_TW = 110                                                      # 지팡이 종이 폭
_T = _TW / 2
_HW = 150                                                      # 방패 종이 폭
_H = _HW / 2

ROLES = (
    {'id': 'tank', 'name': '탱커', 'stat': '체력', 'look': '큰 방패를 든 꼬마 기사',
     'deco': (('helmet', 'p', _arc(X, 132, 72, 68, 180, 360, 18) + [(X + 72, 118), (X - 72, 118)]),),
     'deco_details': ([(X - 72, 120), (X + 72, 120)], _arc(X, 64, 14, 26, 180, 360, 10)),   # 투구 챙, 꼭대기 술
     'gear': ({'name': '방패', 'w': _HW,
               'parts': (('shield', 'p', [(_H - 57, 168), (_H + 57, 168), (_H + 57, 252), (_H, 326),
                                          (_H - 57, 252)]),),
               'details': ([(_H, 188), (_H, 300)], [(_H - 37, 226), (_H + 37, 226)]),       # 방패 십자
               'pivot': (_H - 57, 236), 'to': (X + 92, 246), 'angle': 0.0},)},
    {'id': 'melee', 'name': '근접 딜러', 'stat': '공격력', 'look': '칼을 든 꼬마 검사',
     'deco': (('hair', 'p', _spiky(X, 132, 66, 84, 195, 345, 5)),),
     'deco_details': (),
     'gear': ({'name': '칼', 'w': _SW,
               'parts': (('blade', 'p', _bar(_HILT, _END, 22)),
                         ('guard', 'p', _bar((_gc[0] - _p[0] * 28, _gc[1] - _p[1] * 28),
                                             (_gc[0] + _p[0] * 28, _gc[1] + _p[1] * 28), 15))),
               'details': ([(_END[0] - _p[0] * 11, _END[1] - _p[1] * 11), (_END[0] + _d[0] * 20, _END[1] + _d[1] * 20),
                            (_END[0] + _p[0] * 11, _END[1] + _p[1] * 11)],),          # 칼끝
               'pivot': (_HILT[0] + _d[0] * 18, _HILT[1] + _d[1] * 18), 'to': (X + 84, 282), 'angle': 0.0},)},
    {'id': 'ranged', 'name': '원거리 딜러', 'stat': '공격력', 'look': '활과 화살을 든 꼬마 궁수',
     'deco': (('hat', 'p', [(X - 72, 116), (X + 72, 116), (X + 30, 62), (X - 20, 46)]),),
     'deco_details': ([(X + 40, 70), (X + 86, 36), (X + 70, 64)],),                  # 모자 깃털
     'gear': ({'name': '활', 'w': _BW,
               'parts': (('bow', 'p', _arc(_BOW, 214, 56, 120, -76, 76, 18) + _arc(_BOW, 214, 42, 110, 76, -76, 18)),),
               'details': ([(_BOW + 14, 98), (_BOW + 14, 330)],),                        # 활시위
               'pivot': (_BOW + 49, 214), 'to': (X + 104, 258), 'angle': 0.0},
              # 화살은 옆으로 눕혀(시계 방향 90도) 활시위에 메긴다
              {'name': '화살', 'w': _AW,
               'parts': (('arrow', 'p', _bar((_A, 318), (_A, 128), 8)),
                         ('arrow_tip', 'p', [(_A - 11, 132), (_A, 104), (_A + 11, 132)])),
               'details': ([(_A - 9, 314), (_A, 302), (_A + 9, 314)],),                  # 화살 깃
               'pivot': (_A, 217), 'to': (X + 174, 258), 'angle': -math.pi / 2})},
    {'id': 'support', 'name': '서포터', 'stat': '버프량', 'look': '별 지팡이를 든 꼬마 마법사',
     'deco': (('hat_brim', 'e', X, 86, 92, 15),
              ('hat', 'p', [(X - 54, 86), (X + 54, 86), (X + 30, 46), (X + 4, 16), (X - 20, 40)])),
     'deco_details': (_star(X + 6, 58, 11, 5) + [_star(X + 6, 58, 11, 5)[0]],),      # 모자 별
     'cheeks': True,
     'gear': ({'name': '지팡이', 'w': _TW,
               'parts': (('staff', 'p', _bar((_T - 7, 352), (_T + 7, 142), 13)),
                         ('star', 'p', _star(_T + 9, 110, 32, 14))),
               'details': (),
               'pivot': (_T, 262), 'to': (X + 100, 270), 'angle': 0.0},)},
)
IDS = tuple(r['id'] for r in ROLES)
FRAMES = ROLES   # 역할 목록 (이름·능력치 설명용)


# ---------------------------------------------------------------- 체형 맞추기
def paper_size(body='medium'):
    """사람 종이 (w, h)."""
    sx, sy = PAPER_SCALE[body]
    return round(PERSON_W * sx), round(PAPER_H * sy)


def gear_size(w, body='medium'):
    """무기 종이 (w, h): 폭은 무기 크기만큼, 높이는 사람 종이와 같게."""
    return round(w * GEAR_SCALE[body]), paper_size(body)[1]


def _scaler(cx0, cx1, foot1, sx, sy):
    """보통 체형 좌표(가운데 cx0, 발 FOOT) → 새 종이 좌표(가운데 cx1, 발 foot1)."""
    return lambda p: (cx1 + (p[0] - cx0) * sx, foot1 + (p[1] - FOOT) * sy)


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
    """역할 + 체형 틀 (위 설명 참고)."""
    body = body if body in BODIES else 'medium'
    key = (frame_id, body)
    if key in _built:
        return _built[key]
    r = role(frame_id)
    sx, sy = BODY_SCALE[body]
    pw, ph = paper_size(body)
    foot = ph - FOOT_MARGIN
    f = _scaler(X, pw / 2, foot, sx, sy)
    parts = [_scale_part(p, f, sx, sy) for p in _BODY + (_HEAD,) + r['deco']]
    details = [_map_detail(d, f, min(sx, sy))
               for d in _face(X, 146, r.get('cheeks', False)) + tuple(r['deco_details']) + (_BELT,)]
    gs = GEAR_SCALE[body]
    gear = []
    for g in r['gear']:
        gw, gh = gear_size(g['w'], body)
        gf = _scaler(g['w'] / 2, gw / 2, foot, gs, gs)
        gear.append({'name': g['name'], 'size': (gw, gh),
                     'parts': tuple(_scale_part(p, gf, gs, gs) for p in g['parts']),
                     'details': tuple(_map_detail(d, gf, gs) for d in g['details']),
                     'pivot': gf(g['pivot']), 'to': f(g['to']), 'angle': g['angle']})
    _built[key] = {'id': frame_id, 'name': r['name'], 'stat': r['stat'], 'look': r['look'], 'body': body,
                   'size': (pw, ph), 'parts': tuple(parts), 'details': tuple(details), 'gear': tuple(gear)}
    return _built[key]


def part_names(frame_id, body='medium'):
    """사람 종이 부위 이름들."""
    return [p[0] for p in get(frame_id, body)['parts']]


def gear_groups(frame_id, body='medium'):
    """무기 묶음(종이)들. 묶음마다 따로 떼어 움직인다 (활과 화살처럼)."""
    return list(get(frame_id, body)['gear'])


def outline(part, n=72):
    """부위 윤곽 점들 (닫힘, 종이 좌표)."""
    if part[1] == 'e':
        _, _, cx, cy, rx, ry = part
        return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
                for i in range(n + 1)]
    pts = list(part[2])
    return pts + [pts[0]]


def mask(parts, size):
    """(h, w) uint8: 0 = 밖, i = parts[i - 1]."""
    img = Image.new('L', size, 0)
    d = ImageDraw.Draw(img)
    for i, part in enumerate(parts, 1):
        d.polygon(outline(part), fill=i)
    return np.asarray(img)


def part_mask(frame_id, body='medium'):
    """사람 종이 (h, w) uint8: 0 = 틀 밖, i = part_names()[i - 1]."""
    f = get(frame_id, body)
    return mask(f['parts'], f['size'])


def gear_mask(frame_id, group, body='medium'):
    g = get(frame_id, body)['gear'][group]
    return mask(g['parts'], g['size'])


def fit(rgba, w, h, anchor='bottom'):
    """그림 배열을 w x h 로. 크기가 다르면 가로는 가운데, 세로는 아래(발)를 맞춰 자르거나 빈 칸을 붙인다."""
    sh, sw = rgba.shape[:2]
    out = np.zeros((h, w, 4), dtype=np.uint8)
    ox = (w - sw) // 2
    oy = (h - sh) if anchor == 'bottom' else (h - sh) // 2
    sx, sy, dx, dy = max(0, -ox), max(0, -oy), max(0, ox), max(0, oy)
    cw, ch = min(sw - sx, w - dx), min(sh - sy, h - dy)
    out[dy:dy + ch, dx:dx + cw] = rgba[sy:sy + ch, sx:sx + cw]
    return out


def held(frame_id, group, p, body='medium'):
    """무기 종이 점 p 를, 그 무기를 손에 쥐었을 때의 사람 종이 위 자리로 (pivot → to, angle 만큼 돌림).
    angle 은 화면에서 반시계가 + (종이 좌표는 y 가 아래로 커서 식을 그에 맞췄다)."""
    g = get(frame_id, body)['gear'][group]
    dx, dy = p[0] - g['pivot'][0], p[1] - g['pivot'][1]
    c, s = math.cos(g['angle']), math.sin(g['angle'])
    return g['to'][0] + dx * c + dy * s, g['to'][1] - dx * s + dy * c


LIMBS = ('leg_l', 'leg_r', 'arm_l', 'arm_r')   # 걸을 때 따로 흔드는 부위


def limb_pivots(frame_id, body='medium'):
    """팔다리가 도는 축: 다리는 엉덩이(타원 위쪽), 팔은 어깨 (사람 종이 좌표)."""
    out = {}
    for name, kind, *rest in get(frame_id, body)['parts']:
        if name in LIMBS and kind == 'e':
            cx, cy, rx, ry = rest
            out[name] = (cx, cy - ry * (0.75 if name.startswith('leg') else 0.72))
    return out
