"""월드 고르기·스테이지·전투 화면 이미지 생성 → image/world/

- world_<n> / world_<n>_hover / world_<n>_locked: 월드 카드 (큰 번호 + 이름)
- stage / stage_hover / stage_clear / stage_locked / stage_boss (+ _hover): 스테이지 동그라미 (번호는 실행 중에 쓴다)
- result: 승리·패배 쪽지
- button_start / back / skip / flee / return (+ _hover)

실행: python tools/gen_world.py
"""
import math
import os
import sys

from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gen_draw as gd  # noqa: E402
import gen_title_pastel as pastel  # noqa: E402
from sketch import Sheet, ellipse_points, PASTEL, PLUM  # noqa: E402
import stages  # noqa: E402

OUT = os.path.join(pastel.ROOT, 'image', 'world')
CARD = (230, 150)
TINTS = ('lavender', 'pink', 'mint', 'sky', 'lemon', 'peach', 'sky', 'pink')
GRAY = (196, 192, 202)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved world/' + name, img.size)


def font(size):
    return ImageFont.truetype(os.path.join(pastel.FONTS, pastel.HAND), size)


def world_card(w, state):
    """state: 'off' / 'hover' / 'locked'."""
    cw, ch = CARD
    tint = GRAY if state == 'locked' else PASTEL[TINTS[w['id']]]
    img = gd.note(cw, ch, 1300 + w['id'] * 3 + ('off', 'hover', 'locked').index(state),
                  ((cw / 2, ch / 2, cw / 2, ch / 2, tint, 170 if state == 'hover' else 90),),
                  fill_alpha=250 if state != 'locked' else 200, line=4.2 if state == 'hover' else 3.2, r=20)
    sh = Sheet(cw, ch, seed=0, ss=1)
    sh.img = img
    col = (150, 144, 158) if state == 'locked' else PLUM
    sh.ink_text(str(w['id']), font(58), cw / 2, ch / 2 - 18, col, anchor='mm')
    sh.ink_text(w['name'] if state != 'locked' else '잠겨 있어요', font(24), cw / 2, ch / 2 + 34, col, anchor='mm')
    return img


def stage_node(kind, hover):
    """kind: 'open' / 'clear' / 'locked' / 'boss'."""
    s = 104 if kind == 'boss' else 92
    sh = Sheet(s, s, seed=1400 + len(kind) + hover)
    sh.line = PLUM
    r = s / 2 - 10
    ring = ellipse_points(s / 2, s / 2, r, r)
    fill = {'open': (255, 251, 246), 'clear': (255, 246, 214), 'locked': (226, 223, 230), 'boss': (255, 236, 236)}[kind]
    sh.fill_poly(ring, fill, 250)
    tint = {'open': PASTEL['sky'], 'clear': PASTEL['lemon'], 'locked': GRAY, 'boss': PASTEL['pink']}[kind]
    sh.wash(s / 2, s / 2, r * 0.8, r * 0.8, tint, alpha=200 if hover else 120, layers=2, blur=3)
    sh.stroke(ring, 4.2 if hover else 3.2, amp=0.5, color=(150, 144, 158) if kind == 'locked' else PLUM)
    if kind == 'boss':   # 뿔 두 개
        for dx in (-1, 1):
            sh.stroke([(s / 2 + dx * 18, 16), (s / 2 + dx * 26, 2), (s / 2 + dx * 30, 18)], 3.0, amp=0.3)
    if kind == 'clear':  # 작은 별
        star = [(s - 22 + 9 * math.cos(math.radians(-90 + 36 * i)) * (1 if i % 2 == 0 else 0.45),
                 20 + 9 * math.sin(math.radians(-90 + 36 * i)) * (1 if i % 2 == 0 else 0.45)) for i in range(10)]
        sh.fill_poly(star, (246, 206, 92))
        sh.stroke(star + [star[0]], 2.0, amp=0.2)
    return sh.result()


def result_note():
    w, h = 600, 300
    return gd.note(w, h, 1450, ((w / 2, h / 2, w / 2, h / 2, PASTEL['lemon'], 80),
                                (120, 80, 140, 80, PASTEL['pink'], 60), (480, 220, 140, 80, PASTEL['sky'], 60)),
                   fill_alpha=248, line=4.0, r=26)


BUTTONS = (
    ('start', '시작!', 'lemon', (200, 84), 36),
    ('back', '뒤로', 'lavender', (160, 70), 30),
    ('skip', '넘기기', 'mint', (170, 72), 30),
    ('flee', '도망가기', 'pink', (180, 72), 30),
    ('return', '돌아가기', 'sky', (200, 80), 32),
)


def main():
    for w in stages.worlds():
        for state in ('off', 'hover', 'locked'):
            suffix = {'off': '', 'hover': '_hover', 'locked': '_locked'}[state]
            save(world_card(w, state), f'world_{w["id"]}{suffix}.png')
    for kind in ('open', 'clear', 'locked', 'boss'):
        for hover in (False, True):
            save(stage_node(kind, hover), f'stage_{kind}{"_hover" if hover else ""}.png')
    save(result_note(), 'result.png')
    for i, (name, label, tint, size, fs) in enumerate(BUTTONS):
        for hover in (False, True):
            save(pastel.button(label, PASTEL[tint], 1500 + i, hover, size=size, font_size=fs),
                 f'button_{name}{"_hover" if hover else ""}.png')


if __name__ == '__main__':
    main()
