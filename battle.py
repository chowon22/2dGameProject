"""턴제 전투 규칙 (PRD 6장). pico2d 와 무관한 순수 로직 (tests/test_battle.py). 화면은 battle_mode.

- 플레이어 차례: 살아 있는 아군이 자리 순서(앞줄부터)대로 한 번씩 행동한다
  · 공격: 적 하나를 골라 흡수(피해). 피해 = 공격력 x 상성 배율 (서포터에게 힘을 받았으면 x 1.3)
  · 서포터는 아군을 골라 치료 + 다음 공격 힘 보태기 (버프량만큼)
  · 넘기기
- 적 차례: 살아 있는 적이 하나씩 아군을 공격한다. 탱커가 살아 있으면 탱커 쪽으로 더 자주 (적의 공격을 끌어온다)
- 적이 다 쓰러지면 승리, 아군이 다 쓰러지면 패배
"""
import random

import stats

POWER_UP = 1.3        # 서포터가 힘을 보탠 다음 공격 배율
TAUNT = 0.6           # 탱커가 있으면 적이 탱커를 노릴 확률


class Fighter:
    def __init__(self, side, slot, st, ref=None):
        self.side, self.slot, self.ref = side, slot, ref
        self.role = st.get('role')
        self.max_hp = self.hp = max(1, round(st['hp']))
        self.atk = st['atk']
        self.buff = st.get('buff', 0)
        self.element = st.get('element')
        self.strength = st.get('strength', 0.5)
        self.boost = False

    @property
    def alive(self):
        return self.hp > 0

    def info(self):
        return {'element': self.element, 'strength': self.strength}


class Battle:
    def __init__(self, allies, enemies, rng=None):
        self.allies = sorted(allies, key=lambda f: f.slot)
        self.enemies = sorted(enemies, key=lambda f: f.slot)
        self.rng = rng or random.Random()
        self.turn = 'player'
        self.acted = set()
        self.round = 1

    # ------------------------------------------------------------ 상태
    def alive(self, side):
        return [f for f in (self.allies if side == 'ally' else self.enemies) if f.alive]

    def result(self):
        if not self.alive('enemy'):
            return 'win'
        if not self.alive('ally'):
            return 'lose'
        return None

    def actor(self):
        """지금 행동할 아군 (없으면 None — 적 차례로 넘어갈 때)."""
        if self.turn != 'player':
            return None
        for f in self.allies:
            if f.alive and f not in self.acted:
                return f
        return None

    # ------------------------------------------------------------ 행동
    def damage(self, attacker, target):
        mul = stats.element_mul(attacker.info(), target.info())
        if attacker.boost:
            mul *= POWER_UP
        return max(1, round(attacker.atk * mul))

    def attack(self, attacker, target):
        """피해를 주고 (피해, 상성 배율) 을 돌려준다."""
        dmg = self.damage(attacker, target)
        mul = stats.element_mul(attacker.info(), target.info())
        target.hp = max(0, target.hp - dmg)
        attacker.boost = False
        self._done(attacker)
        return dmg, mul

    def support(self, supporter, ally):
        """서포터: 아군 치료 + 다음 공격 힘 보태기. 치료한 양."""
        amount = round(3 + supporter.buff * 2)
        before = ally.hp
        ally.hp = min(ally.max_hp, ally.hp + amount)
        ally.boost = True
        self._done(supporter)
        return ally.hp - before

    def skip(self, f):
        self._done(f)

    def _done(self, f):
        if f.side == 'ally':
            self.acted.add(f)
            if self.actor() is None:
                self.turn = 'enemy'

    # ------------------------------------------------------------ 적 차례
    def enemy_plan(self):
        """[(적, 노릴 아군)] — 차례대로 보여 주며 enemy_hit 로 실행한다."""
        plan = []
        for e in self.alive('enemy'):
            plan.append((e, None))
        return plan

    def pick_target(self):
        allies = self.alive('ally')
        if not allies:
            return None
        tanks = [a for a in allies if a.role == 'tank']
        if tanks and self.rng.random() < TAUNT:
            return self.rng.choice(tanks)
        return self.rng.choice(allies)

    def enemy_hit(self, enemy, target):
        if not enemy.alive or not target or not target.alive:
            return 0, 1.0
        dmg = self.damage(enemy, target)
        mul = stats.element_mul(enemy.info(), target.info())
        target.hp = max(0, target.hp - dmg)
        return dmg, mul

    def end_enemy_turn(self):
        self.turn = 'player'
        self.acted = set()
        self.round += 1
