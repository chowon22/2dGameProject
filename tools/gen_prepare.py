"""준비 화면·로딩 화면 이미지 (image/prepare/*.png). 되찾은 색(파스텔 수채화) 타이틀과 같은 그림체.

- sky.png: 하늘 (움직이지 않음, 1280x720)
- far.png / mid.png / ground.png: 옆으로 흘러가는 배경 층 (1280 폭, 왼쪽 끝과 오른쪽 끝이 이어진다)
- boy_0..2.png: 검은 잉크통을 안고 오른쪽으로 달리는 꼬마 화가 3프레임 (0·2: 다리를 벌린 자세, 1: 모은 자세)
- shadow.png: 소년 발밑 그림자
- loading.png: 로딩 화면 한 장
- ink_<색>.png: 잉크 양 표시용 작은 잉크병
- hud.png: 잉크 양 쪽지, button_*.png: 준비 화면 버튼, toast.png: 알림 쪽지

실행:  python tools/gen_prepare.py
"""
import math
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import gen_title_bg as bg  # noqa: E402
import gen_title_pastel as pastel  # noqa: E402
from sketch import Sheet, bezier, ellipse_points, PASTEL, PLUM  # noqa: E402

ROOT = pastel.ROOT
OUT = os.path.join(ROOT, 'image', 'prepare')
W, H = 1280, 720
WHITE = (255, 255, 255)
SOFT_PLUM = bg.SOFT_PLUM
GROUND_Y = 560          # 땅 윗선 (PIL y). 실행 중 소년 발이 닿는 높이와 맞춘다 (prepare_mode.GROUND)
INK_BLACK = (44, 38, 56)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved prepare/' + name, img.size)


def wrapped(draw, seed, h=H):
    """가로로 이어지는 층: 세 배 넓은 시트 가운데에 그리고, 양옆으로 넘친 부분을 반대편에 접어 넣는다."""
    sh = Sheet(W * 3, h, seed=seed)
    sh.line = PLUM
    draw(sh)
    big = sh.result()
    out = big.crop((W, 0, W * 2, h))
    out.alpha_composite(big.crop((0, 0, W, h)))
    out.alpha_composite(big.crop((W * 2, 0, W * 3, h)))
    return out


# ================================================================ 배경 층
def sky():
    base = bg.sky_gradient()
    sh = Sheet(W, H, seed=301)
    sh.line = PLUM
    sh.img.alpha_composite(bg.sun().img)
    for x, y, w, h, tint in ((520, 140, 120, 34, PASTEL['pink']), (930, 90, 150, 40, PASTEL['sky']),
                             (1180, 230, 90, 26, PASTEL['lavender']), (300, 270, 70, 20, PASTEL['peach'])):
        bg.cloud(sh, x, y, w, h, tint)
    base.alpha_composite(sh.result())
    return base.convert('RGB')


def _hills(sh, tint, base_y, alpha, period, amp, seed_off):
    """주기가 W 의 약수인 언덕이라 이어 붙여도 이음매가 없다."""
    def hy(x):
        return (base_y - amp * math.sin(2 * math.pi * x / period + seed_off)
                - amp * 0.4 * math.sin(2 * math.pi * x / (period / 2) + seed_off * 2))
    hill = [(x, hy(x - W)) for x in range(W - 20, W * 2 + 40, 20)]
    m = bg.poly_mask((W * 3, H), hill + [(W * 2 + 40, H), (W - 20, H)])
    f = Sheet(W * 3, H, seed=sh.rng.randint(0, 9999))
    for x in range(W, W * 2, 160):  # 번짐은 가운데 한 장 안에만 (접을 때 두 번 겹치지 않게)
        f.wash(x, base_y + 70, 140, 110, tint, alpha=alpha, layers=2, blur=6)
    sh.masked(f, m)
    sh.stroke([p for p in hill if W <= p[0] <= W * 2], 2.4, SOFT_PLUM, 170, amp=2, taper=False)


def far():
    """먼 언덕 두 겹 + 아주 작은 나무 실루엣."""
    def draw(sh):
        _hills(sh, PASTEL['lavender'], 400, 150, 640, 34, 0.6)
        for x in range(W + 60, W * 2, 230):
            ty = 400 - 34 * math.sin(2 * math.pi * (x - W) / 640 + 0.6) - 13.6 * math.sin(2 * math.pi * (x - W) / 320 + 1.2)
            sh.wash(x, ty - 26, 18, 22, PASTEL['mint'], alpha=150, layers=2, blur=3)
            sh.stroke([(x, ty + 4), (x, ty - 10)], 2.2, SOFT_PLUM, 160)
        _hills(sh, PASTEL['mint'], 470, 160, 1280 / 3, 22, 2.0)
    return wrapped(draw, 311)


def pine_tree(sh, x, ground, height, width, tint):
    """gen_title_bg.pine_tree 와 같은 그림 (시트 크기가 화면과 달라도 되게)."""
    size = (sh.w, sh.h)
    sh.stroke([(x - 6, ground), (x - 5, ground - height * 0.2)], 4)
    sh.stroke([(x + 6, ground), (x + 5, ground - height * 0.2)], 4)
    for t in range(3):
        base_y = ground - height * 0.18 - t * height * 0.24
        top_y = base_y - height * (0.36 - t * 0.04)
        hw = width * (1 - t * 0.26)
        tri = bg.poly_mask(size, [(x - hw, base_y + 6), (x, top_y), (x + hw, base_y + 6)])
        fill = Sheet(*size, seed=sh.rng.randint(0, 9999))
        fill.wash(x, (base_y + top_y) / 2 + 6, hw, (base_y - top_y) * 0.6, tint, alpha=210, layers=3, blur=4)
        fill.wash(x - hw * 0.3, (base_y + top_y) / 2, hw * 0.3, (base_y - top_y) * 0.3, WHITE, alpha=90, layers=2)
        sh.masked(fill, tri)
        sh.stroke([(x - hw, base_y), (x - hw * 0.45, (base_y + top_y) / 2 + 4), (x, top_y)], 4)
        sh.stroke([(x, top_y), (x + hw * 0.45, (base_y + top_y) / 2 + 3), (x + hw, base_y)], 4)
        sh.stroke(bezier((x - hw, base_y), (x - hw * 0.4, base_y + 9), (x + hw * 0.4, base_y + 9), (x + hw, base_y), 20),
                  3.4)


def mid():
    """나무·덤불 (땅 바로 뒤)."""
    def draw(sh):
        g = GROUND_Y + 6
        items = (('leafy', 80, 300, 88, 'pink'), ('pine', 300, 260, 66, 'mint'), ('leafy', 560, 340, 96, 'lavender'),
                 ('pine', 760, 230, 56, 'sky'), ('leafy', 980, 280, 84, 'peach'), ('pine', 1170, 300, 70, 'lavender'))
        for kind, x, hgt, size, tint in items:
            if kind == 'leafy':
                bg.leafy_tree(sh, W + x, g, hgt, size, PASTEL[tint])
            else:
                pine_tree(sh, W + x, g - 2, hgt, size, PASTEL[tint])
        for bx, r, tint in ((200, 34, 'mint'), (450, 40, 'pink'), (680, 28, 'sky'), (880, 36, 'mint'), (1080, 30, 'pink')):
            x = W + bx
            sh.wash(x, GROUND_Y - r * 0.45, r * 0.95, r * 0.6, PASTEL[tint], alpha=220, layers=3, blur=3)
            sh.stroke(ellipse_points(x, GROUND_Y - 2, r, r * 0.9, 40, math.pi * 1.02, math.pi * 0.96), 3.8)
    return wrapped(draw, 321)


def ground():
    """땅 띠: 민트빛 풀밭 + 흙길, 풀 포기와 꽃 (아래 160px)."""
    gh = H - GROUND_Y + 20  # 이미지 높이 (윗선 위로 20px 여유)
    top = 20

    def draw(sh):
        sh.fill_poly([(W, top), (W * 2, top), (W * 2, gh), (W, gh)], (226, 242, 224), 255)
        for x in range(W, W * 2, 160):
            sh.wash(x, top + 70, 130, 70, PASTEL['mint'], alpha=130, layers=2, blur=6)
        for x in range(W, W * 2, 160):  # 흙길
            sh.wash(x, top + 46, 150, 16, PASTEL['peach'], alpha=150, layers=2, blur=4, wobble=0.1)
        line = [(x, top + 3 * math.sin(2 * math.pi * (x - W) / 320) + 2 * math.sin(2 * math.pi * (x - W) / 128))
                for x in range(W, W * 2 + 1, 16)]
        sh.stroke(line, 4.2, amp=1.6, taper=False)
        for x in range(W + 20, W * 2, 52):
            y = top + 70 + (x * 7) % 50
            sh.stroke([(x, y), (x + 16, y)], 2.2, SOFT_PLUM, 150)
        for x in range(W + 40, W * 2, 130):
            bg.grass_tuft(sh, x + sh.rng.uniform(-20, 20), top + 4, sh.rng.uniform(0.8, 1.2))
        tints = list(PASTEL.values())
        for i in range(22):
            bg.flower(sh, W + sh.rng.uniform(0, W), top + sh.rng.uniform(70, gh - 20), tints[i % len(tints)])
        for x in range(W + 300, W * 2, 520):
            bg.rock(sh, x, top + 8, 22, 12, PASTEL['lavender'])
    return wrapped(draw, 331, gh)


# ================================================================ 소년 (tools/boy_anime.py)
from boy_anime import boy, FEET  # noqa: E402
import boy_line  # noqa: E402


def shadow():
    sh = Sheet(140, 30, seed=420)
    sh.wash(70, 15, 52, 8, (110, 90, 140), alpha=110, layers=3, blur=3)
    return sh.result()


# ================================================================ 로딩 화면
def loading():
    """밤하늘 수채 종이 한가운데 달리는 소년, 아래에 '여정을 준비하는 중' (점 세 개는 실행 중에 찍는다)."""
    base = bg.sky_gradient(night=True)
    sh = Sheet(W, H, seed=501)
    sh.line = PLUM
    for _ in range(40):
        x, y = sh.rng.uniform(20, W - 20), sh.rng.uniform(20, 460)
        if sh.rng.random() < 0.4:
            bg.sparkle_stroke(sh, x, y, sh.rng.uniform(4, 8), WHITE, 210, 1.8)
        else:
            sh.wash(x, y, 2, 2, WHITE, alpha=210, layers=1, blur=0.6)
    # 화면 끝까지 완만하게 둥근 언덕 (아래 땅 띠를 덮는다)
    R = 1500
    hill = ellipse_points(640, 452 + R, R, R, 720, math.pi * 1.2, math.pi * 0.6)
    m = bg.poly_mask((W, H), hill + [(W, H), (0, H)])
    f = Sheet(W, H, seed=503)
    f.fill_poly([(0, 380), (W, 380), (W, H), (0, H)], (92, 76, 132), 255)
    for x in range(80, W, 220):
        f.wash(x, 560, 170, 110, PASTEL['lavender'], alpha=110, layers=2, blur=8)
    f.wash(640, 470, 260, 40, (255, 240, 200), alpha=70, layers=2, blur=8)
    sh.masked(f, m)
    sh.stroke(hill, 3.6, (230, 220, 245), 230, taper=False)
    sh.wash(640, 410, 190, 120, (255, 240, 200), alpha=60, layers=3, blur=12)   # 은은한 빛
    base.alpha_composite(sh.result())
    b = boy_line.draw_frame(boy_line.POSES[0], 700, 0)     # 준비 화면과 같은 주인공 (1:1)
    base.alpha_composite(b, (640 - b.width // 2 + 10, 452 - boy_line.FEET))
    t = Sheet(W, H, seed=502)
    f = pastel.hand_font(46)
    t.ink_text('여정을 준비하는 중', f, 642, 594, (34, 28, 60), 150, anchor='mm')
    t.ink_text('여정을 준비하는 중', f, 640, 590, pastel.NIGHT_TEXT, 255, anchor='mm')
    t.ink_text('여정을 준비하는 중', f, 640.8, 590, pastel.NIGHT_TEXT, 255, anchor='mm')
    base.alpha_composite(t.result())
    return base.convert('RGB')


# ================================================================ UI
def ink_icon(color):
    """잉크 양 표시용 작은 잉크병."""
    sh = Sheet(56, 64, seed=600 + sum(color))
    sh.line = PLUM
    body = [(12, 22), (10, 50), (16, 58), (40, 58), (46, 50), (44, 22)]
    sh.fill_poly(body, (255, 252, 248))
    sh.fill_poly([(12, 30), (10, 50), (16, 58), (40, 58), (46, 50), (44, 30)], color)
    sh.wash(20, 42, 4, 9, WHITE, alpha=120, layers=2, blur=1)
    sh.fill_poly([(19, 22), (20, 10), (36, 10), (37, 22)], (210, 170, 130))
    sh.stroke(body + [body[0]], 3.0, amp=0.3)
    sh.stroke([(19, 22), (20, 10), (36, 10), (37, 22)], 2.6, amp=0.2)
    return sh.result()


def hud():
    """잉크 양 쪽지 (왼쪽 위)."""
    w, h = 470, 112
    sh = Sheet(w, h, seed=610)
    sh.line = PLUM
    box = pastel.wobbly_box(14, 14, w - 14, h - 14, 20, sh.rng)
    p = Sheet(w, h, seed=611)
    p.fill_poly([(0, 0), (w, 0), (w, h), (0, h)], (255, 251, 246), 240)
    p.wash(90, 40, 120, 50, PASTEL['lemon'], alpha=80, layers=2, blur=8)
    p.wash(380, 80, 120, 50, PASTEL['sky'], alpha=80, layers=2, blur=8)
    sh.masked(p, pastel.poly_mask((w, h), box))
    sh.stroke(box, 3.6)
    return sh.result()


def toast():
    w, h = 520, 86
    sh = Sheet(w, h, seed=620)
    sh.line = PLUM
    box = pastel.wobbly_box(14, 14, w - 14, h - 14, 22, sh.rng)
    p = Sheet(w, h, seed=621)
    p.fill_poly([(0, 0), (w, 0), (w, h), (0, h)], (255, 251, 246), 245)
    p.wash(w / 2, h / 2, w / 2, h / 2, PASTEL['lavender'], alpha=90, layers=2, blur=8)
    sh.masked(p, pastel.poly_mask((w, h), box))
    sh.stroke(box, 3.6)
    return sh.result()


BUTTONS = (  # 파일 이름, 글씨, 색, 크기
    ('add_unit', '유닛 추가하기', 'pink', (250, 90)),
    ('mix', '잉크 섞기', 'mint', (250, 90)),
    ('units', '내 유닛', 'sky', (250, 90)),
    ('depart', '출발하기!', 'lemon', (250, 90)),
    ('back', '타이틀로', 'lavender', (180, 72)),
)


def main():
    save(sky(), 'sky.png')
    save(far(), 'far.png')
    save(mid(), 'mid.png')
    save(ground(), 'ground.png')
    for i in range(3):
        save(boy(i), f'boy_{i}.png')
    save(shadow(), 'shadow.png')
    save(loading(), 'loading.png')
    for name, col in (('black', INK_BLACK), ('red', (232, 104, 112)), ('green', (104, 192, 140)),
                      ('blue', (100, 150, 228))):
        save(ink_icon(col), f'ink_{name}.png')
    save(hud(), 'hud.png')
    save(toast(), 'toast.png')
    for i, (name, label, tint, size) in enumerate(BUTTONS):
        fs = 34 if size[0] > 200 else 30
        for hover in (False, True):
            save(pastel.button(label, PASTEL[tint], 700 + i, hover, size=size, font_size=fs),
                 f'button_{name}{"_hover" if hover else ""}.png')


if __name__ == '__main__':
    main()
