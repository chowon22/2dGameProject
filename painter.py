"""그리는 종이 (PRD 9.1 #2·#5·#6). pico2d 와 무관한 순수 로직이라 따로 테스트할 수 있다 (tests/test_painter.py).

종이는 픽셀마다 '어떤 잉크가 칠해졌는지'만 기억한다 (0 = 빈 칸, 1~4 = COLORS 순서).
그래서 색별 픽셀 수(= 능력치·원소의 재료)가 언제나 정확하고, 덧칠하면 아래 색은 그만큼 줄어든다.

- begin / drag / end: 마우스를 누르고 끌고 떼면, 지나간 자리에 동그라미 붓을 촘촘히 찍는다 (빠르게 움직여도 이어진다)
- limit: 색마다 쓸 수 있는 잉크 양. 넘치게 칠하려는 붓 도장은 찍히지 않는다 (#6 잉크 상한)
- counts / ink_used: 색별 픽셀 수, 그만큼 드는 잉크
- save_png / load_png: PNG 로 저장·불러오기 (#3)
"""
import math

import numpy as np
from PIL import Image

COLORS = ('black', 'red', 'green', 'blue')
ERASER = 'eraser'
# 칠한 색 (수채화 느낌 팔레트, PRD 8.1). 저장한 PNG 를 다시 읽을 때 가장 가까운 색으로 되돌린다.
RGB = {'black': (44, 38, 56), 'red': (222, 84, 96), 'green': (70, 170, 108), 'blue': (72, 124, 214)}
PIXELS_PER_INK = 25   # 잉크 1 로 칠할 수 있는 픽셀 수 (수치는 미정 사항, 나중에 조정)
BRUSH_R = 3.0         # 붓 반지름 (선 굵기 6px 남짓, PRD 8.1 선 굵기 3~5px 와 맞춤)
ERASER_R = 9.0

_PALETTE = np.array([(0, 0, 0, 0)] + [RGB[c] + (255,) for c in COLORS], dtype=np.uint8)


def label_of(tool):
    return 0 if tool == ERASER else COLORS.index(tool) + 1


def ink_for(pixels):
    """픽셀 수 → 드는 잉크 (조금이라도 칠했으면 1 부터)."""
    return math.ceil(pixels / PIXELS_PER_INK)


class Paper:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.labels = np.zeros((h, w), dtype=np.uint8)
        self.counts = np.zeros(len(COLORS) + 1, dtype=np.int64)
        self.dirty = None       # 다시 그려야 할 영역 (x0, y0, x1, y1). 화면 쪽이 가져가면 None 으로
        self.last = None        # 끌고 있는 붓의 마지막 자리
        self.blocked = False    # 이번 붓질에서 잉크가 모자라 못 칠한 적이 있는가

    # ------------------------------------------------------------ 잉크
    def count(self, color):
        return int(self.counts[label_of(color)])

    def counts_dict(self):
        return {c: self.count(c) for c in COLORS}

    def ink_used(self):
        return {c: ink_for(self.count(c)) for c in COLORS}

    def is_empty(self):
        return int(self.counts[1:].sum()) == 0

    # ------------------------------------------------------------ 붓질
    def begin(self, x, y, tool, limit=None):
        self.last = None
        self.blocked = False
        self.drag(x, y, tool, limit)

    def drag(self, x, y, tool, limit=None):
        """(x, y) 까지 붓을 끈다. 좌표는 종이 왼쪽 위가 (0, 0)."""
        r = ERASER_R if tool == ERASER else BRUSH_R
        if self.last is None:
            points = [(x, y)]
        else:
            lx, ly = self.last
            n = max(1, int(math.hypot(x - lx, y - ly) / (r * 0.5)))
            points = [(lx + (x - lx) * i / n, ly + (y - ly) * i / n) for i in range(1, n + 1)]
        for px, py in points:
            if not self.stamp(px, py, tool, limit, r):
                self.blocked = True
        self.last = (x, y)

    def end(self):
        self.last = None

    def stamp(self, x, y, tool, limit=None, r=None):
        """동그라미 붓 도장 하나. 잉크가 모자라면 찍지 않고 False."""
        r = r or (ERASER_R if tool == ERASER else BRUSH_R)
        x0, y0 = max(0, int(math.floor(x - r))), max(0, int(math.floor(y - r)))
        x1, y1 = min(self.w, int(math.ceil(x + r)) + 1), min(self.h, int(math.ceil(y + r)) + 1)
        if x0 >= x1 or y0 >= y1:
            return True
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mask = (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= r * r
        region = self.labels[y0:y1, x0:x1]
        new = label_of(tool)
        changed = mask & (region != new)
        if not changed.any():
            return True
        old = np.bincount(region[changed], minlength=len(self.counts))
        added = int(changed.sum())
        if new and limit is not None:
            color = COLORS[new - 1]
            if ink_for(self.counts[new] + added) > limit.get(color, 0):
                return False
        self.counts -= old
        self.counts[new] += added
        region[changed] = new
        self._mark(x0, y0, x1, y1)
        return True

    def clear(self):
        self.labels[:] = 0
        self.counts[:] = 0
        self._mark(0, 0, self.w, self.h)

    def _mark(self, x0, y0, x1, y1):
        if self.dirty:
            a, b, c, d = self.dirty
            x0, y0, x1, y1 = min(a, x0), min(b, y0), max(c, x1), max(d, y1)
        self.dirty = (x0, y0, x1, y1)

    # ------------------------------------------------------------ 이미지
    def rgba(self, rect=None):
        """(h, w, 4) uint8 RGBA. rect = (x0, y0, x1, y1) 면 그 부분만."""
        x0, y0, x1, y1 = rect or (0, 0, self.w, self.h)
        return _PALETTE[self.labels[y0:y1, x0:x1]]

    def save_png(self, path):
        Image.fromarray(self.rgba(), 'RGBA').save(path)

    def load_png(self, path):
        """저장한 그림을 종이에 올린다. 크기가 다르면 가운데 맞춤으로 잘라 넣는다."""
        img = np.asarray(Image.open(path).convert('RGBA'))
        self.load_rgba(img)

    def load_rgba(self, img):
        h, w = img.shape[:2]
        labels = np.zeros((self.h, self.w), dtype=np.uint8)
        # 가장 가까운 팔레트 색으로 (투명한 곳은 빈 칸)
        rgb = img[..., :3].astype(np.int32)
        dist = np.stack([((rgb - np.array(RGB[c])) ** 2).sum(-1) for c in COLORS])
        lab = (dist.argmin(0) + 1).astype(np.uint8)
        lab[img[..., 3] < 128] = 0
        ox, oy = (self.w - w) // 2, (self.h - h) // 2
        sx0, sy0 = max(0, -ox), max(0, -oy)
        dx0, dy0 = max(0, ox), max(0, oy)
        cw, ch = min(w - sx0, self.w - dx0), min(h - sy0, self.h - dy0)
        labels[dy0:dy0 + ch, dx0:dx0 + cw] = lab[sy0:sy0 + ch, sx0:sx0 + cw]
        self.labels = labels
        self.counts = np.bincount(labels.ravel(), minlength=len(COLORS) + 1).astype(np.int64)
        self._mark(0, 0, self.w, self.h)
