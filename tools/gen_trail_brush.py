"""커서 빛 선용 둥근 붓 도장 (image/common/trail_brush_*.png).

BrushTrail 은 이 도장을 곡선을 따라 촘촘히 찍어 선을 만든다. 예전 trail_cap 은 가운데 흰 점이 딱딱해서
찍은 자리마다 점이 보였다. 여기서는 흰 심도 색 번짐도 가우스로 부드럽게 퍼져 겹치면 끊김 없는 선이 된다.
색 단계는 gen_title_images 의 trail_colors (TRAIL_STEPS 개) 와 같다.

실행:  python tools/gen_trail_brush.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from gen_title_images import trail_colors  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'image', 'common')
SIZE = 32


def brush(color):
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(np.float32)
    r2 = (xx - (SIZE - 1) / 2) ** 2 + (yy - (SIZE - 1) / 2) ** 2
    glow = np.exp(-r2 / (2 * 5.0 ** 2))          # 색 번짐
    core = np.exp(-r2 / (2 * 1.9 ** 2))          # 흰 심 (부드럽게)
    a = np.clip(glow * 0.85 + core * 0.4, 0, 1)
    white = np.clip(core * 1.15, 0, 1)[..., None]
    rgb = np.array(color, np.float32) * (1 - white) + 255 * white
    arr = np.dstack([rgb, a[..., None] * 255]).astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')


def main():
    for i, c in enumerate(trail_colors()):
        path = os.path.join(OUT, f'trail_brush_{i}.png')
        brush(c).save(path)
        print('saved', os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
