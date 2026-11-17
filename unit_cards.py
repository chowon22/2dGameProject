"""그린 유닛(프리셋) 카드 한 장 그리기. 유닛 그리기 화면과 내 유닛 화면이 함께 쓴다.

카드 = 쪽지 + 무기를 손에 쥔 그림(unit_art.compose)을 잘라 줄인 썸네일 + 체형·틀 이름.
드는 잉크는 카드에 마우스를 올렸을 때만 카드 아래 쪽지로 보인다 (draw_tip) — 색이 많아져도 잘리지 않게.
draw_mark: 유닛 발밑 등에 붙이는 역할 마크 (탱커 방패 / 근딜 칼 / 원딜 활 / 서포터 치료 십자, tools/gen_marks.py).
카드에 마우스를 올리면 오른쪽 위 모서리에 지우기 × 도 뜬다. 한 번 누르면 붉게 바뀌고, 한 번 더 누르면 지운다 (Deleter).
open_canvas() 뒤에만 쓸 수 있다.
"""
import numpy as np
from PIL import Image as PILImage

import frames
import save_data
import unit_art
import text
from assets import image
from live_image import LiveImage

INK = (86, 68, 106)
CARD_W, CARD_H = 112, 92
THUMB_W, THUMB_H = 84, 42       # 카드 안 그림 칸 (아래 이름 칸 위)
NAMES = {'black': '검정', 'red': '빨강', 'green': '초록', 'blue': '파랑'}
DEL_DX, DEL_DY, DEL_R = 48, 38, 16   # 지우기 × 자리 (카드 가운데에서), 누르는 반지름

_thumbs = {}                    # (슬롯, 유닛 id, 크기) → 썸네일 (없으면 None)


def make_thumb(unit, max_w=THUMB_W, max_h=THUMB_H, scale=None):
    """무기를 손에 쥔 그림을 max_w x max_h 안에 맞게 줄인 것."""
    arr = unit_art.compose(unit, *unit_art.load(save_data.current['slot'], unit))
    if arr is None:
        return None
    img = PILImage.fromarray(arr, 'RGBA')
    k = scale if scale else min(max_w / img.width, max_h / img.height, 1.0)   # scale: 체형 크기 차이가 보이게 같은 배율로
    img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), PILImage.LANCZOS)
    return LiveImage(img.width, img.height, np.asarray(img))


def thumb(unit, size=(THUMB_W, THUMB_H), scale=None):
    """카드 썸네일. size 를 바꾸면 필드 미리보기용처럼 다른 크기로 (크기마다 따로 만들어 둔다)."""
    key = (save_data.current['slot'], unit['id'], size, scale)
    if key not in _thumbs:
        _thumbs[key] = make_thumb(unit, *size, scale=scale)
    return _thumbs[key]


def forget(unit_id):
    """지운 유닛의 썸네일을 버린다 (같은 id 가 다시 쓰일 수 있다)."""
    for key in [k for k in _thumbs if k[:2] == (save_data.current['slot'], unit_id)]:
        del _thumbs[key]


def cost(unit):
    return sum(unit.get('ink', {}).values())


def label(unit):
    """카드 아래 이름: 체형 + 틀 (예: '큰 탱커')."""
    if unit.get('frame') not in frames.IDS:
        return ''
    body = unit.get('body', 'medium')
    if body == 'medium':
        return frames.get(unit['frame'])['name']
    return f'{frames.BODY_NAMES.get(body, "")} {frames.SHORT_NAMES[unit["frame"]]}'   # 좁은 카드라 줄인 이름


def draw_tip(unit_id, cards):
    """마우스를 올린 카드 아래에 드는 잉크 쪽지 (다른 카드보다 위에 그리도록 카드를 다 그린 뒤 부른다)."""
    for unit, x, y in cards:
        if unit['id'] != unit_id:
            continue
        ink = {c: n for c, n in unit.get('ink', {}).items() if n}
        msg = '  ·  '.join(f'{NAMES.get(c, c)} {n}' for c, n in ink.items()) or '잉크 0'
        w = max(120, 14 * len(msg) + 40)
        note = image('prepare', 'toast.png')
        tx, ty = x, y - CARD_H / 2 - 18   # 카드 바로 아래
        note.draw(tx, ty, w, 50)
        text.draw(msg, tx, ty + 1, 20, INK, 'c')
        return


def hit(x, y, mx, my):
    return abs(mx - x) <= CARD_W / 2 - 6 and abs(my - y) <= CARD_H / 2 - 6


def _draw(img, x, y, alpha, w=None, h=None):
    if alpha < 1:
        img.opacify(alpha)
    img.draw(x, y, w, h) if w else img.draw(x, y)
    if alpha < 1:
        img.opacify(1)


def draw_mark(unit, x, y, size=24, alpha=1.0):
    """유닛(또는 역할 id) 의 역할 마크를 (x, y) 가운데에 size 크기로."""
    role = unit if isinstance(unit, str) else unit.get('frame')
    if role in frames.IDS:
        _draw(image('common', f'mark_{role}.png'), x, y, alpha, size, size)


def draw_empty(x, y, alpha=1.0):
    _draw(image('draw', 'card_empty.png'), x, y, alpha)


def hit_delete(x, y, mx, my):
    return (mx - x - DEL_DX) ** 2 + (my - y - DEL_DY) ** 2 <= DEL_R ** 2


def draw(unit, x, y, on=False, alpha=1.0, delete=None):
    """카드 한 장. on: 노란 쪽지(고름), alpha < 1: 흐리게(고를 수 없음),
    delete: None / 'show'(지우기 × ) / 'confirm'(붉은 × — 한 번 더 누르면 지움)."""
    _draw(image('draw', 'card_on.png' if on else 'card.png'), x, y, alpha)
    img = thumb(unit)
    if img:
        _draw(img, x, y + 9, alpha)
    text.draw(label(unit), x, y - 21, 15, INK, 'c', alpha=alpha)   # 쪽지 테두리(가운데에서 34px) 안쪽
    if delete:
        image('draw', 'card_del_confirm.png' if delete == 'confirm' else 'card_del.png').draw(x + DEL_DX, y + DEL_DY)


class Deleter:
    """프리셋 카드 지우기: 마우스를 올린 카드에 × 를 보이고, 두 번 눌러 지운다.
    cards 는 지금 보이는 [(유닛, x, y)]."""

    def __init__(self):
        self.hover = self.confirm = None

    def move(self, cards, mx, my):
        self.hover = None
        for unit, x, y in cards:
            if hit(x, y, mx, my) or hit_delete(x, y, mx, my):
                self.hover = unit['id']

    def state(self, unit):
        if unit['id'] == self.confirm:
            return 'confirm'
        return 'show' if unit['id'] == self.hover else None

    def click(self, cards, mx, my):
        """× 를 눌렀으면 'asked'(확인 대기) 또는 지운 유닛 id, 아니면 None (확인은 취소된다)."""
        for unit, x, y in cards:
            if self.state(unit) and hit_delete(x, y, mx, my):
                if self.confirm == unit['id']:
                    self.confirm = None
                    save_data.delete_unit(save_data.current, unit['id'])
                    forget(unit['id'])
                    save_data.save_current()
                    return unit['id']
                self.confirm = unit['id']
                return 'asked'
        self.confirm = None
        return None
