"""유닛 그리기 화면(draw_mode) 이미지 생성 → image/draw/

- panel: 화면을 덮는 커다란 수채화 종이 판
- paper: 그림을 그리는 흰 도화지 (가운데 PAPER_W x PAPER_H 가 실제로 칠하는 곳)
- card / card_on / card_empty: 프리셋(내가 그린 유닛) 카드
- guide_<id>: 종이에 깔리는 틀 밑그림 — 역할별 귀여운 생물(frames.py)을 삐뚤빼뚤한 연필 점선으로
- frame_<id> / frame_<id>_on: 틀 고르기 카드 (밑그림 + 이름)
- ink_wave: 고른 잉크 아래 구불구불한 밑줄 (형광펜처럼), eraser: 지우개
- tab_<all|틀 id> / _on: 내 유닛 화면의 프리셋 나누기 칸 (전체·탱커·근접 딜러·원거리 딜러·서포터)
- card_del / card_del_confirm: 프리셋 카드 모서리의 지우기 × (한 번 누르면 붉게 → 한 번 더 누르면 지움)
- button_save / button_clear / button_close / button_unequip (+ _hover)

실행: python tools/gen_draw.py
"""
import os
import sys

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


GUIDE_LINE = (150, 128, 170)
DASH, GAP = 13.0, 8.0


def _resample(points, step=2.0):
    out = [points[0]]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n + 1)]
    return out


def _dashes(points, keep=None):
    """선을 점선 조각들로. keep(x, y) 가 False 인 곳은 비운다."""
    pts = _resample(points)
    out, cur, run, on = [], [], 0.0, True
    for i, p in enumerate(pts):
        if i:
            run += math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1])
        if on and run > DASH:
            on, run = False, 0.0
        elif not on and run > GAP:
            on, run = True, 0.0
        if on and (keep is None or keep(*p)):
            cur.append(p)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [d for d in out if len(d) > 1]


def guide(frame, alpha=170, width=3.0, fill_alpha=22, color=GUIDE_LINE):
    """틀 밑그림: 부위들을 합친 바깥 윤곽 + 무늬를 연필 점선으로, 안은 아주 옅게."""
    w, h = frames.PAPER_W, frames.PAPER_H
    sh = Sheet(w, h, seed=1100 + frames.IDS.index(frame['id']))
    sh.line = color
    parts = frame['parts']
    masks = []
    for part in parts:
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).polygon(frames.outline(part), fill=255)
        masks.append(np.asarray(m.filter(ImageFilter.MinFilter(5))) > 0)   # 조금 줄인 안쪽
    union = np.asarray(Image.fromarray(((frames.part_mask(frame['id']) > 0) * 255).astype(np.uint8)))
    p = Sheet(w, h, seed=1)
    p.fill_poly([(0, 0), (w, 0), (w, h), (0, h)], color, fill_alpha)
    sh.masked(p, Image.fromarray(union))
    for i, part in enumerate(parts):
        others = [m for j, m in enumerate(masks) if j != i]

        def keep(x, y, others=others):
            xi, yi = min(w - 1, max(0, int(x))), min(h - 1, max(0, int(y)))
            return not any(m[yi, xi] for m in others)
        for d in _dashes(frames.outline(part), keep):
            sh.stroke(d, width, alpha=alpha, amp=0.4, taper=False)
    for det in frame['details']:
        if det[0] == 'dot':
            _, x, y, r = det
            sh.fill_poly(ellipse_points(x, y, r, r), color, alpha)
        else:
            for d in _dashes(list(det)):
                sh.stroke(d, width * 0.85, alpha=alpha, amp=0.3, taper=False)
    return sh.result()


def frame_card(frame, on):
    w, h = FRAME_CARD
    tint = {'tank': 'sky', 'melee': 'pink', 'ranged': 'peach', 'support': 'mint'}[frame['id']]
    img = note(w, h, 930 + frames.IDS.index(frame['id']) * 3 + on,
               ((w / 2, h / 2, w / 2, h / 2, PASTEL[tint], 150 if on else 60),), line=4.2 if on else 3.0, r=16)
    # 왼쪽에 작은 틀 실루엣
    g = guide(frame, alpha=255, width=6.0, fill_alpha=80 if on else 50, color=PLUM)
    g = g.crop(g.getbbox())
    k = min(62 / g.width, 64 / g.height)   # 아이콘 칸 62px, 나머지는 이름 칸
    icon = g.resize((round(g.width * k), round(g.height * k)), Image.LANCZOS)
    img.alpha_composite(icon, (16 + (62 - icon.width) // 2, (h - icon.height) // 2))
    sh = Sheet(w, h, seed=0, ss=1)
    sh.img = img
    sh.ink_text(frame['name'], ImageFont.truetype(os.path.join(pastel.FONTS, pastel.HAND), 22), 136, h / 2,
                PLUM, anchor='mm')
    return img


TAB = (138, 58)
TABS = (('all', '전체', 'lemon'), ('tank', '탱커', 'sky'), ('melee', '근접 딜러', 'pink'),
        ('ranged', '원거리 딜러', 'peach'), ('support', '서포터', 'mint'))


def tab(i, label, tint, on):
    w, h = TAB
    img = note(w, h, 1000 + i * 2 + on, ((w / 2, h / 2, w / 2, h / 2, PASTEL[tint], 170 if on else 45),),
               fill_alpha=250 if on else 170, line=3.8 if on else 2.6, r=16)
    sh = Sheet(w, h, seed=0, ss=1)
    sh.img = img
    sh.ink_text(label, ImageFont.truetype(os.path.join(pastel.FONTS, pastel.HAND), 24), w / 2, h / 2, PLUM,
                alpha=255 if on else 170, anchor='mm')
    return img


def card_del(confirm):
    sh = Sheet(34, 34, seed=990 + confirm)
    sh.line = PLUM
    ring = ellipse_points(17, 17, 13, 13)
    sh.fill_poly(ring, (238, 118, 128) if confirm else (255, 251, 246))
    if not confirm:
        sh.wash(17, 17, 10, 10, PASTEL['pink'], alpha=120, layers=2, blur=2)
    sh.stroke(ring, 2.6, amp=0.4)
    x_col = WHITE if confirm else PLUM
    sh.stroke([(11, 11), (23, 23)], 3.0, color=x_col, amp=0.3)
    sh.stroke([(23, 11), (11, 23)], 3.0, color=x_col, amp=0.3)
    return sh.result()


def ink_wave():
    w, h = 76, 22
    sh = Sheet(w, h, seed=951)
    pts = [(8 + (w - 16) * i / 40, h / 2 + 4.2 * math.sin(i / 40 * math.pi * 3)) for i in range(41)]
    sh.stroke(pts, 7.0, color=(246, 206, 92), alpha=210, amp=0.3, taper=False)      # 노란 형광펜
    sh.stroke(pts, 2.4, color=(214, 160, 52), alpha=200, amp=0.3)                   # 가운데 진한 선
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
    ('unequip', '다 빼기', 'peach', (190, 80)),     # 내 유닛 화면
)


def main():
    save(panel(), 'panel.png')
    save(paper(), 'paper.png')
    for state in ('off', 'on', 'empty'):
        save(card(state), {'off': 'card.png', 'on': 'card_on.png', 'empty': 'card_empty.png'}[state])
    for f in frames.FRAMES:
        save(guide(f), f'guide_{f["id"]}.png')
        for on in (False, True):
            save(frame_card(f, on), f'frame_{f["id"]}{"_on" if on else ""}.png')
    for i, (tid, label, tint) in enumerate(TABS):
        for on in (False, True):
            save(tab(i, label, tint, on), f'tab_{tid}{"_on" if on else ""}.png')
    save(card_del(False), 'card_del.png')
    save(card_del(True), 'card_del_confirm.png')
    save(ink_wave(), 'ink_wave.png')
    save(eraser(), 'eraser.png')
    for i, (name, label, tint, size) in enumerate(BUTTONS):
        for hover in (False, True):
            save(pastel.button(label, PASTEL[tint], 970 + i, hover, size=size, font_size=32),
                 f'button_{name}{"_hover" if hover else ""}.png')


if __name__ == '__main__':
    main()
