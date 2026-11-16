"""그린 유닛(프리셋) 카드 한 장 그리기. 유닛 그리기 화면과 내 유닛 화면이 함께 쓴다.

카드 = 쪽지 + 그린 부분만 잘라 줄인 썸네일(오른쪽) + 틀 이름 + 왼쪽 세로 칸에 잉크병과 이 유닛에 드는 잉크.
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
THUMB_W, THUMB_H = 64, 48       # 카드 안 그림 칸 (왼쪽 잉크 칸 옆)

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


def draw(unit, x, y, on=False, alpha=1.0):
    """카드 한 장. on: 노란 쪽지(고름), alpha < 1: 흐리게(고를 수 없음)."""
    _draw(image('draw', 'card_on.png' if on else 'card.png'), x, y, alpha)
    img = thumb(unit)
    if img:
        _draw(img, x + 12, y + 8, alpha)
    name = frames.get(unit['frame'])['name'] if unit.get('frame') in frames.IDS else ''
    text.draw(name, x, y - 27, 17, INK, 'c', alpha=alpha)
    _draw(image('prepare', 'ink_black.png'), x - 34, y + 22, alpha, 16, 18)
    text.draw(str(cost(unit)), x - 34, y + 2, 16, INK, 'c', alpha=alpha)
