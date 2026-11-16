"""그린 유닛 그림 다루기 (pico2d 와 무관한 순수 로직, PIL·numpy).

유닛 그림은 사람 종이(unit_<id>.png) 한 장 + 무기 종이마다 한 장(unit_<id>_gear<n>.png, 원딜은 활·화살 두 장).
- load(slot, unit): (사람, [무기 …]) RGBA 배열 — 그 틀·체형의 종이 크기로 맞춘다. 없는 그림은 빈 종이
- pieces(unit, gears): 무기마다 손에 쥐었을 때의 가운데·쥔 점·각도
- compose(unit, person, gears): 무기를 손에 쥔 한 장짜리 그림 (카드 썸네일·필드 미리보기용)
"""
import math

import numpy as np
from PIL import Image

import frames
import save_data


def frame_of(unit):
    fid = unit.get('frame')
    body = unit.get('body', 'medium')
    return (fid if fid in frames.IDS else None), (body if body in frames.BODIES else 'medium')


def _read(path, size):
    w, h = size
    try:
        return frames.fit(np.asarray(Image.open(path).convert('RGBA')), w, h)
    except OSError:
        return np.zeros((h, w, 4), np.uint8)


def load(slot, unit, folder=None):
    fid, body = frame_of(unit)
    size = frames.get(fid, body)['size'] if fid else frames.paper_size(body)
    person = _read(save_data.unit_path(slot, unit['id'], folder), size)
    gears = [_read(save_data.gear_path(slot, unit['id'], folder, i), g['size'])
             for i, g in enumerate(frames.get(fid, body)['gear'])] if fid else []
    return person, gears


def bbox(rgba):
    ys, xs = np.nonzero(rgba[..., 3])
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def pieces(unit, gears):
    """무기마다 {'img': 잘라 낸 RGBA, 'center': 손에 쥐었을 때 가운데(사람 종이 좌표), 'to': 쥔 점, 'angle'}.
    빈 무기 종이는 뺀다."""
    fid, body = frame_of(unit)
    if fid is None:
        return []
    out = []
    for i, (g, rgba) in enumerate(zip(frames.get(fid, body)['gear'], gears)):
        b = bbox(rgba)
        if not b:
            continue
        c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        out.append({'img': rgba[b[1]:b[3], b[0]:b[2]], 'center': frames.held(fid, i, c, body),
                    'to': g['to'], 'angle': g['angle']})
    return out


def compose(unit, person, gears):
    """무기를 손에 쥔 한 장 (RGBA 배열, 그린 부분만 잘라서). 아무것도 없으면 None."""
    pad = 260
    h, w = person.shape[:2]
    canvas = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(Image.fromarray(person, 'RGBA'), (pad, pad))
    for p in pieces(unit, gears):
        img = Image.fromarray(np.ascontiguousarray(p['img']), 'RGBA')
        if p['angle']:
            img = img.rotate(math.degrees(p['angle']), resample=Image.BICUBIC, expand=True)
        x = round(p['center'][0] + pad - img.width / 2)
        y = round(p['center'][1] + pad - img.height / 2)
        canvas.alpha_composite(img, (max(0, x), max(0, y)))
    arr = np.asarray(canvas)
    b = bbox(arr)
    return arr[b[1]:b[3], b[0]:b[2]].copy() if b else None
