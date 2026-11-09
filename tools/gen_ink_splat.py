"""클릭하면 튀는 잉크 자국 (image/common/ink_splat_<색>_<0|1>.png).

처음 버전의 수채 잉크 방울처럼, 종이에 잉크가 톡 떨어진 느낌:
- 가운데는 부드럽게 번지고, 마르며 가장자리에 진한 물 자국이 진다 (wash 의 edge)
- 둘레로 크고 작은 방울이 제각각 튀고(대부분 몸통 가까이), 몸통에 튀다 만 작은 혹이 붙는다
- 색은 원소 색(빨·초·파 + 노랑·청록·자홍). 색마다 모양 두 가지

실행:  python tools/gen_ink_splat.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'image', 'common')
SIZE = 160
COLORS = {
    'red': (214, 72, 70), 'green': (78, 164, 88), 'blue': (62, 118, 210),
    'yellow': (236, 186, 52), 'cyan': (56, 178, 196), 'magenta': (200, 72, 168),
}
WHITE = (255, 255, 255)


def splat(color, seed):
    sh = Sheet(SIZE, SIZE, seed=seed)
    rng = sh.rng
    c = SIZE / 2
    light = tuple(int(v * 0.6 + 255 * 0.4) for v in color)
    # 번진 바탕 → 진한 몸통 (가장자리 물 자국) → 가운데 맑게 고인 곳
    sh.wash(c, c, 38, 35, light, alpha=150, layers=3, edge=0.8, blur=3.0, wobble=0.26)
    for _ in range(3):  # 몸통 둘레 혹 (잉크가 퍼지다 만 자리)
        a = rng.uniform(0, 2 * math.pi)
        sh.wash(c + math.cos(a) * 21, c + math.sin(a) * 19, rng.uniform(10, 15), rng.uniform(9, 13), color,
                alpha=220, layers=3, edge=1.8, blur=1.2, wobble=0.3)
    sh.wash(c, c, 30, 27, color, alpha=240, layers=4, edge=2.2, blur=0.9, wobble=0.24)
    sh.wash(c - 4, c - 4, 11, 9, light, alpha=120, layers=2, edge=0.4, blur=2.5)
    # 튄 방울: 몸통 가까이 많이·멀리 조금, 크기와 거리를 제각각 (줄지어 뻗지 않게)
    for _ in range(rng.randint(10, 14)):
        a = rng.uniform(0, 2 * math.pi)
        d = 34 + rng.random() ** 1.8 * 30          # 대부분 몸통 가까이
        r = rng.uniform(1.4, 4.6) * (1.25 - (d - 34) / 50)
        sh.wash(c + math.cos(a) * d, c + math.sin(a) * d, r * rng.uniform(0.9, 1.2), r, color, alpha=240, layers=2,
                edge=1.2, blur=0.5, wobble=0.3)
    # 몸통에 붙은 작은 혹 몇 개 (튀다 만 잉크)
    for _ in range(rng.randint(2, 4)):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(3.5, 6)
        sh.wash(c + math.cos(a) * (29 + r * 0.6), c + math.sin(a) * (26 + r * 0.6), r, r * 0.9, color, alpha=235,
                layers=2, edge=1.4, blur=0.6, wobble=0.25)
    return sh.result()


def main():
    for i, (name, col) in enumerate(COLORS.items()):
        for v in range(2):
            path = os.path.join(OUT, f'ink_splat_{name}_{v}.png')
            splat(col, 700 + i * 10 + v).save(path)
            print('saved', os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
