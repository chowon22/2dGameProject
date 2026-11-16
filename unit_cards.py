"""그린 유닛(프리셋) 카드 한 장 그리기. 유닛 그리기 화면과 내 유닛 화면이 함께 쓴다.

카드 = 쪽지 + 그린 부분만 잘라 줄인 썸네일(오른쪽) + 틀 이름 + 왼쪽 세로 칸에 잉크병과 이 유닛에 드는 잉크.
카드에 마우스를 올리면 오른쪽 위 모서리에 지우기 × 가 뜬다. 한 번 누르면 붉게 바뀌고, 한 번 더 누르면 지운다 (Deleter).
open_canvas() 뒤에만 쓸 수 있다.
"""
import numpy as np
from PIL import Image as PILImage

import frames
import save_data
import text
from assets import image
from live_image import LiveImage

INK = (86, 68, 106)
CARD_W, CARD_H = 112, 92
THUMB_W, THUMB_H = 58, 38       # 카드 안 그림 칸 (왼쪽 잉크 칸 옆, 아래 이름 칸 위)
DEL_DX, DEL_DY, DEL_R = 48, 38, 16   # 지우기 × 자리 (카드 가운데에서), 누르는 반지름

_thumbs = {}                    # (슬롯, 유닛 id) → 썸네일 (없으면 None)


def make_thumb(path):
    """그린 부분만 잘라 카드 칸에 맞게 줄인 썸네일."""
    img = PILImage.open(path).convert('RGBA')
    box = img.getbbox()
    if not box:
        return None
    img = img.crop(box)
    k = min(THUMB_W / img.width, THUMB_H / img.height, 1.0)
    img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), PILImage.LANCZOS)
    return LiveImage(img.width, img.height, np.asarray(img))


def thumb(unit):
    key = (save_data.current['slot'], unit['id'])
    if key not in _thumbs:
        try:
            _thumbs[key] = make_thumb(save_data.unit_path(*key))
        except OSError:
            _thumbs[key] = None
    return _thumbs[key]


def forget(unit_id):
    """지운 유닛의 썸네일을 버린다 (같은 id 가 다시 쓰일 수 있다)."""
    _thumbs.pop((save_data.current['slot'], unit_id), None)


def cost(unit):
    return sum(unit.get('ink', {}).values())


def hit(x, y, mx, my):
    return abs(mx - x) <= CARD_W / 2 - 6 and abs(my - y) <= CARD_H / 2 - 6


def _draw(img, x, y, alpha, w=None, h=None):
    if alpha < 1:
        img.opacify(alpha)
    img.draw(x, y, w, h) if w else img.draw(x, y)
    if alpha < 1:
        img.opacify(1)


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
        _draw(img, x + 13, y + 11, alpha)
    name = frames.get(unit['frame'])['name'] if unit.get('frame') in frames.IDS else ''
    text.draw(name, x, y - 21, 15, INK, 'c', alpha=alpha)   # 쪽지 테두리(가운데에서 34px) 안쪽
    ink = unit.get('ink') or {'black': 0}
    main = max(ink, key=ink.get)   # 가장 많이 드는 색의 잉크병
    _draw(image('prepare', f'ink_{main}.png'), x - 31, y + 19, alpha, 14, 16)
    text.draw(str(cost(unit)), x - 31, y + 2, 15, INK, 'c', alpha=alpha)
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
