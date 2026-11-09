"""세이브 파일 선택 화면 이미지 (image/save/*.png). 파스텔 설정 창과 같은 수채화 종이 쪽지 그림체.

- panel.png: '세이브 파일' 제목이 적힌 창 (슬롯 내용 글씨는 실행 중에 쓴다)
- slot_<n>.png / slot_<n>_hover.png: 슬롯 카드 세 장 (분홍·민트·하늘)
- button_delete*.png: 지우기 / 한 번 더 누르면 지워지는 확인 상태
- button_close*.png: 닫기

위치는 save_select_mode 의 SLOT_Y·CLOSE_Y 와 맞춘다.

실행:  python tools/gen_save_select.py
"""
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import gen_title_pastel as pastel  # noqa: E402
from sketch import Sheet, bezier, PASTEL, PLUM  # noqa: E402

ROOT = pastel.ROOT
OUT = os.path.join(ROOT, 'image', 'save')
PANEL_W, PANEL_H = 820, 600
CARD_SIZE = (700, 124)
SLOT_TINTS = ('pink', 'mint', 'sky')


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name))
    print('saved save/' + name, img.size)


def panel():
    """설정 창과 같은 크림색 종이 + 파스텔 번짐 + 펜 테두리 두 줄, 위에 손글씨 제목."""
    sh = Sheet(PANEL_W, PANEL_H, seed=801)
    sh.line = PLUM
    box = (26, 26, PANEL_W - 26, PANEL_H - 26)
    outline = pastel.wobbly_box(*box, 28, sh.rng)
    shadow = Sheet(PANEL_W, PANEL_H, seed=802)
    shadow.fill_poly([(x + 6, y + 8) for x, y in outline], (120, 96, 150), 90)
    sh.img.alpha_composite(shadow.img.filter(ImageFilter.GaussianBlur(8 * sh.ss)))
    paper_ = Sheet(PANEL_W, PANEL_H, seed=803)
    paper_.fill_poly([(0, 0), (PANEL_W, 0), (PANEL_W, PANEL_H), (0, PANEL_H)], (255, 251, 246), 250)
    paper_.wash(160, 110, 220, 120, PASTEL['pink'], alpha=100, layers=3, blur=10)
    paper_.wash(680, 500, 240, 140, PASTEL['sky'], alpha=100, layers=3, blur=10)
    paper_.wash(700, 120, 140, 90, PASTEL['lemon'], alpha=90, layers=3, blur=10)
    paper_.wash(130, 510, 150, 90, PASTEL['mint'], alpha=90, layers=3, blur=10)
    sh.masked(paper_, pastel.poly_mask((PANEL_W, PANEL_H), outline))
    sh.stroke(outline, 4.4)
    sh.stroke(pastel.wobbly_box(box[0] + 12, box[1] + 12, box[2] - 12, box[3] - 12, 20, sh.rng), 1.8,
              pastel.SOFT_PLUM, 170, amp=0.8)
    f = pastel.hand_font(50)
    cx = PANEL_W / 2
    sh.ink_text('세이브 파일', f, cx + 2, 78, (255, 255, 255), 230, anchor='mm')
    pastel.thick_text(sh, '세이브 파일', f, cx, 76, PLUM)
    sh.stroke(bezier((cx - 92, 106), (cx - 30, 100), (cx + 30, 110), (cx + 92, 103)), 3, PLUM)
    pastel.sparkle_stroke(sh, cx + 118, 60, 10, (255, 222, 120), 255, 2.8)
    pastel.sparkle_stroke(sh, cx - 120, 88, 6, (255, 222, 120), 255, 2.2)
    return sh.result()


def main():
    save(panel(), 'panel.png')
    for i, tint in enumerate(SLOT_TINTS):
        for hover in (False, True):
            img = pastel.button('', PASTEL[tint], 811 + i, hover, size=CARD_SIZE)
            save(img, f'slot_{i + 1}{"_hover" if hover else ""}.png')
    for hover in (False, True):
        sfx = '_hover' if hover else ''
        save(pastel.button('지우기', PASTEL['peach'], 821, hover, size=(150, 70), font_size=28),
             f'button_delete{sfx}.png')
        save(pastel.button('정말 지울까요?', (240, 150, 150), 822, hover, size=(210, 70), font_size=26),
             f'button_delete_confirm{sfx}.png')
        save(pastel.button('닫기', PASTEL['lavender'], 823, hover, size=(220, 84)), f'button_close{sfx}.png')


if __name__ == '__main__':
    main()
