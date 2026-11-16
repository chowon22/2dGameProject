"""그린 유닛을 '사람 + 손에 쥔 무기 묶음들' 로 움직이게 그린다 (준비 화면에서 걷는 유닛 등).

사람 종이 그림은 몸 그대로, 무기 종이 그림은 묶음(방패·칼·활·화살·지팡이)마다 잘라
틀(frames)의 쥐는 점(pivot)이 손 자리(to)에 오게 옮기고 angle 만큼 돌려 쥔다 (unit_art.pieces).
움직일 때는 쥔 점을 축으로 흔든다. open_canvas() 뒤에만 쓸 수 있다.
"""
import math
import os

import numpy as np
from PIL import Image as PILImage

import save_data
import unit_art
from live_image import LiveImage

_cache = {}


class Rig:
    def __init__(self, unit, person, gear, scale):
        self.pieces = unit_art.pieces(unit, gear)
        pb = unit_art.bbox(person)
        boxes = [pb] if pb else []
        for p in self.pieces:            # 쥔 무기가 차지하는 자리 (돌린 뒤 네 모서리)
            h, w = p['img'].shape[:2]
            r = math.hypot(w, h) / 2
            cx, cy = p['center']
            boxes.append((cx - r, cy - r, cx + r, cy + r) if p['angle'] else (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        if not boxes:
            raise ValueError('empty drawing')
        ux0, uy0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        ux1, uy1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        # 발(사람 그림 맨 아래 가운데)을 기준으로 맞춘다
        self.k = scale
        self.fx = (pb[0] + pb[2]) / 2 if pb else (ux0 + ux1) / 2
        self.fy = pb[3] if pb else uy1
        self.w, self.h = (ux1 - ux0) * self.k, (uy1 - uy0) * self.k
        self.body = _image(person[pb[1]:pb[3], pb[0]:pb[2]], self.k) if pb else None
        self.body_c = ((pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2) if pb else None
        for p in self.pieces:
            p['tex'] = _image(p['img'], self.k)

    def to_screen(self, p, foot_x, foot_y):
        """사람 종이 좌표(위가 0) → 화면 좌표. 발이 (foot_x, foot_y)."""
        return foot_x + (p[0] - self.fx) * self.k, foot_y + (self.fy - p[1]) * self.k

    def draw(self, foot_x, foot_y, tilt=0.0, sway=0.0, alpha=1.0):
        """tilt: 몸 기울기, sway: 무기를 쥔 점을 축으로 더 흔드는 각도 (라디안, 반시계 +)."""
        if self.body:
            bx, by = self.to_screen(self.body_c, foot_x, foot_y)
            _draw(self.body, bx, by, tilt, alpha)
        for p in self.pieces:
            px, py = self.to_screen(p['to'], foot_x, foot_y)
            cx, cy = self.to_screen(p['center'], foot_x, foot_y)
            a = tilt + sway
            vx, vy = cx - px, cy - py
            gx = px + vx * math.cos(a) - vy * math.sin(a)
            gy = py + vx * math.sin(a) + vy * math.cos(a)
            _draw(p['tex'], gx, gy, p['angle'] + a, alpha)


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
