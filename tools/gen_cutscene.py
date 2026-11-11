"""스토리 컷씬 이미지 (image/cutscene/*.png). 되찾은 색(파스텔 수채화) 타이틀과 같은 그림체.

배경 동굴(낮·밤)과 컬러 모래시계 잉크통은 타이틀 그림(title_restore, title_restore_night)을 그대로 쓰고,
여기서는 컷씬에만 나오는 것을 그린다 (PRD 2.4 스토리 흐름).

- cutscene_inside/background.png, dye_0..9.png: 동굴 안 (흑백 + 잉크통에서부터 번지는 색 층)
- fire.png / ice.png: 잉크통으로 피운 불, 만든 얼음
- man.png: 긴 외투에 챙 넓은 모자를 쓴 남자 실루엣 
- sleeper.png: 이불을 덮고 잠든 소년 
- carrier_red/green/blue.png: 색을 몸에 담아 나르는 운반자 몬스터 
- seal.png: 봉인 장소, black_bottle.png / color_bottle.png: 검정·컬러 잉크통 (타이틀 모래시계 split_bottle 의 위·아래 칸.
  모래시계는 두 잉크통이 합쳐진 모습이고, 이야기에서는 컬러를 동굴에서, 검정을 봉인 장소에서 따로 찾는다)
- run_sky/far/mid/ground.png: 색을 빼앗긴 흑백 들판 (준비 화면 층을 흑백으로)
- caption.png: 자막 쪽지

실행:  python tools/gen_cutscene.py
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import gen_title_bg as bg  # noqa: E402
import gen_title_pastel as pastel  # noqa: E402
import gen_title_restore as restore  # noqa: E402
from sketch import Sheet, bezier, ellipse_points, paper, PASTEL, PLUM, INK, WATERCOLOR  # noqa: E402

ROOT = pastel.ROOT
OUT = os.path.join(ROOT, 'image', 'cutscene')
PREPARE = os.path.join(ROOT, 'image', 'prepare')
W, H = 1280, 720
WHITE = (255, 255, 255)
SOFT_PLUM = bg.SOFT_PLUM
DARK = (58, 44, 76)   # 남자 실루엣: 보랏빛 펜보다 짙은 먹빛


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved cutscene/' + name, img.size)


def filled(sh, pts, color, alpha=235, light=None, seed=0, width=3.8, solid=False):
    """윤곽 안을 수채 번짐으로 칠하고 펜 선을 두른다. solid: 비치지 않게 바탕을 꽉 채운다 (실루엣)."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    rx, ry = (max(xs) - min(xs)) / 2 + 6, (max(ys) - min(ys)) / 2 + 6
    f = Sheet(sh.w, sh.h, seed=seed or sh.rng.randint(0, 9999))
    f.fill_poly(pts, color, 255 if solid else int(alpha * 0.75))
    f.wash(cx, cy, rx, ry, color, alpha=alpha, layers=3, blur=3)
    if light:
        f.wash(cx - rx * 0.35, cy - ry * 0.35, rx * 0.4, ry * 0.35, light, alpha=120, layers=2, blur=3)
    sh.masked(f, bg.poly_mask((sh.w, sh.h), pts))
    if width:
        sh.stroke(pts + [pts[0]], width)


# ================================================================ 컷 2: 불과 얼음
def fire():
    w, h = 150, 190
    sh = Sheet(w, h, seed=801)
    sh.line = PLUM
    cx, base = w / 2, h - 22
    sh.wash(cx, base - 50, 62, 70, PASTEL['peach'], alpha=90, layers=2, blur=10)   # 불빛
    outer = bezier((cx, base), (cx - 70, base - 6), (cx - 46, base - 90), (cx - 8, base - 150), 30) + \
        bezier((cx - 8, base - 150), (cx + 6, base - 110), (cx + 30, base - 120), (cx + 26, base - 96), 14)[1:] + \
        bezier((cx + 26, base - 96), (cx + 64, base - 60), (cx + 62, base - 4), (cx, base), 24)[1:]
    filled(sh, outer, WATERCOLOR['red'], 240, PASTEL['peach'], 802)
    inner = bezier((cx, base - 8), (cx - 34, base - 10), (cx - 22, base - 60), (cx - 2, base - 88), 20) + \
        bezier((cx - 2, base - 88), (cx + 24, base - 56), (cx + 30, base - 12), (cx, base - 8), 20)[1:]
    filled(sh, inner, (250, 196, 96), 245, (255, 244, 200), 803, width=2.6)
    sh.wash(cx, base - 30, 12, 16, (255, 250, 228), alpha=220, layers=2, blur=2)
    # 장작 두 개
    for a in (-0.22, 0.22):
        dx, dy = math.cos(a) * 46, math.sin(a) * 46
        sh.stroke([(cx - dx, base + 6 - dy), (cx + dx, base + 6 + dy)], 9, (196, 150, 120), 255, amp=0.4)
        sh.stroke([(cx - dx, base + 6 - dy), (cx + dx, base + 6 + dy)], 2.4, PLUM, 200, amp=0.6)
    for x, y in ((cx - 40, base - 120), (cx + 40, base - 140), (cx + 12, base - 170)):
        bg.sparkle_stroke(sh, x, y, 6, (255, 214, 120), 230, 2.2)
    return sh.result(crop=True)


def ice():
    w, h = 230, 180
    sh = Sheet(w, h, seed=811)
    sh.line = PLUM
    cx, base = w / 2, h - 18
    sh.wash(cx, base - 50, 70, 60, PASTEL['sky'], alpha=80, layers=2, blur=10)
    shards = ((cx, 0, 112, 30), (cx - 34, -0.4, 74, 22), (cx + 36, 0.45, 80, 22), (cx - 58, -0.75, 46, 16),
              (cx + 62, 0.8, 50, 16))
    for i, (x, a, ln, hw) in enumerate(sorted(shards, key=lambda s: -abs(s[1]))):
        dx, dy = math.sin(a), -math.cos(a)
        px, py = -dy, dx
        tip = (x + dx * ln, base + dy * ln)
        pts = [(x - px * hw * 0.5, base - py * hw * 0.5), (x - px * hw * 0.55 + dx * ln * 0.72, base + dy * ln * 0.72 - py * hw * 0.55),
               tip, (x + px * hw * 0.55 + dx * ln * 0.72, base + dy * ln * 0.72 + py * hw * 0.55),
               (x + px * hw * 0.5, base + py * hw * 0.5)]
        filled(sh, pts, (150, 200, 240), 230, WHITE, 812 + i, width=3.2)
        sh.stroke([((pts[0][0] + pts[-1][0]) / 2, base), tip], 1.6, WHITE, 200, amp=0.3)
    sh.wash(cx, base + 2, 70, 9, (190, 214, 240), alpha=200, layers=2, blur=2)
    sh.stroke([(cx - 72, base + 4), (cx + 72, base + 4)], 3.2, amp=0.8)
    for x, y in ((cx - 50, 30), (cx + 52, 44), (cx + 8, 12)):
        bg.sparkle_stroke(sh, x, y, 7, WHITE, 240, 2.2)
        bg.sparkle_stroke(sh, x, y, 7, (150, 200, 240), 160, 1.0)
    return sh.result(crop=True)


# ================================================================ 컷 3: 남자, 잠든 소년
def man():
    """오른쪽(동굴 쪽)을 향해 걷는 키 큰 남자. 얼굴은 모자 챙 그늘에 가려 보이지 않는 실루엣."""
    w, h = 260, 440
    sh = Sheet(w, h, seed=821)
    sh.line = (150, 132, 190)   # 밤에 보이도록 달빛이 비친 테두리
    cx = 120
    ground = h - 10
    coat_light = (78, 62, 104)
    sil = (30, 24, 44)          # 실루엣 바탕
    # 다리 (외투 아래로 조금)
    for x0, x1 in ((cx - 26, cx - 40), (cx + 16, cx + 30)):
        leg = [(x0 - 9, ground - 90), (x0 + 9, ground - 90), (x1 + 8, ground - 8), (x1 - 8, ground - 8)]
        filled(sh, leg, sil, 255, None, 822, solid=True)
        shoe = [(x1 - 12, ground - 14), (x1 + 20, ground - 14), (x1 + 24, ground), (x1 - 12, ground)]
        filled(sh, shoe, sil, 255, None, 823, width=3, solid=True)
    # 외투: 어깨에서 아래로 넓게 퍼지고 뒷자락이 바람에 날린다
    coat = bezier((cx - 30, 120), (cx - 52, 180), (cx - 70, 270), (cx - 92, 352), 24) + \
        bezier((cx - 92, 352), (cx - 60, 362), (cx - 20, 352), (cx + 8, 360), 12)[1:] + \
        bezier((cx + 8, 360), (cx + 34, 352), (cx + 56, 356), (cx + 62, 350), 8)[1:] + \
        bezier((cx + 62, 350), (cx + 54, 270), (cx + 46, 180), (cx + 34, 120), 24)[1:] + \
        bezier((cx + 34, 120), (cx + 14, 108), (cx - 12, 108), (cx - 30, 120), 10)[1:]
    filled(sh, coat, DARK, 255, coat_light, 824, solid=True)
    sh.stroke([(cx + 6, 130), (cx + 2, 250), (cx + 6, 352)], 2.2, coat_light, 220)   # 앞섶
    for y in (170, 215, 260):
        sh.wash(cx + 14, y, 3.2, 3.2, (200, 180, 140), alpha=230, layers=1, blur=0.5)  # 단추
    # 목도리
    scarf = [(cx - 26, 116), (cx + 32, 116), (cx + 30, 136), (cx - 24, 136)]
    filled(sh, scarf, (112, 90, 140), 255, None, 825, width=3, solid=True)
    tail = bezier((cx - 22, 126), (cx - 60, 130), (cx - 84, 150), (cx - 106, 146), 14)
    sh.stroke(tail, 12, (112, 90, 140), 255, amp=0.6)
    sh.stroke(tail, 2.4, sh.line, 200, amp=0.8)
    # 머리 + 모자
    head = ellipse_points(cx + 2, 92, 22, 26, 48)
    filled(sh, head, sil, 255, None, 828, width=3.2, solid=True)
    for ex in (cx + 10, cx + 22):   # 그늘 속에서 희미하게 빛나는 눈
        sh.wash(ex, 92, 2.6, 1.8, (230, 220, 250), alpha=200, layers=1, blur=0.6)
    crown = [(cx - 26, 64), (cx - 22, 18), (cx + 28, 16), (cx + 32, 64)]
    filled(sh, crown, sil, 255, None, 826, solid=True)
    sh.stroke([(cx - 24, 52), (cx + 30, 52)], 6, (112, 90, 140), 255, amp=0.4)   # 모자 띠
    brim = ellipse_points(cx + 4, 66, 64, 11, 48)
    filled(sh, brim, sil, 255, None, 827, width=3.4, solid=True)
    # 앞으로 내민 팔: 잉크통을 받쳐 들 손 (잉크통은 실행 중에 이 손 위에 그린다)
    arm = bezier((cx + 26, 140), (cx + 54, 170), (cx + 76, 196), (cx + 104, 200), 16)
    sh.stroke(arm, 24, sh.line, 255, amp=0.4)   # 테두리
    sh.stroke(arm, 18, DARK, 255, amp=0.4)
    sh.wash(cx + 110, 200, 11, 9, (214, 196, 206), alpha=255, layers=2, blur=1)  # 장갑 낀 손
    sh.ellipse(cx + 110, 200, 11, 9, 2.8)
    return sh.result()


MAN_HAND = (230, 200)   # man.png 안 손 위치 (PIL). cutscene_mode 가 잉크통을 여기 올린다


def sleeper():
    """이불을 덮고 옆으로 누워 잠든 소년: 베개 위로 연보랏빛 머리와 감은 눈만."""
    w, h = 330, 170
    sh = Sheet(w, h, seed=831)
    sh.line = PLUM
    ground = h - 14
    sh.wash(w / 2, ground - 4, 150, 12, (110, 90, 140), alpha=90, layers=2, blur=3)
    pillow = ellipse_points(78, ground - 34, 58, 28, 48)
    filled(sh, pillow, (255, 250, 246), 245, None, 832)
    # 얼굴
    sh.wash(98, ground - 66, 30, 28, (255, 226, 214), alpha=255, layers=2, blur=1)
    sh.ellipse(98, ground - 66, 29, 27, 3.2)
    sh.wash(110, ground - 56, 7, 4, (248, 170, 180), alpha=200, layers=1, blur=1.5)       # 볼
    sh.stroke(bezier((96, ground - 66), (100, ground - 60), (108, ground - 60), (112, ground - 66), 10), 2.6)  # 감은 눈
    # 머리카락 (스프라이트와 같은 연보라)
    hair = (196, 172, 226)
    for i, (x, y, rx, ry) in enumerate(((84, ground - 86, 34, 22), (66, ground - 70, 20, 24), (106, ground - 92, 24, 14))):
        sh.wash(x, y, rx, ry, hair, alpha=245, layers=3, blur=2)
    sh.stroke(bezier((52, ground - 60), (50, ground - 100), (96, ground - 116), (128, ground - 88), 24), 3.4)
    sh.stroke(bezier((128, ground - 88), (118, ground - 82), (110, ground - 84), (104, ground - 78), 8), 3)
    sh.stroke(bezier((96, ground - 108), (90, ground - 132), (114, ground - 140), (116, ground - 124), 16), 3.2)  # 삐침 머리
    sh.wash(100, ground - 120, 7, 9, hair, alpha=230, layers=2, blur=1)
    # 이불: 몸 모양으로 둥글게 솟은 언덕
    quilt = bezier((112, ground - 30), (130, ground - 92), (230, ground - 104), (300, ground - 46), 40) + \
        bezier((300, ground - 46), (316, ground - 24), (314, ground), (290, ground), 12)[1:] + \
        [(110, ground)]
    filled(sh, quilt, PASTEL['pink'], 245, WHITE, 833)
    for x, y in ((170, ground - 56), (230, ground - 66), (260, ground - 30), (190, ground - 20)):
        sh.wash(x, y, 9, 8, PASTEL['lemon'], alpha=230, layers=2, blur=1)   # 이불 무늬
        sh.ellipse(x, y, 8, 7, 1.8, SOFT_PLUM, 220)
    sh.stroke(bezier((116, ground - 40), (150, ground - 46), (176, ground - 36), (196, ground - 44), 14), 2.4, SOFT_PLUM, 200)
    return sh.result(crop=True)


# ================================================================ 컷 4: 운반자 몬스터
def carrier(color, seed):
    """색을 몸에 담은 둥실 떠다니는 물방울 몬스터. 배 속에서 색이 출렁이고, 등엔 작은 날개."""
    w, h = 170, 170
    sh = Sheet(w, h, seed=seed)
    sh.line = PLUM
    cx, cy = 88, 82
    # 날개 (뒤)
    for d in (-1, 1):
        wing = bezier((cx + d * 30, cy - 30), (cx + d * 80, cy - 70), (cx + d * 84, cy - 10), (cx + d * 40, cy - 6), 20)
        filled(sh, wing, (240, 236, 250), 220, None, seed + 1 + d, width=2.8)
    body = [(cx + math.cos(a) * 50 * (1 + 0.04 * math.sin(3 * a)),
             cy + math.sin(a) * 50 * (1 if math.sin(a) < 0 else 1.06) + (6 * math.sin(a * 5) if math.sin(a) > 0.5 else 0))
            for a in [2 * math.pi * i / 60 for i in range(60)]]
    f = Sheet(w, h, seed=seed + 3)
    f.fill_poly(body, (250, 246, 252), 235)
    f.wash(cx, cy + 22, 44, 26, color, alpha=255, layers=3, blur=3)        # 배 속에 담긴 색
    f.wash(cx + 10, cy + 12, 18, 10, color, alpha=200, layers=2, blur=2)
    f.wash(cx - 18, cy - 24, 14, 10, WHITE, alpha=220, layers=2, blur=2)    # 윤기
    sh.masked(f, bg.poly_mask((w, h), body))
    surface = [(x, cy + 6 + 4 * math.sin((x - cx) / 7)) for x in range(cx - 44, cx + 46, 4)]
    sh.stroke(surface, 2.2, tuple(int(c * 0.75) for c in color), 230, amp=0.4)   # 출렁이는 수면
    sh.stroke(body + [body[0]], 3.8)
    # 얼굴
    for ex in (cx - 16, cx + 14):
        sh.wash(ex, cy - 14, 5, 6, (44, 34, 58), alpha=255, layers=1, blur=0.6)
        sh.wash(ex - 1.5, cy - 16.5, 1.6, 1.6, WHITE, alpha=255, layers=1, blur=0.2)
    sh.stroke(bezier((cx - 6, cy - 2), (cx - 2, cy + 3), (cx + 2, cy + 3), (cx + 6, cy - 2), 8), 2.4)
    for ex in (cx - 26, cx + 24):
        sh.wash(ex, cy - 4, 6, 3.5, (248, 170, 180), alpha=170, layers=1, blur=1.5)
    return sh.result(crop=True)


# ================================================================ 컷 5: 봉인 장소
def seal():
    """동굴 깊은 곳 돌 제단. 위에서 한 줄기 빛이 내려온다. 제단 윗면은 PIL y 470 (실행 중 검정 잉크통 자리)."""
    ys = np.linspace(0, 1, H)
    stops = [(0.0, (36, 30, 66)), (0.5, (58, 48, 92)), (0.78, (74, 62, 104)), (1.0, (48, 40, 74))]
    col = np.zeros((H, 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    sky = np.repeat(col[:, None, :], W, axis=1)
    grain = np.asarray(paper(W, H, seed=5).convert('RGB'), np.float32) / np.array((247, 244, 237), np.float32)
    base = Image.fromarray(np.clip(sky * grain, 0, 255).astype(np.uint8)).convert('RGBA')

    sh = Sheet(W, H, seed=841)
    sh.line = (24, 20, 40)
    light_line = (150, 132, 186)
    cx = W / 2
    # 빛줄기: 위가 좁고 아래로 퍼지는 사다리꼴을 크게 흐려 깐다 (번짐을 겹치면 가로 줄무늬가 진다)
    m = bg.poly_mask((W, H), [(cx - 60, -20), (cx + 60, -20), (cx + 230, 560), (cx - 230, 560)])
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(26)), np.float32) / 255
    fall = np.clip(1.15 - np.linspace(0, 1, H) * 0.7, 0, 1)[:, None]   # 아래로 갈수록 옅게
    beam = np.zeros((H, W, 4), np.uint8)
    beam[..., :3] = (255, 244, 214)
    beam[..., 3] = (m * fall * 95).astype(np.uint8)
    base.alpha_composite(Image.fromarray(beam, 'RGBA'))
    # 양옆 바위벽 (울퉁불퉁)
    for d in (-1, 1):
        edge = [(cx + d * (520 - 80 * math.sin(y / 120) - 40 * math.sin(y / 47)), y) for y in range(-10, H + 20, 20)]
        edge = bg.lumpy(edge, 10, sh.rng, 0.2)
        far = W + 40 if d > 0 else -40
        wall = edge + [(far, H + 20), (far, -10)]
        f = Sheet(W, H, seed=843 + d)
        f.fill_poly(wall, (30, 26, 50), 255)
        for y in range(40, H, 110):
            f.wash(cx + d * 600, y, 90, 70, (70, 58, 100), alpha=150, layers=2, blur=8)
        sh.masked(f, bg.poly_mask((W, H), wall))
        sh.stroke(edge, 4.2, light_line, 220)
    # 바닥
    floor = [(x, 560 + 4 * math.sin(x / 50)) for x in range(-10, W + 20, 16)]
    f = Sheet(W, H, seed=845)
    f.fill_poly(floor + [(W + 20, H), (-10, H)], (44, 38, 70), 255)
    f.wash(cx, 590, 300, 50, (130, 112, 160), alpha=150, layers=3, blur=10)     # 빛이 비친 바닥
    sh.masked(f, bg.poly_mask((W, H), floor + [(W + 20, H), (-10, H)]))
    sh.stroke(floor, 3.8, light_line, 200)
    # 바닥의 봉인 문양 (빛 아래 원)
    sh.stroke(ellipse_points(cx, 600, 250, 40, 80), 2.6, (220, 206, 240), 160, amp=0.6)
    sh.stroke(ellipse_points(cx, 600, 200, 30, 80), 2.0, (220, 206, 240), 130, amp=0.6)
    for i in range(10):
        a = 2 * math.pi * i / 10
        x, y = cx + math.cos(a) * 225, 600 + math.sin(a) * 35
        sh.stroke([(x - 6, y - 2), (x, y + 3), (x + 6, y - 2)], 2.0, (220, 206, 240), 150, amp=0.3)
    # 돌 제단
    top_y = 470
    ped = [(cx - 86, top_y), (cx + 86, top_y), (cx + 70, top_y + 26), (cx + 62, 572), (cx - 62, 572), (cx - 70, top_y + 26)]
    filled(sh, ped, (150, 140, 170), 250, (210, 200, 226), 846, width=0)
    sh.stroke(ped + [ped[0]], 4.2)
    sh.stroke([(cx - 70, top_y + 26), (cx + 70, top_y + 26)], 3.2)
    sh.stroke(ellipse_points(cx, 530, 22, 22, 40), 2.4, (90, 80, 112), 220)     # 새겨진 문양
    sh.stroke([(cx, 512), (cx, 548)], 2.0, (90, 80, 112), 200)
    sh.stroke([(cx - 18, 530), (cx + 18, 530)], 2.0, (90, 80, 112), 200)
    # 떠다니는 먼지 빛
    for _ in range(36):
        x, y = cx + sh.rng.uniform(-240, 240), sh.rng.uniform(40, 540)
        if abs(x - cx) > 60 + y * 0.36:
            continue
        sh.wash(x, y, 2, 2, (255, 246, 220), alpha=sh.rng.randint(120, 220), layers=1, blur=0.6)
    base.alpha_composite(sh.result())
    return base.convert('RGB')


def half_bottle(kind):
    """타이틀 모래시계(gen_title_restore.split_bottle)의 반쪽 그대로 (kind: 'black' 위 칸 / 'color' 아래 칸).
    모래시계는 검정·컬러 두 잉크통이 목의 이음 고리에서 합쳐진 모습이고, 이야기에서는 따로 찾는다
    (동굴: 컬러, 봉인 장소: 검정). 잘라 쓰지 않고 같은 곡선·나무판·이음 고리로 그 반쪽만 그린다.
    양옆 기둥은 두 병을 이어 주는 틀이라 뺀다.
    두 병은 모양이 같고, 모래시계에서는 검정 병이 거꾸로 뒤집혀 컬러 병 위에 끼워져 있다.
    따로 놓일 땐 둘 다 바로 선다: 이음 고리(위) → 둥근 유리 → 넓은 나무판 받침(아래).
    - 컬러: 파스텔 나무, 바닥에 모인 빨강·초록·파랑
    - 검정: 먹빛 나무, 바닥에 고인 검정 잉크 (모래시계에서 나무판 쪽에 차 있던 그 잉크)"""
    bw, bh = 240, 320
    cx = bw / 2
    sh = Sheet(bw, bh, seed=41)
    sh.line = PLUM
    top, bottom = 46, 274
    neck = (top + bottom) / 2
    half = bezier((cx - 9, neck), (cx - 14, neck + 30), (cx - 86, bottom - 80), (cx - 78, bottom), 40)
    mirror = [(2 * cx - x, y) for x, y in half]
    mask = pastel.poly_mask((bw, bh), half + mirror[::-1])
    dark_wood = (214, 186, 170)   # 검정 잉크통 쪽 나무 (split_bottle 과 같은 색)

    glass = Sheet(bw, bh, seed=42)
    glass.wash(cx, neck, 80, 130, (236, 240, 255), alpha=150, layers=2)
    if kind == 'black':
        surf = bottom - 66   # 바닥에 고인 잉크의 수면 (살짝 출렁)
        pool = [(x, surf + 3 * math.sin(x / 9) + 2 * math.sin(x / 4 + 1)) for x in range(0, bw + 1, 4)]
        ink = Sheet(bw, bh, seed=44)
        ink.fill_poly([(0, 0), (bw, 0), (bw, bh), (0, bh)], INK, 250)
        ink.wash(cx + 22, bottom - 24, 30, 18, (78, 62, 102), alpha=150, layers=3, blur=4)   # 보랏빛 먹 번짐
        ink.wash(cx - 30, surf + 8, 24, 6, (120, 112, 138), alpha=170, layers=2, blur=2)    # 수면 윤기
        glass.masked(ink, pastel.poly_mask((bw, bh), pool + [(bw, bh), (0, bh)]))
    else:
        glass.wash(cx - 22, bottom - 16, 34, 16, WATERCOLOR['red'], alpha=220, layers=3)
        glass.wash(cx + 20, bottom - 14, 32, 15, WATERCOLOR['blue'], alpha=220, layers=3)
        glass.wash(cx, bottom - 24, 22, 12, WATERCOLOR['green'], alpha=220, layers=3)
    sh.masked(glass, mask)

    sh.stroke(half, 4.4)
    sh.stroke(mirror, 4.4)
    sh.stroke(bezier((cx - 58, bottom - 30), (cx - 64, bottom - 50), (cx - 52, bottom - 70), (cx - 44, bottom - 80), 14),
              3, WHITE, 220, amp=0.6)

    # 넓은 나무판 받침 (검정은 먹빛 나무)
    wood = dark_wood if kind == 'black' else PASTEL['peach']
    y0, y1 = bottom - 2, bottom + 26
    sh.wash(cx, (y0 + y1) / 2, 94, 13, wood, alpha=240, layers=2, blur=2)
    sh.wash(cx - 40, (y0 + y1) / 2 - 3, 40, 5, WHITE, alpha=120, layers=1, blur=2)
    sh.stroke([(cx - 96, y0), (cx + 96, y0 + 1), (cx + 98, y1), (cx - 95, y1 - 1), (cx - 96, y0 - 2)], 4.2)
    for k in range(5):
        xx = cx - 70 + k * 35
        sh.stroke([(xx, y0 + 7), (xx + 10, y1 - 7)], 1.8, pastel.SOFT_PLUM, 160)

    # 목의 이음 고리 (두 병이 여기서 맞물린다)
    rw, rh = 15, 7
    sh.wash(cx, neck, rw, rh, dark_wood, alpha=235, layers=2, edge=0.3, blur=0.8, wobble=0.04)
    sh.wash(cx - 6, neck - 3, 6, 1.5, WHITE, alpha=130, layers=1, blur=0.8)
    sh.stroke([(cx - rw, neck - rh), (cx + rw, neck - rh + 0.5), (cx + rw + 0.5, neck + rh), (cx - rw, neck + rh - 0.5),
               (cx - rw, neck - rh - 1)], 2.8)
    return sh.result(crop=True, margin=4)


def black_bottle():
    """검정 잉크통 (모래시계 위 칸을 바로 세운 것). 봉인 장소에서 찾는다."""
    return half_bottle('black')


def color_bottle():
    """컬러 잉크통 (모래시계 아래 칸). 동굴에서 찾고, 남자가 가져간다."""
    return half_bottle('color')


# ================================================================ 동굴 안
INSIDE_GROUND = 585     # 동굴 안 바닥 (PIL y). 바깥 배경 땅과 같은 높이라 소년이 같은 자리를 밟는다
INSIDE_ROCK_TOP = 552   # 잉크통을 올려 둔 바위 윗면 (PIL y). 잉크통은 그 위 물들이기 자리 (DYE_FROM) 에 떠 있다


def crystal_cluster(sh, x, base, size, tint, seed):
    """바닥이나 벽에서 솟은 수정 무리."""
    rng = sh.rng
    shards = sorted(((rng.uniform(-0.6, 0.6), rng.uniform(0.55, 1.0)) for _ in range(rng.randint(3, 5))),
                    key=lambda s: -abs(s[0]))
    for i, (a, k) in enumerate(shards):
        ln, hw = size * k, size * 0.2 * (0.7 + k * 0.5)
        dx, dy = math.sin(a), -math.cos(a)
        px, py = -dy, dx
        x0 = x + a * size * 0.5
        tip = (x0 + dx * ln, base + dy * ln)
        pts = [(x0 - px * hw, base - py * hw), (x0 - px * hw + dx * ln * 0.72, base + dy * ln * 0.72 - py * hw),
               tip, (x0 + px * hw + dx * ln * 0.72, base + dy * ln * 0.72 + py * hw), (x0 + px * hw, base + py * hw)]
        filled(sh, pts, tint, 235, WHITE, seed + i, width=3.4)
        sh.stroke([(x0, base - 2), (tip[0] * 0.9 + x0 * 0.1, tip[1] * 0.9 + base * 0.1)], 1.6, WHITE, 190, amp=0.3)
    sh.wash(x, base - size * 0.4, size * 0.9, size * 0.7, tint, alpha=60, layers=2, blur=10)   # 수정 빛


def cave_inside():
    """동굴 안쪽 (컬러). 둥근 바위 천장과 벽이 화면을 감싸고, 안쪽엔 파스텔 수정이 빛나고,
    가운데 납작한 바위 위에서 잉크통 빛이 퍼진다. 흑백 배경·물들이기 층은 이것으로 만든다."""
    G = INSIDE_GROUND
    ys = np.linspace(0, 1, H)
    stops = [(0.0, (150, 130, 196)), (0.45, (196, 176, 226)), (G / H, (232, 212, 232)),
             (G / H + 0.001, (214, 200, 230)), (1.0, (196, 184, 220))]
    col = np.zeros((H, 3), np.float32)
    for c in range(3):
        col[:, c] = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
    grain = np.asarray(paper(W, H, seed=7).convert('RGB'), np.float32) / np.array((247, 244, 237), np.float32)
    base = Image.fromarray(np.clip(np.repeat(col[:, None, :], W, axis=1) * grain, 0, 255).astype(np.uint8)).convert('RGBA')

    sh = Sheet(W, H, seed=871)
    sh.line = PLUM
    cx = W / 2
    bx, by = pastel.DYE_FROM   # 잉크통 자리

    # 안쪽 벽: 울퉁불퉁한 바위 턱 두 겹 (뒤 턱은 옅게, 앞 턱은 조금 짙게)
    for k, (tint, top, alpha) in enumerate(((PASTEL['lavender'], 330, 120), ((176, 152, 206), 430, 140))):
        line = [(x, top + 26 * math.sin(x / (90 + k * 40) + k * 2) + 14 * math.sin(x / 31 + k))
                for x in range(-20, W + 40, 14)]
        line = bg.lumpy(line, 18, sh.rng, 0.35)
        m = bg.poly_mask((W, H), line + [(W + 40, G + 4), (-20, G + 4)])
        f = Sheet(W, H, seed=872 + k)
        for x in range(0, W + 160, 160):
            f.wash(x, top + 100, 150, 130, tint, alpha=alpha, layers=2, blur=8)
        sh.masked(f, m)
        sh.stroke(line, 2.6, SOFT_PLUM, 170, amp=1.2)
        for _ in range(7):   # 바위 금
            x = sh.rng.uniform(40, W - 40)
            y = top + sh.rng.uniform(40, 110)
            sh.stroke([(x, y), (x + 10, y + 14), (x + 4, y + 30)], 2.2, SOFT_PLUM, 140)
    # 들어온 쪽(왼쪽)에서 비치는 바깥 빛
    sh.wash(60, 420, 200, 260, (255, 240, 214), alpha=110, layers=3, blur=16)

    # 잉크통 빛
    sh.wash(bx, by, 300, 230, (255, 246, 214), alpha=90, layers=3, blur=16)
    sh.wash(bx, by, 150, 130, PASTEL['mint'], alpha=80, layers=3, blur=10)
    sh.wash(bx, by + 10, 80, 80, (255, 252, 236), alpha=140, layers=3, blur=8)

    # 안쪽 수정 무리
    for x, size, tint in ((250, 70, PASTEL['mint']), (420, 46, PASTEL['sky']), (900, 56, PASTEL['pink']),
                          (1060, 80, PASTEL['sky']), (1170, 44, PASTEL['lavender'])):
        crystal_cluster(sh, x, G - 4, size, tint, 880 + int(x))

    # 바닥
    floor = [(x, G + 3 * math.sin(x / 41) + 2 * math.sin(x / 13)) for x in range(-10, W + 20, 16)]
    sh.wash(cx, G + 60, W * 0.5, 50, PASTEL['lavender'], alpha=90, layers=3, blur=8)
    sh.wash(bx, G + 30, 240, 36, PASTEL['lemon'], alpha=120, layers=3, blur=8)    # 잉크통 빛이 바닥에 비침
    sh.stroke(floor, 4.2, amp=1.6)
    for x in range(30, W, 52):
        if abs(x - cx) < 200:
            continue
        y = G + 30 + (x * 7) % 60
        sh.stroke([(x, y), (x + 14, y + 1)], 2.2, SOFT_PLUM, 140)
    for x, y, rx, tint in ((330, G + 8, 26, PASTEL['lavender']), (980, G + 10, 32, PASTEL['pink']),
                           (180, G + 70, 20, PASTEL['sky']), (1120, G + 90, 24, PASTEL['peach'])):
        bg.rock(sh, x, y, rx, rx * 0.6, tint)

    # 잉크통을 올려 둔 납작한 바위
    top = INSIDE_ROCK_TOP
    stone = bezier((bx - 110, G + 4), (bx - 120, top + 6), (bx - 60, top - 4), (bx, top - 2), 24) + \
        bezier((bx, top - 2), (bx + 70, top), (bx + 122, top + 8), (bx + 108, G + 4), 24)[1:]
    stone = bg.lumpy(stone, 4, sh.rng, 0.2)
    f = Sheet(W, H, seed=876)
    f.fill_poly(stone, PASTEL['lavender'], 230)
    f.wash(bx - 30, top + 10, 70, 16, (255, 246, 220), alpha=200, layers=2, blur=4)   # 윗면에 비친 빛
    f.wash(bx + 50, G - 6, 60, 14, (150, 128, 186), alpha=120, layers=2, blur=4)
    sh.masked(f, bg.poly_mask((W, H), stone))
    sh.stroke(stone, 4.2)
    sh.stroke([(bx - 70, top + 14), (bx + 40, top + 16)], 2.0, SOFT_PLUM, 150)

    # 천장과 양옆 벽: 바닥까지 내려와 화면을 감싸는 짙은 바위 (밖에서 본 입구가 아니라 안에 들어온 느낌)
    hole = bezier((70, G + 10), (40, 330), (150, 80), (cx - 60, 70), 50) + \
        bezier((cx - 60, 70), (cx + 240, 64), (W - 110, 110), (W - 80, G + 10), 50)[1:]
    hole = bg.lumpy(hole, 22, sh.rng, 0.12)
    frame = hole + [(W + 60, G + 10), (W + 60, -40), (-60, -40), (-60, G + 10)]
    rock_col = (148, 122, 176)
    f = Sheet(W, H, seed=877)
    f.fill_poly(frame, rock_col, 255)
    f.wash(90, 260, 160, 320, (122, 98, 152), alpha=200, layers=3, blur=10)       # 벽 그늘
    f.wash(W - 80, 300, 160, 320, (122, 98, 152), alpha=200, layers=3, blur=10)
    f.wash(cx, 20, 420, 60, (176, 150, 200), alpha=170, layers=3, blur=8)
    f.wash(70, 470, 80, 120, (255, 226, 214), alpha=110, layers=2, blur=10)        # 들어온 쪽 빛이 벽에
    for _ in range(10):
        f.wash(f.rng.uniform(0, W), f.rng.uniform(0, 140), 60, 30, PASTEL['pink'], alpha=70, layers=2, blur=6)
    sh.masked(f, bg.poly_mask((W, H), frame))
    sh.stroke(hole, 5)
    for x0, y0, x1, y1 in ((20, 300, 52, 340), (110, 100, 150, 130), (900, 18, 940, 44), (W - 50, 260, W - 20, 310),
                           (30, 480, 50, 530), (W - 40, 470, W - 20, 520), (400, 20, 440, 40)):
        sh.stroke([(x0, y0), ((x0 + x1) / 2 + 6, (y0 + y1) / 2), (x1, y1)], 2.8, PLUM, 200)
    # 천장에서 내려온 종유석 (구멍 윤곽 바로 아래)
    for x, ln in ((280, 54), (360, 30), (520, 44), (700, 62), (780, 34), (930, 48), (1060, 30)):
        ty = min(p[1] for p in hole if abs(p[0] - x) < 12) - 4
        pts = [(x - 14, ty), (x - 3, ty + ln), (x + 3, ty + ln), (x + 14, ty)]
        filled(sh, pts, rock_col, 250, (200, 180, 220), 890 + x, width=3.4)

    # 반짝이 (수정·잉크통 둘레)
    for _ in range(16):
        a = sh.rng.uniform(0, 2 * math.pi)
        d = sh.rng.uniform(90, 230)
        bg.sparkle_stroke(sh, bx + math.cos(a) * d, by + math.sin(a) * d * 0.6, sh.rng.uniform(4, 8), WHITE, 220)
    base.alpha_composite(sh.result())
    return base.convert('RGB')


# ================================================================ 컷 6: 흑백 들판
def gray_layer(name):
    """준비 화면 층을 색을 빼앗긴 흑백으로 (투명도는 그대로). gray_background 와 같은 밝기 매기기."""
    img = Image.open(os.path.join(PREPARE, name + '.png')).convert('RGBA')
    arr = np.asarray(img, np.float32)
    g = arr[..., 0] * 0.62 + arr[..., 1] * 0.38
    g = np.clip(250 - (250 - g) * 1.5, 40, 255)
    out = arr.copy()
    for c, k in enumerate((1.0, 0.985, 0.965)):
        out[..., c] = g * k
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')


# ================================================================ 자막 쪽지
def caption():
    """한 문장이 들어가는 쪽지 (화면 아래, 땅 띠 위에 얹는다)."""
    w, h = 1000, 108
    sh = Sheet(w, h, seed=851)
    sh.line = PLUM
    box = pastel.wobbly_box(14, 14, w - 14, h - 14, 20, sh.rng)
    p = Sheet(w, h, seed=852)
    p.fill_poly([(0, 0), (w, 0), (w, h), (0, h)], (255, 251, 246), 238)
    p.wash(160, 44, 200, 50, PASTEL['pink'], alpha=60, layers=2, blur=10)
    p.wash(w - 180, h - 44, 220, 50, PASTEL['sky'], alpha=60, layers=2, blur=10)
    p.wash(w / 2, h / 2, 260, 40, PASTEL['lemon'], alpha=40, layers=2, blur=10)
    sh.masked(p, pastel.poly_mask((w, h), box))
    sh.stroke(box, 3.6)
    return sh.result()


def main():
    save(fire(), 'fire.png')
    save(ice(), 'ice.png')
    save(man(), 'man.png')
    save(sleeper(), 'sleeper.png')
    for i, (name, col) in enumerate(WATERCOLOR.items()):
        save(carrier(col, 860 + i * 10), f'carrier_{name}.png')
    # 동굴 안: 흑백 배경 + 잉크통에서부터 번지는 물들이기 층 (타이틀과 같은 방식, image/cutscene_inside)
    inside = cave_inside()
    out = os.path.join(ROOT, 'image', 'cutscene_inside')
    os.makedirs(out, exist_ok=True)
    pastel.gray_background(inside).save(os.path.join(out, 'background.png'))
    for i, f in enumerate(pastel.dye_frames(inside)):
        f.save(os.path.join(out, f'dye_{i}.png'))
    print('saved cutscene_inside/background.png, dye_0..9.png')
    save(seal(), 'seal.png')
    save(black_bottle(), 'black_bottle.png')
    save(color_bottle(), 'color_bottle.png')
    for name in ('sky', 'far', 'mid', 'ground'):
        save(gray_layer(name), f'run_{name}.png')
    save(caption(), 'caption.png')


if __name__ == '__main__':
    main()
