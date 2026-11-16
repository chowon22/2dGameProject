"""그린 유닛을 틀(frames)에 맞춰 마디마디 움직이게 그린다 (준비 화면에서 걷기, 전투에서 서 있기·공격).

사람 그림은 몸통 / 왼다리 / 오른다리 / 왼팔 / 오른팔로 나누고(unit_art.split_person) 다리는 엉덩이, 팔은 어깨를 축으로 돈다.
무기 종이 그림은 쥐는 점(pivot)이 손 자리(to)에 오게 옮기고(화살은 눕혀 활시위에), 오른팔에 붙어 함께 흔들린다.
open_canvas() 뒤에만 쓸 수 있다.
"""
import math
import os

import numpy as np
from PIL import Image as PILImage

import frames
import save_data
import unit_art
from live_image import LiveImage

_cache = {}
DRAW_ORDER = ('leg_l', 'leg_r', 'arm_l', 'body', 'arm_r')   # 뒤에 그린 것이 앞


def _rot(vx, vy, a):
    return vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)


class Rig:
    def __init__(self, unit, person, gears, scale):
        self.k = scale
        fid, body = unit_art.frame_of(unit)
        self.frame = fid
        parts = unit_art.split_person(unit, person)
        pivots = frames.limb_pivots(fid, body) if fid else {}
        pb = unit_art.bbox(person)
        if not pb and not any(unit_art.bbox(g) is not None for g in gears):
            raise ValueError('empty drawing')
        h, w = person.shape[:2]
        # 발(사람 그림 맨 아래 가운데, 그림이 없으면 종이 발 자리)을 기준점으로
        self.fx = (pb[0] + pb[2]) / 2 if pb else w / 2
        self.fy = pb[3] if pb else h - frames.FOOT_MARGIN
        self.limbs = []
        for name in DRAW_ORDER:
            rgba = parts.get(name)
            b = unit_art.bbox(rgba) if rgba is not None else None
            if not b:
                continue
            self.limbs.append({'name': name, 'tex': _image(rgba[b[1]:b[3], b[0]:b[2]], scale),
                               'center': ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), 'pivot': pivots.get(name)})
        self.shoulder = pivots.get('arm_r')
        self.weapons = unit_art.pieces(unit, gears)
        for p in self.weapons:
            p['tex'] = _image(p['img'], scale)
        # 대략 크기 (그림자 등)
        boxes = ([pb] if pb else []) + [
            (p['center'][0] - p['img'].shape[1] / 2, p['center'][1] - p['img'].shape[0] / 2,
             p['center'][0] + p['img'].shape[1] / 2, p['center'][1] + p['img'].shape[0] / 2) for p in self.weapons]
        self.w = (max(b[2] for b in boxes) - min(b[0] for b in boxes)) * scale
        self.h = (max(b[3] for b in boxes) - min(b[1] for b in boxes)) * scale

    def to_screen(self, p, foot_x, foot_y):
        """사람 종이 좌표(위가 0) → 화면 좌표. 발이 (foot_x, foot_y)."""
        return foot_x + (p[0] - self.fx) * self.k, foot_y + (self.fy - p[1]) * self.k

    @staticmethod
    def pose(kind, phase):
        """(마디별 각도 (라디안, 반시계 +), 마디별 들어 올림(px), 몸 들썩임(px)).
        kind: 'walk' / 'idle' / 'attack'(phase 0→1 휘두르기). 앞을 보는 꼬마라 걸을 때 다리는 번갈아 들어 올린다."""
        s = math.sin(phase)
        if kind == 'walk':
            up = max(0.0, s), max(0.0, -s)
            return ({'leg_l': 0.1 * up[0], 'leg_r': -0.1 * up[1], 'arm_l': -0.28 * s, 'arm_r': 0.28 * s,
                     'weapon': 0.1 * math.sin(phase + 0.6)},
                    {'leg_l': 9 * up[0], 'leg_r': 9 * up[1]}, abs(s) * 4)
        if kind == 'attack':   # 팔을 들었다가 앞으로 크게 휘두르기
            k = math.sin(min(1.0, max(0.0, phase)) * math.pi)
            return ({'arm_r': -1.1 * k, 'arm_l': 0.25 * k, 'weapon': -0.3 * k}, {'leg_l': 4 * k}, 2 * k)
        return {'arm_l': 0.04 * s, 'arm_r': -0.04 * s, 'weapon': 0.05 * s}, {}, 1.5 * (s + 1)   # idle: 숨쉬기

    def draw(self, foot_x, foot_y, kind='walk', phase=0.0, alpha=1.0):
        angles, lifts, bob = self.pose(kind, phase)
        foot_y += bob
        for limb in self.limbs:
            a = angles.get(limb['name'], 0.0)
            cx, cy = self.to_screen(limb['center'], foot_x, foot_y)
            cy += lifts.get(limb['name'], 0.0)
            if limb['pivot'] and a:
                px, py = self.to_screen(limb['pivot'], foot_x, foot_y)
                dx, dy = _rot(cx - px, cy - py, a)
                cx, cy = px + dx, py + dy
            _draw(limb['tex'], cx, cy, a, alpha)
        arm = angles.get('arm_r', 0.0)
        sway = angles.get('weapon', 0.0)
        sx, sy = self.to_screen(self.shoulder, foot_x, foot_y) if self.shoulder else (0, 0)
        for p in self.weapons:
            cx, cy = self.to_screen(p['center'], foot_x, foot_y)
            tx, ty = self.to_screen(p['to'], foot_x, foot_y)
            if self.shoulder and arm:   # 오른팔과 함께 어깨를 축으로
                dx, dy = _rot(cx - sx, cy - sy, arm)
                cx, cy = sx + dx, sy + dy
                dx, dy = _rot(tx - sx, ty - sy, arm)
                tx, ty = sx + dx, sy + dy
            dx, dy = _rot(cx - tx, cy - ty, sway)   # 쥔 점을 축으로 조금 더 흔들기
            _draw(p['tex'], tx + dx, ty + dy, p['angle'] + arm + sway, alpha)


def _image(rgba, k):
    img = PILImage.fromarray(np.ascontiguousarray(rgba), 'RGBA')
    w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
    img = img.resize((w, h), PILImage.LANCZOS)
    return LiveImage(w, h, np.asarray(img))


def _draw(img, x, y, rad, alpha):
    if alpha < 1:
        img.opacify(alpha)
    img.composite_draw(rad, '', round(x), round(y), img.w, img.h)
    if alpha < 1:
        img.opacify(1)


def rig(unit, scale):
    """유닛의 Rig (그림 파일이 바뀌면 새로 만든다). 그림이 없으면 None."""
    slot = save_data.current['slot']
    paths = [save_data.unit_path(slot, unit['id'])] + [save_data.gear_path(slot, unit['id'], group=i) for i in range(4)]
    stamp = tuple(_mtime(p) for p in paths)
    key = (slot, unit['id'], stamp, unit.get('frame'), unit.get('body'), scale)
    if key not in _cache:
        try:
            _cache[key] = Rig(unit, *unit_art.load(slot, unit), scale)
        except ValueError:
            _cache[key] = None
    return _cache[key]


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None
