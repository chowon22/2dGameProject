"""그린 유닛 그림 다루기 (pico2d 와 무관한 순수 로직, PIL·numpy).

유닛 그림은 두 장: 사람 종이(unit_<id>.png) + 무기 종이(unit_<id>_gear.png).
- load(slot, unit): (사람, 무기) RGBA 배열 — 무기 그림이 없는 예전 유닛은 빈 무기
- pieces(unit, person, gear): 무기를 묶음(활·화살 …)으로 나누고, 손에 쥐었을 때의 가운데·각도까지
- compose(unit, person, gear): 무기를 손에 쥔 한 장짜리 그림 (카드 썸네일·필드 미리보기용)
"""
import math

import numpy as np
from PIL import Image

import frames
import save_data


def frame_of(unit):
    fid = unit.get('frame')
    return (fid if fid in frames.IDS else None), unit.get('body', 'medium')


def load(slot, unit, folder=None):
    def read(path, w):
        try:
            return frames.fit(np.asarray(Image.open(path).convert('RGBA')), w)
        except OSError:
            return np.zeros((frames.PAPER_H, w, 4), np.uint8)
    return (read(save_data.unit_path(slot, unit['id'], folder), frames.PERSON_W),
            read(save_data.gear_path(slot, unit['id'], folder), frames.GEAR_W))


def bbox(rgba):
    ys, xs = np.nonzero(rgba[..., 3])
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def pieces(unit, gear):
    """무기 묶음마다 {'img': 잘라 낸 RGBA, 'center': 손에 쥐었을 때 가운데(사람 종이 좌표), 'to': 쥔 점, 'angle'}.
    빈 묶음은 뺀다."""
    fid, body = frame_of(unit)
    if fid is None:
        return []
    out = []
    for i, piece in enumerate(frames.split_gear(gear, fid)):
        b = bbox(piece)
        if not b:
            continue
        g = frames.get(fid, body)['gear'][i]
        c = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        out.append({'img': piece[b[1]:b[3], b[0]:b[2]], 'center': frames.held(fid, i, c, body),
                    'to': g['to'], 'angle': g['angle']})
    return out


def compose(unit, person, gear):
    """무기를 손에 쥔 한 장 (RGBA 배열, 그린 부분만 잘라서). 아무것도 없으면 None."""
    pad = 220
    canvas = Image.new('RGBA', (frames.PERSON_W + pad * 2, frames.PAPER_H + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(Image.fromarray(person, 'RGBA'), (pad, pad))
    for p in pieces(unit, gear):
        img = Image.fromarray(np.ascontiguousarray(p['img']), 'RGBA')
        if p['angle']:
            img = img.rotate(math.degrees(p['angle']), resample=Image.BICUBIC, expand=True)
        x = round(p['center'][0] + pad - img.width / 2)
        y = round(p['center'][1] + pad - img.height / 2)
        canvas.alpha_composite(img, (max(0, x), max(0, y)))
    arr = np.asarray(canvas)
    b = bbox(arr)
    return arr[b[1]:b[3], b[0]:b[2]].copy() if b else None
