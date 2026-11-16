"""유닛 그리기 화면(draw_mode) 이미지 생성 → image/draw/

- panel: 화면을 덮는 커다란 수채화 종이 판
- paper: 그림을 그리는 흰 도화지 (가운데 PAPER_W x PAPER_H 가 실제로 칠하는 곳)
- card / card_on / card_empty: 프리셋(내가 그린 유닛) 카드
- frame_<id> / frame_<id>_on: 틀 고르기 카드 (틀 실루엣 + 이름)
- ink_ring: 고른 잉크 아래 동그라미, eraser: 지우개
- button_save / button_clear / button_close (+ _hover)

실행: python tools/gen_draw.py
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gen_title_pastel as pastel  # noqa: E402
from sketch import Sheet, ellipse_points, PASTEL, PLUM  # noqa: E402
import frames  # noqa: E402

ROOT = pastel.ROOT
OUT = os.path.join(ROOT, 'image', 'draw')
WHITE = (255, 255, 255)
PAPER_MARGIN = 16
CARD = (112, 92)
FRAME_CARD = (204, 96)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved draw/' + name, img.size)


def note(w, h, seed, tints, fill=(255, 251, 246), fill_alpha=240, line=3.6, r=22):
    """손으로 그린 둥근 네모 쪽지에 물감 얼룩 몇 개."""
    sh = Sheet(w, h, seed=seed)
    sh.line = PLUM
    box = pastel.wobbly_box(12, 12, w - 12, h - 12, r, sh.rng)
    p = Sheet(w, h, seed=seed + 1)
    p.fill_poly([(0, 0), (w, 0), (w, h), (0, h)], fill, fill_alpha)
    for cx, cy, rx, ry, tint, a in tints:
        p.wash(cx, cy, rx, ry, tint, alpha=a, layers=2, blur=10)
    sh.masked(p, pastel.poly_mask((w, h), box))
    sh.stroke(box, line)
    return sh.result()


def panel():
    w, h = 1240, 700
    return note(w, h, 900, ((200, 140, 260, 160, PASTEL['lemon'], 70), (1050, 560, 280, 170, PASTEL['sky'], 70),
                            (1080, 120, 200, 120, PASTEL['pink'], 50), (160, 600, 200, 120, PASTEL['mint'], 50)),
                fill_alpha=236, line=4.0, r=30)


def paper():
    w, h = frames.PAPER_W + PAPER_MARGIN * 2, frames.PAPER_H + PAPER_MARGIN * 2
    sh = Sheet(w, h, seed=910)
    sh.line = PLUM
    # 살짝 기운 그림자 → 흰 도화지
    shadow = pastel.wobbly_box(10, 14, w - 4, h - 2, 10, sh.rng, amp=1.0)
    sh.fill_poly(shadow, (150, 128, 170), 60)
    box = pastel.wobbly_box(6, 6, w - 8, h - 10, 8, sh.rng, amp=1.0)
    sh.fill_poly(box, (255, 254, 251), 255)
    sh.stroke(box, 3.0, amp=0.6)
    return sh.result()


def card(state):
    w, h = CARD
    if state == 'empty':
        sh = Sheet(w, h, seed=920)
        sh.line = PLUM
        box = pastel.wobbly_box(10, 10, w - 10, h - 10, 14, sh.rng)
        sh.fill_poly(box, (255, 251, 246), 110)
        for i in range(0, len(box) - 1, 2):   # 점선 테두리
            sh.stroke([box[i], box[i + 1]], 2.2, alpha=150, amp=0.2, taper=False)
        return sh.result()
    tint = PASTEL['lemon'] if state == 'on' else PASTEL['lavender']
    return note(w, h, 921 if state == 'on' else 922, ((w / 2, h / 2, w / 2, h / 2, tint, 120 if state == 'on' else 60),),
                line=4.2 if state == 'on' else 3.0, r=14)


def frame_card(frame, on):
    w, h = FRAME_CARD
    tint = {'tank': 'sky', 'melee': 'pink', 'ranged': 'peach', 'support': 'mint'}[frame['id']]
    img = note(w, h, 930 + frames.IDS.index(frame['id']) * 3 + on,
               ((w / 2, h / 2, w / 2, h / 2, PASTEL[tint], 150 if on else 60),), line=4.2 if on else 3.0, r=16)
    # 왼쪽에 작은 틀 실루엣
    sil = frames.silhouette(frame['id'], (190, 98), color=PLUM, fill_alpha=90 if on else 60, line_alpha=230)
    icon = Image.fromarray(sil, 'RGBA').crop((28, 0, 166, 98)).resize((76, 54), Image.LANCZOS)
    img.alpha_composite(icon, (14, (h - 54) // 2))
    sh = Sheet(w, h, seed=0, ss=1)
    sh.img = img
    sh.ink_text(frame['name'], ImageFont.truetype(os.path.join(pastel.FONTS, pastel.HAND), 24), 150, h / 2,
                PLUM, anchor='mm')
    return img


def ink_ring():
    sh = Sheet(84, 40, seed=950)
    sh.line = PLUM
    sh.wash(42, 20, 34, 12, PASTEL['lemon'], alpha=200, layers=3, blur=3)
    sh.stroke(ellipse_points(42, 20, 34, 12), 2.6, amp=0.6)
    return sh.result()


def eraser():
    sh = Sheet(64, 64, seed=960)
    sh.line = PLUM
    body = [(10, 40), (34, 14), (54, 30), (30, 56)]
    sh.fill_poly(body, (255, 214, 222))
    sh.fill_poly([(10, 40), (22, 27), (42, 43), (30, 56)], (150, 190, 236))
    sh.stroke(body + [body[0]], 3.0, amp=0.3)
    sh.stroke([(22, 27), (42, 43)], 2.4, amp=0.2)
    return sh.result()


BUTTONS = (  # 파일 이름, 글씨, 색, 크기
    ('save', '저장하기', 'lemon', (190, 80)),
    ('clear', '다 지우기', 'pink', (190, 80)),
    ('close', '닫기', 'lavender', (190, 80)),
)


def main():
    save(panel(), 'panel.png')
    save(paper(), 'paper.png')
    for state in ('off', 'on', 'empty'):
        save(card(state), {'off': 'card.png', 'on': 'card_on.png', 'empty': 'card_empty.png'}[state])
    for f in frames.FRAMES:
        for on in (False, True):
            save(frame_card(f, on), f'frame_{f["id"]}{"_on" if on else ""}.png')
    save(ink_ring(), 'ink_ring.png')
    save(eraser(), 'eraser.png')
    for i, (name, label, tint, size) in enumerate(BUTTONS):
        for hover in (False, True):
            save(pastel.button(label, PASTEL[tint], 970 + i, hover, size=size, font_size=32),
                 f'button_{name}{"_hover" if hover else ""}.png')


if __name__ == '__main__':
    main()
