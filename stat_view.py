"""능력치를 한눈에: 막대 그래프 (유닛 그리기 화면 오른쪽) 와 한 줄 글씨 (카드 쪽지).

막대 한 줄 = 이름 · 막대 · 숫자. 막대는 기본 능력치(검정 100) 의 두 배까지 채워지고,
가운데 세로 눈금이 기본 자리 (눈금을 넘으면 기본보다 세다). 숫자는 '지금 / 기본'.
원소 줄은 가장 많이 칠한 색의 잉크병 + 원소 이름 + 상성 세기 막대 (stats.strength, 칠할수록 세다).
open_canvas() 뒤에만 쓸 수 있다.
"""
from pico2d import draw_rectangle

import painter
import stats
import text
from assets import image

INK = (86, 68, 106)
SOFT = (150, 128, 170)
TRACK = (240, 234, 244)
BAR_H = 14
COLORS = {'hp': (232, 112, 124), 'atk': (240, 168, 80), 'buff': (110, 188, 140)}
LABELS = {'hp': '체력', 'atk': '공격력', 'buff': '버프'}
ELEMENT_INK = {v: k for k, v in stats.ELEMENT_OF.items()}   # 원소 → 잉크 색


def _bar(x, y, w, frac, color, tick=None):
    """(x, y) 왼쪽 가운데부터 폭 w 막대. frac 0~1 만큼 채우고 tick(0~1) 자리에 세로 눈금."""
    frac = max(0.0, min(1.0, frac))
    y1, y2 = y - BAR_H / 2, y + BAR_H / 2
    draw_rectangle(x, y1, x + w, y2, *TRACK, filled=True)
    if frac > 0:
        draw_rectangle(x + 2, y1 + 2, x + 2 + (w - 4) * frac, y2 - 2, *color, filled=True)
    draw_rectangle(x, y1, x + w, y2, *INK, filled=False)
    if tick is not None:
        tx = x + w * tick
        draw_rectangle(tx - 1, y1 - 4, tx + 1, y2 + 4, *INK, filled=True)


def _num(v):
    return f'{v:g}'


def draw_bars(now, base, x, y, w=220, gap=30, label_w=58, show_buff=False):
    """now·base = stats.unit_stats 결과. (x, y) 는 첫 줄 이름의 왼쪽 가운데. 다음 줄 y 를 돌려준다."""
    keys = ('hp', 'atk') + (('buff',) if show_buff else ())
    bx = x + label_w
    for k in keys:
        text.draw(LABELS[k], x, y, 20, INK)
        top = base[k] * 2 or 1
        _bar(bx, y, w, now[k] / top, COLORS[k], tick=0.5)
        text.draw(f'{_num(now[k])} / {_num(base[k])}', bx + w + 10, y - 1, 18, SOFT)
        y -= gap
    text.draw('원소', x, y, 20, INK)
    el = now.get('element')
    if el:
        c = ELEMENT_INK[el]
        image('prepare', f'ink_{c}.png').draw(bx + 8, y, 16, 19)
        text.draw(stats.ELEMENT_NAMES[el], bx + 22, y - 1, 20, INK)
        _bar(bx + 50, y, w - 50, now.get('strength', 0), painter.RGB[c])
        text.draw(f'{round(now.get("strength", 0) * 100)}%', bx + w + 10, y - 1, 18, SOFT)
    else:
        text.draw('없음  (색을 칠하면 생겨요)', bx, y - 1, 18, SOFT)
    return y - gap


def tip_line(unit):
    """카드 쪽지용 한 줄: '체력 80 · 공격력 8 · 불'."""
    st = stats.unit_stats(unit)
    parts = [f'체력 {st["hp"]}', f'공격력 {_num(st["atk"])}']
    if st['role'] == 'support':
        parts.append(f'버프 {_num(st["buff"])}')
    if st['element']:
        parts.append(stats.ELEMENT_NAMES[st['element']])
    return '  ·  '.join(parts)
