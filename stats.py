"""그린 유닛·몬스터의 능력치와 원소 (PRD 4.2, 5장). pico2d 와 무관한 순수 로직 (tests/test_battle.py).

- 검정 잉크 1 = 체력·공격력(·버프량) +1% (예: 검정 150 을 썼으면 기본의 2.5배). 역할마다 기본 능력치가 다르다
  (탱커는 체력, 근딜·원딜은 공격력, 서포터는 버프량이 높다)
- 색을 칠하면 원소가 생긴다: 가장 많이 칠한 색 (빨강 불, 초록 풀, 파랑 물). 많이 칠할수록 상성이 세게 먹힌다
- 체형: 작은 체형은 날렵하게(공격 조금 ↑, 체력 ↓), 큰 체형은 튼튼하게(체력 ↑, 공격 조금 ↓)
- 전투력(power) = 한눈에 비교하는 값 (체력 + 공격력·버프량 가중 합)
수치는 PRD 미정 사항이라 여기 상수로 모아 두고 나중에 맞춘다.
"""
ELEMENT_OF = {'red': 'fire', 'green': 'grass', 'blue': 'water'}
ELEMENT_NAMES = {'fire': '불', 'grass': '풀', 'water': '물', None: '없음'}
BEATS = {'fire': 'grass', 'grass': 'water', 'water': 'fire'}   # 불 > 풀 > 물 > 불

BASE = {   # 역할마다 기본 (체력, 공격력, 버프량) — 검정 잉크 % 만큼 커진다
    'tank': (40, 4, 0), 'melee': (24, 8, 0), 'ranged': (20, 7, 0), 'support': (22, 3, 4),
}
BLACK_PERCENT = 1.0           # 검정 잉크 1 마다 능력치 +1%
BODY_MUL = {'small': (0.85, 1.1), 'medium': (1.0, 1.0), 'large': (1.2, 0.92)}   # (체력, 공격력)
ELEMENT_MIN_SHARE = 0.08      # 색이 칠한 픽셀의 이만큼은 넘어야 원소가 생긴다
ELEMENT_FULL = 2000           # 색을 이만큼 칠하면 상성 세기 최대


def power(hp, atk, buff=0):
    return round(hp + atk * 5 + buff * 4)


def unit_stats(unit):
    """그린 유닛 → {'role', 'hp', 'atk', 'buff', 'element', 'strength', 'power'}."""
    role = unit.get('frame') if unit.get('frame') in BASE else 'melee'
    counts = unit.get('counts', {})
    black = counts.get('black', 0)
    grow = 1 + unit.get('ink', {}).get('black', 0) * BLACK_PERCENT / 100   # 검정 잉크 1 = +1%
    hp, atk, buff = (v * grow for v in BASE[role])
    mh, ma = BODY_MUL.get(unit.get('body', 'medium'), (1.0, 1.0))
    hp, atk = hp * mh, atk * ma
    colors = {c: counts.get(c, 0) for c in ELEMENT_OF}
    total = black + sum(colors.values())
    best = max(colors, key=colors.get)
    element, strength = None, 0.0
    if total and colors[best] >= total * ELEMENT_MIN_SHARE:
        element = ELEMENT_OF[best]
        strength = min(1.0, colors[best] / ELEMENT_FULL)
    hp, atk, buff = round(hp), round(atk, 1), round(buff, 1)
    return {'role': role, 'hp': hp, 'atk': atk, 'buff': buff, 'element': element, 'strength': strength,
            'power': power(hp, atk, buff)}


def element_mul(attacker, defender):
    """상성 배율: 이기는 원소면 1.25 ~ 1.5, 지는 원소면 0.8 ~ 0.7 (칠한 만큼 세게), 아니면 1."""
    a, d = attacker.get('element'), defender.get('element')
    s = attacker.get('strength', 0.5)
    if a and BEATS.get(a) == d:
        return 1.25 + 0.25 * s
    if d and BEATS.get(d) == a:
        return 0.8 - 0.1 * s
    return 1.0


HURT_MAX, HURT_MIN = 0.8, 0.15   # 다친 그림 투명도: 거의 가득 → 거의 없음 (PRD 1.4: 그림이 곧 체력)


def hurt_alpha(frac):
    """남은 체력 비율 → 그림 투명도. 가득이면 1, 한 번이라도 다치면 바로 반투명, 쓰러지면 아주 흐리게."""
    if frac >= 1:
        return 1.0
    if frac <= 0:
        return 0.12
    return HURT_MIN + (HURT_MAX - HURT_MIN) * frac


def team_power(stats_list):
    return sum(s['power'] for s in stats_list)
