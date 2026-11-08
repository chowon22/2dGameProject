"""손그림 펜 선 + 수채화 느낌을 PIL로 그리는 도구 모음.

PRD 8.1 아트 방향:
- 살짝 삐뚤빼뚤한 검정 펜 선, 선 굵기 3~5px
- 수채화 빨강·초록·파랑 고정 팔레트
- 흑백 세상, 원소 색은 진하게 / 배경은 연하게

좌표는 모두 PIL 기준(왼쪽 위가 원점, y 아래로 증가)이다.
내부적으로 ss배 크게 그린 뒤 줄여서 선을 부드럽게(안티에일리어싱) 만든다.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- 팔레트
INK = (34, 31, 36)
PAPER = (247, 244, 237)
GRAY = (120, 118, 124)
LIGHT_GRAY = (170, 168, 172)
# 타이틀 화면용 몽환적인 파스텔 팔레트
PASTEL = {
    'pink': (247, 178, 200),
    'peach': (252, 206, 172),
    'lemon': (250, 232, 158),
    'mint': (168, 224, 198),
    'sky': (166, 204, 242),
    'lavender': (198, 180, 238),
}
PLUM = (86, 68, 106)  # 파스텔 화면에 어울리는 보랏빛 펜 선

WATERCOLOR = {
    'red': (219, 77, 66),
    'green': (92, 170, 84),
    'blue': (66, 124, 210),
}

FONT_DIR = 'C:/Windows/Fonts/'


def font(name, size):
    return ImageFont.truetype(FONT_DIR + name, size)


# ---------------------------------------------------------------- 경로 도우미
def bezier(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
        pts.append((x, y))
    return pts


def ellipse_points(cx, cy, rx, ry, n=48, start=0.0, sweep=2 * math.pi):
    return [(cx + math.cos(start + sweep * i / n) * rx,
             cy + math.sin(start + sweep * i / n) * ry) for i in range(n + 1)]


def _resample(points, step):
    out = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(d / step))
        for i in range(n):
            t = i / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    out.append(points[-1])
    return out


def _wobble(points, amp, rng, step):
    """선 방향의 수직으로 천천히 흔들어 손떨림 느낌을 낸다."""
    pts = _resample(points, step)
    off = 0.0
    vel = 0.0
    res = []
    for i, (x, y) in enumerate(pts):
        j0, j1 = max(0, i - 1), min(len(pts) - 1, i + 1)
        dx, dy = pts[j1][0] - pts[j0][0], pts[j1][1] - pts[j0][1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        vel = vel * 0.9 + rng.uniform(-1, 1) * 0.06 * amp
        off = max(-amp, min(amp, off * 0.97 + vel))
        res.append((x + nx * off, y + ny * off))
    return res


# ---------------------------------------------------------------- 시트
class Sheet:
    """투명 RGBA 도화지. 펜 선과 수채화 번짐을 얹는다."""

    def __init__(self, w, h, seed=0, ss=2):
        self.w, self.h, self.ss = w, h, ss
        self.img = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.line = INK  # 기본 펜 색


    # ---- 펜 선
    def stroke(self, points, width=4.0, color=None, alpha=255, amp=1.3, taper=True):
        """붓 도장을 촘촘히 찍어 펜 선을 그린다 (PRD 9.1 붓 그리기와 같은 방식)."""
        s = self.ss
        color = self.line if color is None else color
        pts = _wobble([(x * s, y * s) for x, y in points], amp * s, self.rng, 1.5 * s)
        n = len(pts)
        fill = tuple(color) + (alpha,)
        jitter = 1.0
        for i, (x, y) in enumerate(pts):
            t = i / max(1, n - 1)
            k = min(1.0, 0.45 + min(t, 1 - t) * 7) if taper else 1.0
            jitter = jitter * 0.8 + self.rng.uniform(0.9, 1.08) * 0.2
            r = width * s / 2 * k * jitter
            self.draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def ellipse(self, cx, cy, rx, ry, width=4.0, color=None, alpha=255, amp=1.3):
        """시작점이 살짝 겹치는 손그림 타원."""
        start = self.rng.uniform(0, 2 * math.pi)
        sweep = 2 * math.pi * self.rng.uniform(1.03, 1.08)
        self.stroke(ellipse_points(cx, cy, rx, ry, 64, start, sweep), width, color, alpha, amp)

    def hatch(self, x0, y0, x1, y1, gap=9, angle=-0.9, width=2.0, color=GRAY, alpha=150, clip=None):
        """사선 해칭. clip(x, y) -> bool 로 범위를 제한할 수 있다."""
        dx, dy = math.cos(angle), math.sin(angle)
        span = (x1 - x0) + (y1 - y0)
        c = x0 - span
        while c < x1 + span:
            seg = []
            for i in range(0, int(span * 2), 3):
                x, y = c + dx * i, y1 + dy * i
                inside = x0 <= x <= x1 and y0 <= y <= y1 and (clip is None or clip(x, y))
                if inside:
                    seg.append((x, y))
                elif len(seg) > 2:
                    self.stroke(seg, width, color, alpha, amp=0.6)
                    seg = []
                else:
                    seg = []
            if len(seg) > 2:
                self.stroke(seg, width, color, alpha, amp=0.6)
            c += gap * self.rng.uniform(0.85, 1.15)

    # ---- 수채화
    def wash(self, cx, cy, rx, ry, color, alpha=120, layers=4, edge=1.4, blur=3.0, wobble=0.14):
        """여러 겹의 흐린 얼룩을 겹치고 가장자리를 진하게 해 수채화 번짐을 만든다."""
        self.img.alpha_composite(self._wash_layer(cx, cy, rx, ry, color, alpha, layers, edge, blur, wobble))

    def _wash_layer(self, cx, cy, rx, ry, color, alpha, layers, edge, blur, wobble):
        s = self.ss
        layer = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        pad = int(max(rx, ry) * 0.4 + blur * 4 + 12)
        bw, bh = int((rx + pad) * 2 * s), int((ry + pad) * 2 * s)
        mask = np.zeros((bh, bw), np.float32)
        for _ in range(layers):
            m = Image.new('L', (bw, bh), 0)
            d = ImageDraw.Draw(m)
            ph = [self.rng.uniform(0, 2 * math.pi) for _ in range(3)]
            sc = self.rng.uniform(0.8, 1.0)
            pts = []
            for i in range(36):
                a = 2 * math.pi * i / 36
                rr = sc * (1 + wobble * math.sin(3 * a + ph[0]) + wobble * 0.6 * math.sin(5 * a + ph[1])
                           + self.rng.uniform(-0.4, 0.4) * wobble)
                pts.append((bw / 2 + math.cos(a) * rx * s * rr, bh / 2 + math.sin(a) * ry * s * rr))
            d.polygon(pts, fill=255)
            m = m.filter(ImageFilter.GaussianBlur(blur * s))
            mask += np.asarray(m, np.float32) / 255.0 / layers
        soft = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5 * s))
        soft = np.asarray(soft, np.float32) / 255.0
        a = mask * 0.7 + np.clip(mask - soft, 0, 1) * edge
        a *= 0.82 + 0.18 * self.np_rng.random((bh, bw), dtype=np.float32)
        a = np.clip(a, 0, 1) * alpha
        arr = np.zeros((bh, bw, 4), np.uint8)
        arr[..., :3] = color
        arr[..., 3] = a.astype(np.uint8)
        _paste(layer, Image.fromarray(arr, 'RGBA'), int((cx - rx - pad) * s), int((cy - ry - pad) * s))
        return layer

    def masked(self, other, mask):
        """다른 시트를 mask(L, 원래 크기) 안쪽만 얹는다."""
        m = mask.resize(self.img.size, Image.BILINEAR)
        r, g, b, a = other.img.split()
        a = Image.fromarray((np.asarray(a, np.float32) * np.asarray(m, np.float32) / 255).astype(np.uint8))
        self.img.alpha_composite(Image.merge('RGBA', (r, g, b, a)))

    def splatter(self, cx, cy, spread, color, count=8, size=(1.5, 5), alpha=230):
        """주변에 튄 잉크 방울."""
        for _ in range(count):
            a = self.rng.uniform(0, 2 * math.pi)
            d = spread * self.rng.uniform(0.6, 1.25)
            r = self.rng.uniform(*size)
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            self.wash(x, y, r, r, color, alpha, layers=2, edge=0.6, blur=0.6, wobble=0.25)

    # ---- 글자
    def text_mask(self, text, fnt, x, y, anchor='la'):
        s = self.ss
        big = ImageFont.truetype(fnt.path, int(fnt.size * s))
        m = Image.new('L', self.img.size, 0)
        ImageDraw.Draw(m).text((x * s, y * s), text, font=big, fill=255, anchor=anchor)
        return m

    def ink_text(self, text, fnt, x, y, color=INK, alpha=255, anchor='la'):
        m = self.text_mask(text, fnt, x, y, anchor)
        m = Image.fromarray((np.asarray(m, np.float32) * alpha / 255).astype(np.uint8))
        layer = Image.new('RGBA', self.img.size, tuple(color) + (0,))
        layer.putalpha(m)
        self.img.alpha_composite(layer)

    # ---- 저장
    def result(self, crop=False, margin=6):
        img = self.img.resize((self.w, self.h), Image.LANCZOS)
        if crop:
            box = img.getbbox()
            if box:
                l, t, r, b = box
                img = img.crop((max(0, l - margin), max(0, t - margin),
                                min(self.w, r + margin), min(self.h, b + margin)))
        return img


def _paste(dst, src, x, y):
    """음수 좌표도 받아 주는 alpha_composite."""
    sx, sy = max(0, -x), max(0, -y)
    dx, dy = max(0, x), max(0, y)
    w = min(src.width - sx, dst.width - dx)
    h = min(src.height - sy, dst.height - dy)
    if w > 0 and h > 0:
        dst.alpha_composite(src.crop((sx, sy, sx + w, sy + h)), dest=(dx, dy))


# ---------------------------------------------------------------- 종이
def paper(w, h, seed=0):
    """잔결과 얼룩, 가장자리 그늘이 있는 미색 도화지."""
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3), np.float32) * np.array(PAPER, np.float32)
    fine = rng.normal(0, 3.0, (h, w)).astype(np.float32)
    low = rng.normal(0, 1, (h // 48 + 2, w // 48 + 2)).astype(np.float32)
    low_img = Image.fromarray(((low * 18) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    low = (np.asarray(low_img, np.float32) - 128) / 18 * 2.5
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) ** 1.2 * 60
    shade = (fine + low - vig)[..., None]
    arr = np.clip(base + shade * np.array([1.0, 1.0, 1.05]), 0, 255).astype(np.uint8)
    return Image.fromarray(arr, 'RGB').convert('RGBA')
