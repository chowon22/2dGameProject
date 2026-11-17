"""능력치를 한눈에: 막대 그래프 (유닛 그리기 화면 오른쪽) 와 한 줄 글씨 (카드 쪽지).

막대 한 줄 = 이름 · 막대 · 숫자. 롤 체력바처럼 칸 하나 = 정해진 양 (그 틀·체형의 기본 능력치로 정한 간격,
예: 체력 5, 공격력 1). 막대 끝은 기본의 두 배인데, 지금 값이 그보다 크면 막대가 꽉 찬 채로 끝이 늘어나
칸이 그만큼 작아진다 (칸이 촘촘할수록 세다). 굵은 눈금이 기본(검정 100) 자리. 숫자는 '지금 / 기본'.
칸이 너무 잘아지면(3px 아래) 열 칸마다 굵고 진한 금 하나만 긋는다.
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
BAR_H = 16
STEPS = (1, 2, 5, 10, 20, 50, 100, 200, 500)
MAX_SEGMENTS = 20
COLORS = {'hp': (232, 112, 124), 'atk': (240, 168, 80), 'buff': (110, 188, 140)}
LABELS = {'hp': '체력', 'atk': '공격력', 'buff': '버프'}
ELEMENT_INK = {v: k for k, v in stats.ELEMENT_OF.items()}   # 원소 → 잉크 색


def segment_step(top):
    """막대 끝 값 top 을 MAX_SEGMENTS 칸 안으로 나누는 깔끔한 간격 (1, 2, 5, 10 …)."""
    return next((s for s in STEPS if top / s <= MAX_SEGMENTS), STEPS[-1])


def _shade(color, k=0.72):
    return tuple(int(c * k) for c in color)


def _bar(x, y, w, frac, color, tick=None, step=None):  # step: 칸 하나의 폭 (막대 전체 = 1)
    """(x, y) 왼쪽 가운데부터 폭 w 막대. frac 0~1 만큼 채우고, 채운 곳은 step(0~1 비율)마다 금을 긋고,
    tick(0~1) 자리에 굵은 세로 눈금."""
    frac = max(0.0, min(1.0, frac))
    y1, y2 = y - BAR_H / 2, y + BAR_H / 2
    draw_rectangle(x, y1, x + w, y2, *TRACK, filled=True)
    if frac > 0:
        fx = x + 2 + (w - 4) * frac
        draw_rectangle(x + 2, y1 + 2, fx, y2 - 2, *color, filled=True)
        draw_rectangle(x + 2, y1 + 2, fx, y1 + 4, *_shade(color, 0.85), filled=True)   # 아래쪽 그늘
        big = False
        while step and (w - 4) * step < 3:   # 너무 촘촘하면 열 칸마다 굵은 금 하나 (롤의 큰 눈금처럼)
            step *= 10
            big = True
        if step:
            k, half, col = step, (1.0 if big else 0.5), _shade(color, 0.5 if big else 0.72)
            while k < frac - 1e-6:
                sx = x + 2 + (w - 4) * k
                draw_rectangle(sx - half, y1 + 2, sx + half, y2 - 2, *col, filled=True)
                k += step
    draw_rectangle(x, y1, x + w, y2, *INK, filled=False)
    if tick is not None:
        tx = x + w * tick
        draw_rectangle(tx - 1, y1 - 4, tx + 1, y2 + 4, *INK, filled=True)


def _num(v):
    return f'{v:g}'


def draw_bars(now, base, x, y, w=220, gap=40, label_w=58, show_buff=False):
    """now·base = stats.unit_stats 결과. (x, y) 는 첫 줄 이름의 왼쪽 가운데. 다음 줄 y 를 돌려준다."""
    keys = ('hp', 'atk') + (('buff',) if show_buff else ())
    bx = x + label_w
    for k in keys:
        text.draw(LABELS[k], x, y, 20, INK)
        cap = base[k] * 2 or 1
        top = max(cap, now[k])            # 넘치면 막대 끝이 늘어나 칸이 작아진다
        _bar(bx, y, w, now[k] / top, COLORS[k], tick=base[k] / top, step=segment_step(cap) / top)
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
        text.draw('없음', bx, y - 1, 18, SOFT)
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
