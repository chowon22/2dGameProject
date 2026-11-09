"""준비 화면 주인공: 애니메이션 꼬마(치비) 그림체.

- 머리가 몸의 1/3 쯤 되는 2.5등신, 가는 다리
- 검은 머리(잉크 색): 끝이 뾰족한 머리카락 다발을 겹쳐 쌓고, 정수리에 빛 고리
- 큰 눈: 진한 윗눈썹 선, 위가 어둡고 아래가 밝은 회청색 눈동자, 흰 빛 두 개
- 손을 덮는 긴 소매의 헐렁한 흰 후드, 검은 바지, 흰 운동화
- 검은 잉크통을 두 팔로 안고 오른쪽으로 달린다 (3프레임)

크게(200x260) 그려서 실행 중에 줄여 쓴다. 선·칠 도구는 boy_sprite 와 같다.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from boy_sprite import smooth, pen, outline, open_line, paint, limb, _joint
from sketch import Sheet, ellipse_points

SPRITE = (200, 260)
FEET = 250
LINE = (46, 40, 54)          # 펜 선: 거의 검정에 가까운 보랏빛 회색
SOFT_LINE = (120, 108, 122)
WHITE = (255, 255, 255)
SKIN = (255, 240, 232)
CHEEK = (246, 170, 172)
HAIR = (54, 50, 64)          # 잉크빛 검은 머리
HAIR_SHINE = (128, 124, 146)
IRIS_TOP = (52, 58, 82)
IRIS_BOTTOM = (140, 170, 196)
HOODIE = (250, 249, 252)
HOODIE_SHADE = (214, 214, 230)
PANTS = (62, 60, 74)
SHOE = (246, 244, 246)
INK_BLACK = (40, 36, 48)

# (몸 들썩임, 앞다리 (허벅지, 정강이), 뒷다리, 흔들림 위상)
POSES = (
    (0.0, (0.8, 0.05), (-0.6, -1.25), 0.0),
    (-6.0, (0.3, -0.8), (-0.1, 0.3), 1.0),
    (0.0, (-0.6, -1.25), (0.8, 0.05), 2.0),
)
LIGHT = (6.0, -5.0)
HAPPY = True   # 웃는 얼굴 (감은 눈 + 활짝 웃는 입)


def fill(sh, pts, color, shade=0.2):
    paint(sh, pts, color, shade=shade, light=LIGHT)


def lock(base0, base1, tip, bend=0.0):
    """끝이 뾰족한 머리카락 다발: base0 → tip → base1. bend 로 휘어진다."""
    mx0 = ((base0[0] + tip[0]) / 2 + bend * (tip[1] - base0[1]) * 0.25,
           (base0[1] + tip[1]) / 2 - bend * (tip[0] - base0[0]) * 0.25)
    mx1 = ((base1[0] + tip[0]) / 2 + bend * (tip[1] - base1[1]) * 0.25,
           (base1[1] + tip[1]) / 2 - bend * (tip[0] - base1[0]) * 0.25)
    side0 = smooth([base0, mx0, tip], False, 8)
    side1 = smooth([tip, mx1, base1], False, 8)
    return side0 + side1[1:]


def leg(sh, hip, pose, behind):
    knee = _joint(hip, pose[0], 25)
    foot = _joint(knee, pose[1], 24)
    shape = limb([hip, knee, foot], 7.5, 5.5)
    fill(sh, shape, tuple(int(c * 0.85) for c in PANTS) if behind else PANTS, 0.1)
    outline(sh, shape, 2.0, LINE, pieces=2)
    toe = 1 if pose[1] > -0.7 else 0.55
    shoe = smooth([(foot[0] - 9, foot[1] - 4), (foot[0] + 3, foot[1] - 6), (foot[0] + 14 * toe, foot[1] - 1),
                   (foot[0] + 14 * toe, foot[1] + 4), (foot[0] - 2, foot[1] + 6), (foot[0] - 10, foot[1] + 3)], n=5)
    fill(sh, shoe, SHOE, 0.25)
    outline(sh, shoe, 1.9, LINE, pieces=1)
    pen(sh, [(foot[0] - 8, foot[1] + 2.5), (foot[0] + 12 * toe, foot[1] + 3)], 1.2, SOFT_LINE)   # 밑창 선


def eye(sh, x, y, s, outer=-1):
    """큰 눈 하나. s: 크기 (먼 눈은 작고 좁다)."""
    w, h = 11 * s, 13 * s
    white = smooth([(x - w, y - h * 0.5), (x, y - h * 0.75), (x + w, y - h * 0.45), (x + w * 0.9, y + h * 0.5),
                    (x, y + h * 0.75), (x - w * 0.9, y + h * 0.45)], n=6)
    fill(sh, white, WHITE, 0.15)
    # 눈동자: 위는 어둡고 아래는 밝은 회청색
    big = sh.img.size
    ss = sh.ss
    m = Image.new('L', big, 0)
    ImageDraw.Draw(m).ellipse(((x - w * 0.62) * ss, (y - h * 0.7) * ss, (x + w * 0.62) * ss, (y + h * 0.72) * ss), 255)
    wm = Image.new('L', big, 0)
    ImageDraw.Draw(wm).polygon([(px * ss, py * ss) for px, py in white], fill=255)
    m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(wm)))
    grad = np.linspace(0, 1, big[1], dtype=np.float32)[:, None]
    t = np.clip((grad * sh.h - (y - h * 0.7)) / (h * 1.4), 0, 1)
    rgb = (np.array(IRIS_TOP, np.float32) * (1 - t[..., None]) + np.array(IRIS_BOTTOM, np.float32) * t[..., None])
    rgb = np.broadcast_to(rgb, (big[1], big[0], 3)).astype(np.uint8)
    iris = Image.fromarray(rgb, 'RGB').convert('RGBA')
    iris.putalpha(m)
    sh.img.alpha_composite(iris)
    sh.wash(x, y - h * 0.05, w * 0.26, h * 0.3, (26, 24, 36), alpha=255, layers=1, blur=0.3)   # 동공
    sh.wash(x - w * 0.22, y - h * 0.32, w * 0.22, h * 0.2, WHITE, alpha=255, layers=1, blur=0.2)   # 큰 빛
    sh.wash(x + w * 0.25, y + h * 0.35, w * 0.12, h * 0.1, WHITE, alpha=230, layers=1, blur=0.2)  # 작은 빛
    # 윗눈썹 선: 진하고 둥글게, 바깥 눈꼬리(outer 쪽)만 살짝 길게 빠진다
    o = outer
    top = smooth([(x - o * w * 1.15, y - h * 0.3), (x - o * w * 0.45, y - h * 0.78), (x + o * w * 0.4, y - h * 0.8),
                  (x + o * w * 1.0, y - h * 0.5)], False, 8)
    pen(sh, top, 3.4 * s, LINE, 255)
    pen(sh, [(x - o * w * 1.0, y - h * 0.38), (x - o * w * 1.4, y - h * 0.5)], 1.6 * s, LINE)   # 눈꼬리 속눈썹
    pen(sh, smooth([(x - w * 0.5, y + h * 0.72), (x, y + h * 0.82), (x + w * 0.5, y + h * 0.7)], False, 5),
        1.1 * s, SOFT_LINE)


def head(sh, hx, hy, swing):
    flutter = math.sin(swing * 2.1)
    # 뒷머리 (얼굴 뒤): 바람에 뒤로 뻗친 다발들
    mass = ellipse_points(hx - 4, hy - 4, 47, 45, 60)
    fill(sh, mass, HAIR, 0.15)
    back_locks = [((hx - 30, hy - 32), (hx - 46, hy - 8), (hx - 60, hy - 16 + flutter * 2), 0.5),
                  ((hx - 44, hy - 10), (hx - 46, hy + 14), (hx - 60, hy + 8 + flutter * 3), 0.4),
                  ((hx - 42, hy + 8), (hx - 32, hy + 32), (hx - 50, hy + 30 + flutter * 2), 0.2)]
    for b0, b1, tip, bend in back_locks:
        shape = lock(b0, b1, tip, bend)
        fill(sh, shape, HAIR, 0.1)
        open_line(sh, shape, 2.0, LINE)
    open_line(sh, mass[34:60] + mass[:6], 2.2, LINE)   # 뒤통수 윤곽

    # 얼굴: 둥근 볼, 오른쪽 아래로 살짝 뾰족한 턱
    face = smooth([(hx - 30, hy - 8), (hx - 18, hy - 36), (hx + 14, hy - 40), (hx + 38, hy - 20), (hx + 42, hy + 6),
                   (hx + 34, hy + 30), (hx + 18, hy + 44), (hx - 4, hy + 40), (hx - 26, hy + 22)], n=8)
    fill(sh, face, SKIN, 0.22)
    sh.wash(hx + 16, hy - 6, 20, 16, (255, 250, 244), alpha=120, layers=2, blur=4)   # 볼록한 빛
    sh.wash(hx + 26, hy + 20, 9, 5, CHEEK, alpha=170, layers=2, blur=2)
    sh.wash(hx + 2, hy + 24, 6, 3.5, CHEEK, alpha=110, layers=2, blur=2)
    for k in range(3):   # 볼의 빗금 홍조
        pen(sh, [(hx + 21 + k * 4, hy + 20), (hx + 19 + k * 4, hy + 24)], 1.0, (226, 120, 130), 170)
    open_line(sh, face[len(face) * 4 // 9:], 2.2, LINE)
    # 귀
    ear = smooth([(hx - 22, hy + 4), (hx - 30, hy + 2), (hx - 32, hy + 14), (hx - 24, hy + 20)], False, 5)
    fill(sh, ear + [(hx - 20, hy + 12)], SKIN, 0.2)
    open_line(sh, ear, 1.8, LINE)

    if HAPPY:
        # 웃느라 감은 눈 (∩ 모양 반달), 활짝 웃는 입
        for ex, sc in ((hx + 13, 1.0), (hx + 35, 0.78)):
            pen(sh, smooth([(ex - 8 * sc, hy + 11), (ex - 3 * sc, hy + 3), (ex + 3 * sc, hy + 3), (ex + 8 * sc, hy + 10)],
                           False, 8), 3.2 * sc, LINE, 255)
        mouth = smooth([(hx + 19, hy + 25), (hx + 30, hy + 24), (hx + 28, hy + 32), (hx + 22, hy + 33)], n=6)
        fill(sh, mouth, (196, 92, 100), 0.1)
        sh.wash(hx + 24, hy + 31, 3, 1.6, (246, 150, 150), alpha=220, layers=1, blur=0.4)   # 혀
        outline(sh, mouth, 1.5, LINE, pieces=1)
    else:
        eye(sh, hx + 12, hy + 9, 1.0, outer=1)    # 가까운 눈: 바깥 눈꼬리가 왼쪽(귀 쪽)
        eye(sh, hx + 35, hy + 7, 0.72, outer=-1)  # 먼 눈: 바깥 눈꼬리가 오른쪽
        pen(sh, [(hx + 30, hy + 30), (hx + 33, hy + 31.5)], 1.4, LINE)      # 작은 입
    pen(sh, [(hx + 42, hy + 14), (hx + 44, hy + 18)], 1.2, SOFT_LINE)  # 콧날

    # 앞머리: 정수리에서 이마로 내려오는 뾰족한 다발들 (눈 위에서 끝나고, 한두 가닥은 눈을 살짝 가린다)
    crown = (hx + 2, hy - 46)
    cap = smooth([(hx - 34, hy - 6), (hx - 30, hy - 36), (hx - 4, hy - 52), (hx + 26, hy - 46), (hx + 44, hy - 24),
                  (hx + 46, hy - 6), (hx + 20, hy - 18), (hx - 10, hy - 16)], n=8)
    fill(sh, cap, HAIR, 0.1)
    # 정수리 빛 고리: 결을 따라 끊어진 짧은 밝은 띠 몇 개 (앞머리 밑에 깔려 가닥 사이로만 보인다)
    for t0, t1 in ((0.3, 0.55),):
        seg = smooth([(hx - 28, hy - 26), (hx - 12, hy - 38), (hx + 10, hy - 39), (hx + 30, hy - 30)], False, 10)
        seg = seg[int(len(seg) * t0):int(len(seg) * t1)]
        pen(sh, seg, 4.0, HAIR_SHINE, 45)
        pen(sh, seg, 1.6, HAIR_SHINE, 80)
    bangs = [((hx - 14, hy - 24), (hx + 2, hy - 26), (hx - 6, hy - 4), 0.1),
             ((hx - 2, hy - 26), (hx + 14, hy - 26), (hx + 8, hy - 7), 0.0),
             ((hx + 10, hy - 26), (hx + 26, hy - 24), (hx + 23, hy - 8), -0.1),
             ((hx + 22, hy - 24), (hx + 38, hy - 18), (hx + 37, hy - 8), -0.15),
             ((hx + 34, hy - 20), (hx + 46, hy - 10), (hx + 48, hy + 8), -0.2),
             ((hx - 26, hy - 18), (hx - 12, hy - 22), (hx - 22, hy + 14), 0.15)]
    for b0, b1, tip, bend in bangs:
        shape = lock(b0, b1, tip, bend)
        fill(sh, shape, HAIR, 0.1)
        open_line(sh, shape, 1.9, LINE)
    open_line(sh, cap[:len(cap) * 5 // 8], 2.3, LINE, pieces=2)
    # 삐친 머리 (정수리 바보털)
    pen(sh, smooth([crown, (crown[0] - 6, crown[1] - 12), (crown[0] - 18, crown[1] - 14 + flutter * 2)], False, 6),
        2.0, LINE)


def boy(frame):
    bob, front, back, swing = POSES[frame]
    sh = Sheet(*SPRITE, seed=520 + frame, ss=3)
    cx = 98
    y = bob
    hip = (cx + 2, 192 + y)

    leg(sh, (hip[0] - 6, hip[1]), back, True)
    leg(sh, (hip[0] + 7, hip[1]), front, False)

    # 후드 모자 (목 뒤로 넘긴)
    hood = smooth([(cx - 26, 132 + y), (cx - 40, 118 + y), (cx - 34, 104 + y), (cx - 12, 112 + y), (cx + 4, 128 + y)],
                  n=6)
    fill(sh, hood, HOODIE_SHADE, 0.2)
    outline(sh, hood, 2.0, LINE, pieces=2)
    # 헐렁한 후드 몸통
    flap = math.sin(swing * 2.1) * 2
    body = smooth([(cx - 12, 124 + y), (cx + 16, 124 + y), (cx + 32, 142 + y), (cx + 36, 178 + y),
                   (cx + 26, 200 + y + flap), (cx, 203 + y), (cx - 24, 199 + y - flap), (cx - 32, 176 + y),
                   (cx - 28, 142 + y)], n=8)
    fill(sh, body, HOODIE, 0.35)
    outline(sh, body, 2.2, LINE, pieces=3)
    pen(sh, smooth([(cx - 24, 192 + y), (cx, 195 + y), (cx + 26, 192 + y)], False, 6), 1.2, SOFT_LINE)   # 고무단
    for dx in (4, 12):   # 끈
        pen(sh, smooth([(cx + dx, 128 + y), (cx + dx + 1, 142 + y), (cx + dx - 1, 150 + y)], False, 5), 1.4, LINE)
    pen(sh, smooth([(cx + 2, 124 + y), (cx + 8, 132 + y), (cx + 18, 126 + y)], False, 5), 1.6, LINE)   # 목둘레

    head(sh, cx + 6, 74 + y, swing)

    # 두 팔로 꼭 안은 검은 잉크통
    bx, by = cx + 34, 160 + y
    jar = smooth([(bx - 14, by - 12), (bx + 14, by - 12), (bx + 17, by + 9), (bx + 11, by + 18), (bx - 11, by + 18),
                  (bx - 17, by + 9)], n=5)
    fill(sh, jar, INK_BLACK, 0.0)
    sh.wash(bx - 7, by + 2, 2.2, 7, (190, 186, 210), alpha=170, layers=1, blur=0.6)
    outline(sh, jar, 2.0, LINE, pieces=2)
    cork = smooth([(bx - 7, by - 12), (bx - 7, by - 21), (bx + 7, by - 21), (bx + 7, by - 12)], n=3)
    fill(sh, cork, (214, 180, 144), 0.2)
    outline(sh, cork, 1.6, LINE, pieces=1)
    # 손을 덮는 긴 소매
    shoulder = (cx + 2, 134 + y)
    paw = (bx + 13, by + 4 - swing * 0.5)
    arm = limb([shoulder, (cx - 4, by + 8), (bx - 4, by + 13), paw], 8.5, 7.5)
    fill(sh, arm, HOODIE, 0.25)
    outline(sh, arm, 2.0, LINE, pieces=2)
    pen(sh, smooth([(paw[0] - 4, paw[1] - 6), (paw[0] - 6, paw[1]), (paw[0] - 4, paw[1] + 6)], False, 5), 1.2, SOFT_LINE)
    sh.wash(paw[0] + 4, paw[1] + 1, 3, 2.6, SKIN, alpha=255, layers=1, blur=0.4)   # 소매 끝에 살짝 나온 손끝
    return sh.result()
