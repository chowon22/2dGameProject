"""준비 화면 주인공(꼬마 화가) 스프라이트. 사람이 그린 부드러운 일러스트 느낌으로 그린다.

- 선: 가늘고 연한 밤색 펜 선. 굵기가 천천히 변하고 끝이 가늘다. 닫힌 모양도 두세 번에 나눠 긋는다
- 색: 채도를 뺀 부드러운 단색 칠 + 빛 반대쪽(왼쪽 아래)에 옅은 푸른 그늘
- 머리: 몽실몽실한 윤곽에 가는 머리카락 결, 바람에 날리는 몇 가닥
- 큰 머리, 헐렁한 스웨터, 짧은 다리. 검은 잉크통을 두 팔로 꼭 안고 달린다
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from sketch import Sheet, ellipse_points, _wobble

SPRITE = (160, 180)
FEET = 168              # 스프라이트 안 발바닥 y (PIL)
LINE = (142, 112, 104)  # 펜 선: 연한 밤색
WHITE = (255, 255, 255)
SKIN = (255, 238, 226)
CHEEK = (250, 176, 170)
HAIR = (222, 196, 166)        # 밀크티빛 머리
HAIR_LINE = (176, 140, 112)
BERET = (156, 172, 196)       # 먼지 낀 하늘빛 베레모
SWEATER = (250, 248, 244)     # 헐렁한 흰 스웨터
PANTS = (160, 178, 198)
SHOE = (206, 186, 172)
INK_BLACK = (58, 52, 66)
SHADE = (190, 196, 222)       # 그늘에 섞는 푸른 회색

# 프레임별 자세: (몸 들썩임, 앞다리 (허벅지, 정강이), 뒷다리, 팔 흔들림)  각도 0 = 아래, + = 앞(오른쪽)
POSES = (
    (0.0, (0.7, 0.1), (-0.5, -1.1), 0.0),
    (-4.0, (0.25, -0.7), (-0.05, 0.25), 1.0),
    (0.0, (-0.5, -1.1), (0.7, 0.1), 2.0),
)


# ---------------------------------------------------------------- 곡선·선·칠 도우미
def smooth(ctrl, closed=True, n=10):
    """조절점을 지나는 캣멀롬 곡선."""
    pts = list(ctrl)
    m = len(pts)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = pts[(i - 1) % m] if closed else pts[max(0, i - 1)]
        p1, p2 = pts[i], pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if closed else pts[min(m - 1, i + 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    if not closed:
        out.append(pts[-1])
    return out


def pen(sh, pts, width=1.3, color=LINE, alpha=235):
    """한 번 긋는 펜 선: 도장을 촘촘히 찍어 끊김이 없고, 끝이 가늘어지고 아주 살짝 떨린다."""
    ss = sh.ss
    pts = _wobble([(x * ss, y * ss) for x, y in pts], 0.3 * ss, sh.rng, 0.3 * ss)
    n = len(pts)
    fill = tuple(color) + (alpha,)
    press = 1.0
    for i, (x, y) in enumerate(pts):
        t = i / max(1, n - 1)
        k = min(1.0, 0.35 + min(t, 1 - t) * 6)        # 시작·끝이 가늘다
        press = press * 0.97 + sh.rng.uniform(0.85, 1.12) * 0.03   # 누르는 힘이 천천히 변한다
        r = width * ss / 2 * k * press
        sh.draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def outline(sh, pts, width=1.3, color=LINE, pieces=2):
    """닫힌 모양을 몇 번에 나눠 긋는다. 조각끼리 살짝 겹치거나 틈이 난다."""
    n = len(pts)
    start = sh.rng.randrange(n)
    ring = pts[start:] + pts[:start]
    cuts = sorted(sh.rng.sample(range(n // 5, n - n // 5), pieces - 1)) if pieces > 1 else []
    bounds = [0] + cuts + [n]
    for a, b in zip(bounds, bounds[1:]):
        lo = max(0, a - sh.rng.randint(-1, 3))
        hi = min(n, b + sh.rng.randint(0, 2))
        seg = ring[lo:hi]
        if len(seg) > 2:
            pen(sh, seg, width * sh.rng.uniform(0.9, 1.08), color)


def open_line(sh, pts, width=1.3, color=LINE, pieces=1):
    """열린 곡선을 몇 번에 나눠 긋는다 (끝과 처음을 잇지 않는다)."""
    n = len(pts)
    cuts = sorted(sh.rng.sample(range(n // 4, n - n // 4), pieces - 1)) if pieces > 1 else []
    bounds = [0] + cuts + [n]
    for a, b in zip(bounds, bounds[1:]):
        seg = pts[max(0, a - sh.rng.randint(0, 3)):b]
        if len(seg) > 2:
            pen(sh, seg, width * sh.rng.uniform(0.9, 1.08), color)


def paint(sh, pts, color, alpha=255, shade=0.18, light=(3.5, -3.0)):
    """부드러운 단색 칠 + 빛 반대쪽(왼쪽 아래)에 옅은 푸른 그늘."""
    ss = sh.ss
    big = sh.img.size

    def mask(dx=0.0, dy=0.0):
        m = Image.new('L', big, 0)
        ImageDraw.Draw(m).polygon([((x + dx) * ss, (y + dy) * ss) for x, y in pts], fill=255)
        return np.asarray(m.filter(ImageFilter.GaussianBlur(0.5 * ss)), np.float32) / 255

    base = mask()
    lit = mask(*light)
    band = Image.fromarray((base * (1 - lit) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6 * ss))
    shadow = np.asarray(band, np.float32) / 255 * base
    dark = tuple(int(c * (1 - shade) + s * shade) for c, s in zip(color, SHADE))
    for col, a in ((color, base * alpha), (dark, shadow * 255)):
        layer = Image.new('RGBA', big, tuple(col) + (0,))
        layer.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
        sh.img.alpha_composite(layer)


def limb(path, r0, r1, n=6):
    """path(곡선) 를 따라 굵기가 r0→r1 로 변하는 한 덩어리 팔·다리 (관절에서 끊기지 않는다)."""
    path = smooth(path, closed=False, n=8)
    m = len(path)
    left, right = [], []
    for i, (x, y) in enumerate(path):
        j0, j1 = max(0, i - 1), min(m - 1, i + 1)
        dx, dy = path[j1][0] - path[j0][0], path[j1][1] - path[j0][1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        r = r0 + (r1 - r0) * i / (m - 1)
        left.append((x + nx * r, y + ny * r))
        right.append((x - nx * r, y - ny * r))

    def cap(p, a0, r):
        return [(p[0] + math.cos(a0 - math.pi * k / n) * r, p[1] + math.sin(a0 - math.pi * k / n) * r)
                for k in range(1, n)]
    a_end = math.atan2(path[-1][1] - path[-2][1], path[-1][0] - path[-2][0])
    a_start = math.atan2(path[1][1] - path[0][1], path[1][0] - path[0][0])
    return left + cap(path[-1], a_end + math.pi / 2, r1) + right[::-1] + cap(path[0], a_start - math.pi / 2, r0)


def _joint(p, a, ln):
    return (p[0] + math.sin(a) * ln, p[1] + math.cos(a) * ln)


def fluffy(cx, cy, rx, ry, a0, a1, bumps, depth, n=120):
    """몽실몽실한 머리 윤곽: 각도 a0→a1 사이에 작은 혹들."""
    pts = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (a1 - a0) * t
        k = 1 + depth * abs(math.sin(t * bumps * math.pi)) ** 0.7
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    return pts


# ---------------------------------------------------------------- 몸 부분
def leg(sh, hip, pose, behind):
    knee = _joint(hip, pose[0], 17)
    foot = _joint(knee, pose[1], 15)
    shape = limb([hip, knee, foot], 6.4, 4.6)
    paint(sh, shape, tuple(int(c * 0.93) for c in PANTS) if behind else PANTS)
    outline(sh, shape, 1.2, pieces=2)
    toe = 1 if pose[1] > -0.6 else 0.5
    shoe = smooth([(foot[0] - 7, foot[1] - 3), (foot[0] + 2, foot[1] - 4.5), (foot[0] + 10 * toe, foot[1] - 1),
                   (foot[0] + 10 * toe, foot[1] + 3.5), (foot[0] - 1, foot[1] + 5), (foot[0] - 8, foot[1] + 2.5)], n=4)
    paint(sh, shoe, SHOE)
    outline(sh, shoe, 1.2, pieces=1)


def head(sh, hx, hy, swing):
    face = smooth([(hx - 26, hy - 4), (hx - 18, hy - 24), (hx + 2, hy - 30), (hx + 22, hy - 22), (hx + 29, hy - 2),
                   (hx + 25, hy + 18), (hx + 10, hy + 28), (hx - 10, hy + 26), (hx - 24, hy + 12)], n=8)
    # 뒷머리 (얼굴 뒤로 둥글게)
    back = fluffy(hx - 3, hy - 2, 30, 30, math.pi * 0.55, math.pi * 1.6, 6, 0.08)
    paint(sh, back + [(hx + 4, hy - 8), (hx - 6, hy + 10)], HAIR)
    paint(sh, face, SKIN)
    sh.wash(hx + 15, hy + 12, 5, 3.4, CHEEK, alpha=150, layers=2, blur=1.4)
    sh.wash(hx - 1, hy + 13, 4, 2.6, CHEEK, alpha=100, layers=2, blur=1.4)
    open_line(sh, face[len(face) * 2 // 5:], 1.3)   # 얼굴 앞·아래 윤곽만
    # 앞머리: 이마를 덮는 몽실한 앞머리, 끝이 몇 갈래로 갈라진다
    bangs = fluffy(hx, hy - 4, 31, 28, math.pi * 1.0, math.pi * 1.95, 7, 0.07)
    bangs += smooth([(hx + 28, hy - 8), (hx + 21, hy - 3), (hx + 15, hy - 10), (hx + 8, hy - 2), (hx + 1, hy - 9),
                     (hx - 6, hy - 1), (hx - 13, hy - 7), (hx - 20, hy + 4), (hx - 29, hy + 1)], False, 4)
    paint(sh, bangs, HAIR)
    open_line(sh, back, 1.3, HAIR_LINE, pieces=2)
    outline(sh, bangs, 1.3, HAIR_LINE, pieces=3)
    for k in range(9):    # 머리카락 결
        a = math.pi * (1.1 + 0.085 * k)
        x0, y0 = hx + math.cos(a) * 25, hy - 4 + math.sin(a) * 22
        pen(sh, [(x0, y0), (x0 + math.cos(a + 2.3) * 7, y0 + math.sin(a + 2.3) * 7)], 0.8, HAIR_LINE, 130)
    for k, (bx, by, ln) in enumerate(((-29, -10, 9), (-31, 2, 7), (-22, -22, 8))):   # 뒤로 날리는 가닥
        x0, y0 = hx + bx, hy + by
        pen(sh, smooth([(x0 + 3, y0), (x0 - ln * 0.6, y0 - 2 + math.sin(swing * 2 + k)), (x0 - ln, y0 + 1.5)],
                       False, 5), 1.0, HAIR_LINE)
    # 베레모: 정수리에 비스듬히
    beret = smooth([(hx - 22, hy - 22), (hx - 10, hy - 34), (hx + 8, hy - 37), (hx + 24, hy - 30), (hx + 20, hy - 23),
                    (hx - 2, hy - 21)], n=6)
    paint(sh, beret, BERET)
    outline(sh, beret, 1.3, pieces=2)
    pen(sh, [(hx + 2, hy - 37), (hx + 3, hy - 42)], 1.4)
    # 얼굴: 반짝이는 동그란 눈 (먼 눈은 조금 작게), 작은 입
    for ex, sc in ((hx + 11, 1.0), (hx + 23, 0.85)):
        sh.wash(ex, hy + 3, 2.4 * sc, 3.1 * sc, (96, 72, 70), alpha=255, layers=1, blur=0.2)
        sh.wash(ex + 0.8, hy + 1.8, 0.9 * sc, 0.9 * sc, WHITE, alpha=255, layers=1, blur=0.1)
    pen(sh, smooth([(hx + 15, hy + 13), (hx + 17, hy + 14.5), (hx + 19, hy + 13)], False, 4), 1.0)


def boy(frame):
    bob, front, back, swing = POSES[frame]
    sh = Sheet(*SPRITE, seed=460 + frame, ss=4)
    sh.line = LINE
    cx = 76
    y = bob
    hip = (cx + 2, 128 + y)

    leg(sh, (hip[0] - 4, hip[1]), back, True)
    leg(sh, (hip[0] + 5, hip[1]), front, False)   # 두 다리 모두 스웨터 뒤에서 나온다

    # 헐렁한 스웨터: 어깨가 둥글고 아래로 퍼지며, 아랫단이 뛰느라 살짝 날린다
    flap = math.sin(swing * 2.1) * 1.5
    sweater = smooth([(cx - 6, 78 + y), (cx + 12, 78 + y), (cx + 22, 92 + y), (cx + 25, 116 + y),
                      (cx + 16, 133 + y + flap), (cx, 135 + y), (cx - 16, 132 + y - flap), (cx - 22, 116 + y),
                      (cx - 20, 92 + y)], n=8)
    paint(sh, sweater, SWEATER)
    outline(sh, sweater, 1.4, pieces=3)
    for k in range(3):   # 아랫단 고무단 결
        x0 = cx - 12 + k * 11
        pen(sh, [(x0, 128 + y), (x0 + 0.5, 133 + y)], 0.9, alpha=140)
    for dx, dy, col in ((-12, 120, (244, 160, 168)), (12, 112, (150, 204, 176))):
        sh.wash(cx + dx, dy + y, 2.0, 1.6, col, alpha=200, layers=2, blur=0.5, wobble=0.3)   # 물감 묻은 자국

    head(sh, cx + 6, 48 + y, swing)

    # 두 팔로 꼭 안은 검은 잉크통
    bx, by = cx + 22, 104 + y
    jar = smooth([(bx - 10, by - 9), (bx + 10, by - 9), (bx + 12, by + 7), (bx + 8, by + 13), (bx - 8, by + 13),
                  (bx - 12, by + 7)], n=5)
    paint(sh, jar, INK_BLACK, shade=0.0)
    sh.wash(bx - 5, by + 1, 1.6, 5, (200, 196, 216), alpha=170, layers=1, blur=0.6)   # 유리 반짝임
    outline(sh, jar, 1.3, (60, 48, 60), pieces=2)
    cork = smooth([(bx - 5, by - 9), (bx - 5, by - 15), (bx + 5, by - 15), (bx + 5, by - 9)], n=3)
    paint(sh, cork, (222, 188, 150))
    outline(sh, cork, 1.1, pieces=1)
    # 소매가 긴 팔: 어깨 → 팔꿈치 → 잉크통 앞으로 감싼다
    shoulder = (cx + 2, 86 + y)
    hand = (bx + 9, by + 3 - swing * 0.4)
    arm = limb([shoulder, (cx - 2, by + 6), (bx - 2, by + 9), hand], 6.0, 5.2)
    paint(sh, arm, SWEATER)
    outline(sh, arm, 1.3, pieces=2)
    sh.wash(hand[0] + 2, hand[1], 3.2, 3.0, SKIN, alpha=255, layers=1, blur=0.4)
    pen(sh, ellipse_points(hand[0] + 2, hand[1], 3.3, 3.0, 14, -1.2, 3.4), 1.0)
    return sh.result()
