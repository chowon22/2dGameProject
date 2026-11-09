"""준비 화면 주인공: 배경과 같은 손그림 선 그림체 (sketch.Sheet 펜 선 + 수채 칠).

- 보랏빛 펜 선(PLUM)과 파스텔 수채 칠: gen_prepare.py 배경·HUD 와 같은 도구
- 동글동글 2.5등신 꼬마. 외형은 기획 참고 그림을 따른다:
  연보랏빛 회색 머리(뒷머리 끝이 둥글게 말림, 초승달 삐친 머리), 크림색 셔츠, 단추 달린 보라 조끼,
  주황 리본, 가죽끈과 놋쇠 버클, 무릎에 초승달 무늬가 있는 볼록한 바지, 레그워머, 단추 달린 부츠
- 가죽끈 버클에 반 잘린 모래시계 모양 잉크통(검정 잉크)이 매달려 진자처럼 흔들리고, 귀 위에는 마우스 커서와 같은 깃펜
- 팔은 어깨·팔꿈치·주먹으로 잡아 다리와 엇갈리게 앞뒤로 흔든다
- 오른쪽으로 달리는 3프레임. 화면에 1:1 로 그리므로 선 굵기가 배경과 같다

실행: python tools/boy_line.py  →  image/prepare/boy_line_{0,1,2}.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sketch import Sheet, ellipse_points, PASTEL, PLUM  # noqa: E402

SPRITE = (150, 180)
FEET = 172                      # 신발 밑창 (PIL y). prepare_mode.BOY_FEET 와 맞춘다
LINE_W = 3.4

WHITE = (255, 255, 255)
SKIN = (255, 236, 224)
HAIR = (152, 142, 184)
HAIR_SHADE = (118, 108, 154)
HAIR_SHINE = (204, 196, 226)
SMOCK = (255, 250, 240)          # 크림색 셔츠
SMOCK_SHADE = (214, 204, 232)
VEST = (134, 114, 178)
BUTTON = (222, 178, 104)
BOW = (248, 162, 126)
PANTS = (102, 106, 158)
MOON = (160, 194, 240)
WARMER = (250, 242, 232)
SHOE = (126, 130, 172)           # 부츠
STRAP = (200, 160, 108)
BRASS = (220, 182, 112)
GLASS = (222, 222, 246)
INK = (44, 38, 56)
FEATHER_TINT = (200, 186, 255)   # 커서 깃털의 빗금 색

# (몸 들썩임, 앞다리 (허벅지, 정강이) 각도, 뒷다리, 머리·잉크통 흔들림, 앞팔 (위팔, 아래팔), 뒷팔)
# 각도 0 = 똑바로 아래, + = 앞(오른쪽). 팔은 같은 쪽 다리와 반대로 흔든다
POSES = (
    (0.0, (0.75, 0.15), (-0.75, -1.15), 0.0, (-0.3, 0.1), (0.55, 1.7)),
    (-5.0, (0.45, -0.5), (-0.25, 0.05), 1.0, (0.05, 1.1), (-0.1, 0.7)),
    (0.0, (-0.75, -1.15), (0.75, 0.15), 0.0, (0.55, 1.7), (-0.3, 0.1)),
)
UPPER, FORE = 15, 14
# 잉크통이 버클을 축으로 흔들리는 각도 (프레임 0·1·2, 실행 순서 0-1-2-1 이라 진자처럼 오간다)
SWING = (-0.32, 0.0, 0.32)
ARM_BACK = 0.3    # 팔 흔들림 전체를 뒤로 기울이는 각도


def smooth(points, closed=True, n=8):
    """캣멀롬 곡선으로 점들을 부드럽게 잇는다."""
    pts = list(points)
    if closed:
        ext = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(ext[-2] if closed else pts[-1])
    return out


def shape(sh, pts, color, line=True, width=LINE_W, shade=None, light=None, shade_color=None):
    """채운 다음 테두리를 긋는다. shade/light: (cx, cy, rx, ry) 수채 그늘·빛."""
    sh.fill_poly(pts, color)
    if shade or light:
        tmp = Sheet(sh.w, sh.h, seed=sh.rng.randint(0, 9999), ss=sh.ss)
        if shade:
            tone = shade_color or (SMOCK_SHADE if color == SMOCK else _darker(color))
            tmp.wash(*shade, tone, alpha=150, layers=2, blur=2)
        if light:
            tmp.wash(*light, WHITE, alpha=110, layers=2, blur=2)
        sh.masked(tmp, _mask(sh, pts))
    if line:
        sh.stroke(pts + [pts[1]], width, amp=0.5, taper=False)


def _darker(c, k=0.82):
    return tuple(int(v * k) for v in c)


def _mask(sh, pts):
    from PIL import Image, ImageDraw
    m = Image.new('L', (sh.w, sh.h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m


def tube(sh, pts, color, width):
    """테두리 있는 굵은 관 (팔·다리): 펜 색으로 굵게 긋고 속을 칠한다."""
    sh.stroke(pts, width + LINE_W * 2, amp=0.3, taper=False)
    sh.stroke(pts, width, color, amp=0.0, taper=False)


def leg(sh, hip, thigh_a, shin_a, back):
    """엉덩이에서 무릎·발목을 잇고 동그란 신발을 신긴다. 각도 0 = 똑바로 아래, + = 앞(오른쪽)."""
    x, y = hip
    kx, ky = x + math.sin(thigh_a) * 16, y + math.cos(thigh_a) * 16
    ax, ay = kx + math.sin(shin_a) * 15, ky + math.cos(shin_a) * 15
    tone = 0.84 if back else 1.0

    def t(c):
        return tuple(int(v * tone) for v in c)
    # 레그워머 (정강이), 주름 고리 두 줄
    mx, my = kx + math.sin(shin_a) * 2, ky + math.cos(shin_a) * 2
    tube(sh, [(mx, my), (ax, ay)], t(WARMER), 8)
    c0, s0 = math.cos(shin_a), math.sin(shin_a)
    for f in (8, 11.5):
        rx, ry = kx + s0 * f, ky + c0 * f
        sh.stroke([(rx - c0 * 4.5, ry + s0 * 4.5), (rx + c0 * 4.5, ry - s0 * 4.5)], 1.4, amp=0.05)
    # 볼록한 바지 (허벅지~무릎)
    tube(sh, [(x, y - 2), (kx, ky)], t(PANTS), 12)
    if not back:   # 앞 무릎 초승달 무늬
        sh.fill_poly(ellipse_points(kx + 1, ky - 0.5, 3.4, 3.4, 16), MOON)
        sh.fill_poly(ellipse_points(kx - 0.8, ky - 1.6, 3.0, 3.0, 16), PANTS)
    # 신발: 발끝이 앞쪽(오른쪽)으로 나온 콩 모양. 정강이 각도를 따라 살짝 기운다
    tilt = shin_a * 0.5
    c, s = math.cos(tilt), math.sin(tilt)
    pts = []
    for px, py in ellipse_points(4, 0, 9, 5.5, 20):
        pts.append((ax + px * c - py * s, ay + 3 + px * s + py * c))
    shoe = tuple(int(v * (0.88 if back else 1.0)) for v in SHOE)
    shape(sh, pts, shoe, shade=(ax + 4, ay + 7, 9, 3))
    for d in (-1.5, 1.5):   # 부츠 단추
        bx, by = ax + 6 * c - d * s, ay + 1 + 6 * s + d * c
        sh.fill_poly(ellipse_points(bx, by, 1.0, 1.0, 8), PLUM)


def quill(sh, nib, top, ink=True):
    """커서(gen_title_images.cursor_pen)와 같은 깃펜: 흰 깃털 + 연보라 빗금, 가운데 깃대, 끝에 검정 잉크."""
    nx, ny = nib
    L = math.hypot(top[0] - nx, top[1] - ny)
    ux, uy = (top[0] - nx) / L, (top[1] - ny) / L
    px, py = -uy, ux

    def at(t, side):
        return nx + ux * L * t + px * side, ny + uy * L * t + py * side
    base = at(0.32, 0)
    feather = smooth([at(0.3, 0), at(0.5, 6), at(0.78, 7), at(1.0, 0.5), at(0.76, -5), at(0.5, -4)], True, 6)
    sh.fill_poly(feather, WHITE)
    xs, ys = [q[0] for q in feather], [q[1] for q in feather]
    sh.scribble((min(xs), min(ys), max(xs), max(ys)), FEATHER_TINT, alpha=200, gap=3.6, width=1.4,
                mask=_mask(sh, feather))
    sh.stroke(feather + [feather[1]], 2.6, amp=0.3, taper=False)
    sh.stroke(smooth([base, at(0.6, 1), at(0.97, 0.5)], False, 6), 1.8, amp=0.2)
    sh.stroke([nib, base], 4.0, amp=0.1, taper=False)
    if ink:
        sh.fill_poly(ellipse_points(nx, ny, 3.0, 3.0, 12), INK)


def arm(sh, shoulder, upper_a, fore_a, back):
    """어깨 → 팔꿈치 → 손목. 크림색 셔츠 소매와 둥근 주먹."""
    elbow = (shoulder[0] + math.sin(upper_a) * UPPER, shoulder[1] + math.cos(upper_a) * UPPER)
    wrist = (elbow[0] + math.sin(fore_a) * FORE, elbow[1] + math.cos(fore_a) * FORE)
    sleeve = SMOCK_SHADE if back else SMOCK
    tube(sh, [shoulder, elbow, wrist], sleeve, 9.5)
    # 소매 끝단 선
    c, s_ = math.cos(fore_a), math.sin(fore_a)
    cx, cy = wrist[0] - s_ * 2, wrist[1] - c * 2
    sh.stroke([(cx - c * 5, cy + s_ * 5), (cx + c * 5, cy - s_ * 5)], 1.6, amp=0.05)
    fx, fy = wrist[0] + s_ * 3, wrist[1] + c * 3
    shape(sh, ellipse_points(fx, fy, 4.6, 4.4, 16), SKIN if not back else (240, 214, 210), width=2.6)


def half_hourglass(sh, top, swing):
    """반 잘린 모래시계 모양 잉크통: 좁은 목에서 아래로 넓어지는 유리, 검정 잉크, 놋쇠 받침.
    top = 고리 자리. swing = 고리를 축으로 기운 각도 (+ 면 아래쪽이 앞으로 나간다)."""
    x0, y0 = top
    c, s_ = math.cos(swing), math.sin(swing)

    def P(dx, dy):   # 고리 기준 좌표 → 기울인 그림 좌표
        return x0 + dx * c + dy * s_, y0 - dx * s_ + dy * c

    def poly(pts):
        return [P(dx, dy) for dx, dy in pts]
    sh.stroke(poly([(0, -3), (0, 2)]), 2.0, PLUM, amp=0.05)
    shape(sh, smooth(poly([(-3.5, 1), (3.5, 1), (3.5, 4), (-3.5, 4)]), True, 2), BRASS, width=1.8)
    glass = smooth(poly([(-2.6, 4), (2.6, 4), (6, 11), (10, 19), (10, 21), (-10, 21), (-10, 19), (-6, 11)]), True, 4)
    shape(sh, glass, GLASS, width=2.2, light=(*P(-3, 11), 1.6, 4))
    sh.fill_poly(smooth(poly([(-6.6, 14), (6.6, 14), (9.6, 19.4), (9.6, 21), (-9.6, 21), (-9.6, 19.4)]), True, 3),
                 INK)        # 검정 잉크
    sh.stroke(smooth(poly([(-6.6, 14), (0, 13.2), (6.6, 14)]), False, 4), 1.4, PLUM, amp=0.02)
    sh.stroke(poly([(-2.6, 6.5), (-4.6, 11)]), 1.4, WHITE, amp=0.05)
    shape(sh, smooth(poly([(-12, 21), (12, 21), (12.4, 24.5), (-12.4, 24.5)]), True, 2), BRASS, width=2.2,
          light=(*P(-5, 22.4), 3, 1))


NAPE_END = 128     # 뒷머리 끝이 얼굴 원(턱)에 닿는 각도


def nape_tufts(hx, hy, sway):
    """뒷머리 아래 끝: 깃펜 밑 뒤통수(P0)에서 귀 밑 턱(P1, 얼굴 원 위)까지 비스듬히 내려가는 톱니.
    선은 바깥으로 살짝 볼록하고, 가닥 끝은 바깥 아래(왼쪽 아래)를 향한다."""
    p0 = (hx - 38, hy + 8)
    a = math.radians(NAPE_END)
    p1 = (hx + 4 + math.cos(a) * 31, hy + 6 + math.sin(a) * 28)
    ux, uy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(ux, uy)
    ux, uy = ux / L, uy / L
    nx, ny = uy, -ux                 # 선의 바깥 쪽 (왼쪽 아래)
    if ny < 0:
        nx, ny = -nx, -ny

    def on(t, k):
        bulge = 7.0 * math.sin(math.pi * t) ** 0.8   # 머리통처럼 둥글게 부풀어 얼굴 원을 감싼다
        return (p0[0] + ux * L * t + nx * (bulge + k), p0[1] + uy * L * t + ny * (bulge + k))
    # 가닥마다 위치·길이를 다르게: (선 위 끝 자리 t, 사이 골 t, 길이). 끝은 거의 아래로 늘어진다
    strands = ((0.22, 0.42, 5.0), (0.62, 0.80, 6.5), (0.95, 1.0, 3.0))
    keys = [p0]
    for t_tip, t_gap, ln in strands:
        bx, by = on(t_tip, 0)
        dx, dy = nx * 0.35 - 0.15, 1.0                  # 바깥으로 살짝, 대부분 아래로
        d = math.hypot(dx, dy)
        keys.append((bx + dx / d * ln - sway * 0.5, by + dy / d * ln))
        keys.append(on(t_gap, -0.5))
    keys[-1] = p1
    out = [keys[0]]
    for a, b in zip(keys, keys[1:]):                     # 변을 살짝 휘어 손으로 그은 가닥처럼
        mx, my = (a[0] + b[0]) / 2 + 1.4, (a[1] + b[1]) / 2 - 0.4
        for k in range(1, 6):
            t = k / 5
            out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * mx + t * t * b[0],
                        (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * my + t * t * b[1]))
    return out


def draw_frame(pose, seed, frame=0):
    bob, front, back, sway, front_arm, back_arm = pose
    sh = Sheet(*SPRITE, seed=seed, ss=3)
    sh.line = PLUM
    oy = bob
    hip_y = 136 + oy

    # ---- 다리 (뒷다리 먼저)
    leg(sh, (68, hip_y), back[0], back[1], back=True)
    leg(sh, (84, hip_y), front[0], front[1], back=False)

    # ---- 반대쪽 팔: 몸을 3/4 로 틀고 있어서 어깨가 몸통 앞쪽 가장자리 뒤에 있다.
    #      앞으로 흔들면 가슴 앞으로 팔과 주먹이 나오고, 뒤로 흔들면 몸통 뒤로 숨는다
    arm(sh, (92, 105 + oy), back_arm[0], back_arm[1], back=True)

    # ---- 몸통: 셔츠 위에 보라 조끼 (밑단은 앞이 뾰족)
    body = smooth([(64, 94 + oy), (90, 94 + oy), (100, 112 + oy), (106, 136 + oy), (96, 142 + oy),
                   (78, 140 + oy), (60, 143 + oy), (50, 136 + oy), (54, 112 + oy)], True, 6)
    sh.fill_poly(body, SMOCK)
    vest = smooth([(62, 98 + oy), (74, 100 + oy), (86, 118 + oy), (92, 100 + oy), (98, 112 + oy),
                   (104, 134 + oy), (90, 146 + oy), (80, 138 + oy), (60, 142 + oy), (51, 135 + oy),
                   (55, 112 + oy)], True, 6)
    shape(sh, vest, VEST, line=False, shade=(58, 130 + oy, 12, 18), light=(94, 118 + oy, 5, 10))
    sh.stroke(body + [body[1]], LINE_W, amp=0.5, taper=False)
    sh.stroke(smooth([(74, 100 + oy), (86, 118 + oy), (92, 100 + oy)], False, 6), 2.2, amp=0.2)   # 조끼 앞섶
    sh.stroke(smooth([(86, 118 + oy), (88, 132 + oy), (90, 146 + oy)], False, 6), 2.0, amp=0.2)
    for by in (124, 131, 138):
        sh.fill_poly(ellipse_points(92 + (by - 124) * 0.15, by + oy, 1.6, 1.6, 8), BUTTON)
    # 흰 깃과 주황 리본
    sh.stroke(smooth([(64, 96 + oy), (70, 103 + oy), (77, 99 + oy), (84, 103 + oy), (90, 96 + oy)], False, 5),
              2.6, amp=0.3)
    # 가죽끈: 앞 어깨에서 뒤 허리로, 끝의 둥근 놋쇠 버클에 잉크통을 매단다
    strap = smooth([(88, 96 + oy), (70, 110 + oy), (54, 122 + oy)], False, 6)
    sh.stroke(strap, 5.0, PLUM, amp=0.1)
    sh.stroke(strap, 3.0, STRAP, amp=0.05)
    half_hourglass(sh, (52, 128 + oy), SWING[frame])
    shape(sh, ellipse_points(54, 122 + oy, 4.4, 4.4, 16), BRASS, width=2.2)
    sh.fill_poly(ellipse_points(54.6, 121.4 + oy, 1.2, 1.2, 8), WHITE)
    # 주황 리본 (끈 위로)
    rx, ry = 83, 101 + oy
    for d in (-1, 1):
        shape(sh, smooth([(rx, ry), (rx + d * 6.5, ry - 4), (rx + d * 7, ry + 3.5)], True, 3), BOW, width=1.8)
    for d in (-1, 1):
        shape(sh, [(rx + d * 0.6, ry + 1), (rx + d * 3.4, ry + 9), (rx + d * 1.2, ry + 9.4)], BOW, width=1.6)
    shape(sh, ellipse_points(rx, ry, 2.2, 2.2, 10), BOW, width=1.6)

    # ---- 머리
    hx, hy = 80, 60 + oy
    # 머리 전체 볼륨: 뒤통수는 귀 뒤로 둥글게 부풀었다가 목덜미 쪽으로 좁아진다
    back_hair = smooth([(hx + 32, hy + 0), (hx + 36, hy - 8), (hx + 32, hy - 27), (hx + 12, hy - 39),
                        (hx - 12, hy - 39), (hx - 30, hy - 30), (hx - 38, hy - 14), (hx - 40, hy + 2),
                        (hx - 38, hy + 8), (hx - 32, hy + 12), (hx - 21, hy + 13), (hx + 10, hy + 12)], True, 6)
    hair_paint = dict(shade=(hx - 26, hy + 12, 13, 12), shade_color=HAIR_SHADE, light=(hx - 4, hy - 28, 18, 7))
    shape(sh, back_hair, HAIR, **hair_paint)
    # 얼굴: 칠은 전체, 테두리는 머리카락 밖으로 드러난 아래쪽(볼·턱)만
    face = ellipse_points(hx + 4, hy + 6, 31, 28, 40)
    shape(sh, face, SKIN, line=False, light=(hx + 10, hy, 12, 10))
    sh.stroke(ellipse_points(hx + 4, hy + 6, 31, 28, 26, math.radians(-12), math.radians(NAPE_END)), LINE_W, amp=0.5,
              taper=False)
    # 귀 뒤·목덜미 머리: 뾰족한 가닥 끝들이 뒤통수를 따라 둥근 호 위에 늘어서 귀 밑으로 감긴다
    nape = nape_tufts(hx, hy, sway)
    ear_line = smooth([(hx - 14, hy + 17), (hx - 17, hy + 21), (nape[-1][0] - 1, nape[-1][1])], False, 6)
    behind_ear = smooth([(hx - 30, hy + 4), (hx - 17, hy + 6), (hx - 18, hy + 13)], False, 5) + ear_line + nape[::-1]
    shape(sh, behind_ear, HAIR, line=False, **hair_paint)
    sh.stroke(nape, LINE_W, amp=0.2, taper=False)
    sh.stroke(ear_line, LINE_W, amp=0.1, taper=False)   # 귀 밑에서 뒤로 휘어 내려가는 머리선
    # 앞머리: 얼굴 윗부분을 덮는 모자 모양, 아래쪽 끝은 물결
    fringe = smooth([(hx - 26, hy + 14), (hx - 30, hy - 8), (hx - 16, hy - 32), (hx + 10, hy - 36),
                     (hx + 30, hy - 26), (hx + 37, hy - 6), (hx + 34, hy + 2),
                     (hx + 26, hy - 6), (hx + 20, hy + 2), (hx + 12, hy - 7), (hx + 4, hy + 1),
                     (hx - 4, hy - 8), (hx - 10, hy + 2), (hx - 18, hy - 2)], True, 6)
    shape(sh, fringe, HAIR, line=False, shade=(hx - 22, hy + 6, 10, 12), light=(hx + 4, hy - 26, 14, 6))
    # 앞머리 테두리는 얼굴과 만나는 물결 끝·옆선만 (머리카락 안쪽에는 선을 긋지 않는다)
    sh.stroke(smooth([(hx + 37, hy - 6), (hx + 34, hy + 2), (hx + 26, hy - 6), (hx + 20, hy + 2), (hx + 12, hy - 7),
                      (hx + 4, hy + 1), (hx - 4, hy - 8), (hx - 10, hy + 2), (hx - 18, hy - 2), (hx - 17, hy + 7)],
                     False, 6), LINE_W, amp=0.4, taper=False)
    # 귀, 그리고 귀 위에 걸쳐 꽂은 깃펜 (관자놀이에서 귀 위를 지나 뒤로 거의 수평)
    ear_pts = [(hx - 9, hy + 8), (hx - 15, hy + 7.5), (hx - 17, hy + 12.5), (hx - 13.5, hy + 18), (hx - 8.5, hy + 17)]
    sh.fill_poly(smooth(ear_pts, True, 4), SKIN)
    sh.stroke(smooth(ear_pts, False, 5), 2.2, amp=0.1, taper=False)          # 바깥 곡선만 (얼굴 쪽은 열어 둔다)
    sh.stroke(smooth([(hx - 12, hy + 10.5), (hx - 14, hy + 12.5), (hx - 12, hy + 15)], False, 4), 1.3, amp=0.05)
    quill(sh, (hx - 10, hy + 7), (hx - 56, hy - 4 - sway * 2), ink=False)
    # 앞머리 결 선
    for x in (hx - 6, hx + 8, hx + 20):
        sh.stroke(smooth([(x - 4, hy - 26), (x + 1, hy - 14), (x + 2, hy - 4)], False, 5), 1.4, HAIR_SHADE,
                  amp=0.1)
    # 머리 빛 고리
    sh.stroke(smooth([(hx - 14, hy - 22), (hx - 2, hy - 28), (hx + 12, hy - 27)], False, 6), 3.2, HAIR_SHINE,
              amp=0.2)
    # 초승달처럼 휜 삐친 머리
    ahoge = smooth([(hx - 2, hy - 37), (hx + 2, hy - 43), (hx - 4 - sway, hy - 51), (hx - 15 - sway * 2, hy - 52),
                    (hx - 8 - sway, hy - 48), (hx - 3, hy - 42), (hx - 6, hy - 38)], True, 6)
    shape(sh, ahoge, HAIR, width=2.6, light=(hx - 2, hy - 45, 2, 3))
    # 볼터치
    sh.wash(hx + 2, hy + 18, 6, 3.5, PASTEL['pink'], alpha=170, layers=2, blur=1.2)
    sh.wash(hx + 30, hy + 17, 4, 3, PASTEL['pink'], alpha=150, layers=2, blur=1.2)
    # 점 눈 + 빛
    for ex in (hx + 12, hx + 26):
        sh.fill_poly(ellipse_points(ex, hy + 9, 2.6, 3.6, 14), PLUM)
        sh.fill_poly(ellipse_points(ex + 0.8, hy + 7.6, 0.9, 0.9, 8), WHITE)
    # 웃는 입
    sh.stroke(smooth([(hx + 16, hy + 19), (hx + 19, hy + 22), (hx + 23, hy + 19)], False, 5), 2.2, amp=0.1)

    # ---- 앞팔 (맨 앞)
    arm(sh, (64, 105 + oy), front_arm[0] - ARM_BACK, front_arm[1] - ARM_BACK, back=False)

    return sh.result()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, '..', 'image', 'prepare')
    for i, pose in enumerate(POSES):
        draw_frame(pose, 700 + i, i).save(os.path.join(out, f'boy_line_{i}.png'))
    print('saved boy_line_0..2.png')


if __name__ == '__main__':
    main()
