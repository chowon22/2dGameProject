"""준비 화면에서 내 유닛(필드에 놓은 유닛)이 소년 뒤를 따라 걷는 모습.

내 유닛 화면의 자리 그대로: 앞줄이 소년 가까이, 뒷줄이 그 뒤. 줄(먼 쪽 ~ 가까운 쪽)마다 조금 위아래·비스듬히.
그린 그림을 몸과 무기로 나눠(unit_rig) 무기는 손에 쥐고, 자리마다 박자를 달리해 통통 튀며 걷는다.
걸음에 맞춰 무기를 쥔 손을 축으로 흔든다 (칼은 크게, 방패는 조금).
"""
import math

import save_data
import unit_rig

FRONT_GAP, BACK_GAP = 140, 270      # 소년 x 에서 앞줄·뒷줄까지 (왼쪽으로)
LANE_DY = (16, 0, -16)              # 줄(먼 쪽 → 가까운 쪽)마다 발 높이
LANE_DX = (34, 0, -34)
SCALE = 0.25                        # 걷는 그림 배율 (체형마다 크기가 다르게 보이도록 모두 같은 배율)
STEP = 6.5                          # 걸음 박자 (라디안/초)
SWAY = {'tank': 0.06, 'melee': 0.22, 'ranged': 0.08, 'support': 0.14}   # 무기 흔드는 폭 (라디안)


def slot_pos(slot, boy_x, ground):
    lane = slot % 3
    gap = FRONT_GAP if slot < 3 else BACK_GAP
    return boy_x - gap + LANE_DX[lane], ground + LANE_DY[lane]


def draw(t, boy_x, ground, shadow=None):
    """boy_x: 소년이 지금 있는 x, ground: 발이 닿는 y."""
    data = save_data.current
    if not data:
        return
    # 먼 줄부터 그려야 가까운 줄이 앞에 온다
    for slot in sorted(range(save_data.PARTY_MAX), key=lambda s: s % 3):
        unit_id = data['party'][slot]
        unit = save_data.find_unit(data, unit_id) if unit_id is not None else None
        r = unit_rig.rig(unit, SCALE) if unit else None
        if not r:
            continue
        x, y = slot_pos(slot, boy_x, ground)
        phase = t * STEP + slot * 1.3
        bob = abs(math.sin(phase)) * 6
        tilt = math.sin(phase) * 0.05
        sway = math.sin(phase + 0.6) * SWAY.get(unit.get('frame'), 0.1)
        if shadow:
            shadow.draw(x, y - 2, r.w * 0.8, shadow.h * 0.45)
        r.draw(x, y + bob, tilt, sway)
