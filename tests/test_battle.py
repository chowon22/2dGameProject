"""stats · stages · battle 테스트.  실행: python -m unittest discover tests"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import battle  # noqa: E402
import save_data  # noqa: E402
import stages  # noqa: E402
import stats  # noqa: E402


def unit(frame, black=0, red=0, green=0, blue=0, body='medium', ink=None):
    """black…blue 는 칠한 픽셀 수, ink 는 검정 잉크 (안 주면 픽셀 50 = 잉크 1)."""
    return {'id': 1, 'frame': frame, 'body': body, 'counts': {'black': black, 'red': red, 'green': green, 'blue': blue},
            'ink': {'black': black // 50 if ink is None else ink}}


class StatsTest(unittest.TestCase):
    def test_black_ink_is_percent(self):
        for role, (hp, atk, buff) in stats.STANDARD.items():
            full = stats.unit_stats(unit(role, ink=100))          # 검정 100 = 100%
            self.assertEqual((full['hp'], full['atk'], full['buff']), (hp, atk, buff))
            half = stats.unit_stats(unit(role, ink=50))           # 50 = 50%
            self.assertEqual(half['hp'], round(hp / 2))
            self.assertAlmostEqual(half['atk'], round(atk / 2, 1))
            double = stats.unit_stats(unit(role, ink=200))        # 200 = 200%
            self.assertEqual(double['hp'], hp * 2)
            one = stats.unit_stats(unit(role, ink=1))             # 1 = 1%
            self.assertEqual(one['hp'], max(1, round(hp / 100)))
            self.assertAlmostEqual(one['atk'], round(atk / 100, 1))
            self.assertLess(one['power'], half['power'])
            self.assertLess(half['power'], full['power'])
        self.assertEqual(stats.unit_stats(unit('tank', ink=0))['hp'], 1)    # 체력은 적어도 1
        self.assertGreater(stats.STANDARD['tank'][0], stats.STANDARD['melee'][0])   # 역할마다 다르다
        self.assertGreater(stats.STANDARD['melee'][1], stats.STANDARD['tank'][1])

    def test_color_makes_element(self):
        self.assertIsNone(stats.unit_stats(unit('melee', 3000))['element'])           # 검정뿐: 원소 없음
        self.assertIsNone(stats.unit_stats(unit('melee', 3000, red=50))['element'])   # 조금은 아직
        st = stats.unit_stats(unit('melee', 3000, red=900))
        self.assertEqual(st['element'], 'fire')
        self.assertEqual(stats.unit_stats(unit('melee', 0, red=100, blue=400))['element'], 'water')

    def test_element_matchup(self):
        fire, grass, water = ({'element': e, 'strength': 1.0} for e in ('fire', 'grass', 'water'))
        self.assertGreater(stats.element_mul(fire, grass), 1)
        self.assertLess(stats.element_mul(fire, water), 1)
        self.assertEqual(stats.element_mul({'element': None}, grass), 1.0)
        weak = {'element': 'fire', 'strength': 0.0}
        self.assertLess(stats.element_mul(weak, grass), stats.element_mul(fire, grass))   # 많이 칠할수록 세게

    def test_body_type(self):
        small, large = stats.unit_stats(unit('tank', ink=150, body='small')), stats.unit_stats(unit('tank', ink=150, body='large'))
        self.assertGreater(large['hp'], small['hp'])
        self.assertGreater(small['atk'], large['atk'])


class StagesTest(unittest.TestCase):
    def test_worlds_and_stages(self):
        self.assertEqual([w['id'] for w in stages.worlds()], list(range(8)))
        self.assertEqual(stages.stage_ids(0), [f'0-{i}' for i in range(1, 8)])
        for sid in stages.stage_ids(0):
            es = stages.enemies(sid)
            self.assertTrue(es, sid)
            self.assertTrue(all(0 <= e['slot'] < save_data.PARTY_MAX for e in es), sid)
            self.assertEqual(len({e['slot'] for e in es}), len(es), sid)   # 한 자리에 하나
        self.assertIsNone(stages.stage('1-1'))                             # 아직 준비 중

    def test_unlock_and_clear(self):
        data = save_data.blank(1, now=0)
        self.assertTrue(stages.unlocked(data, '0-1'))
        self.assertFalse(stages.unlocked(data, '0-2'))
        self.assertFalse(stages.world_unlocked(data, 1))
        before = dict(data['ink'])
        got = stages.clear(data, '0-1')
        self.assertTrue(got)
        for c, n in got.items():
            self.assertEqual(data['ink'][c], before.get(c, 0) + n)   # 되찾은 잉크
        self.assertTrue(stages.unlocked(data, '0-2'))
        for sid in stages.stage_ids(0):
            stages.clear(data, sid)
        self.assertTrue(stages.world_unlocked(data, 1))
        self.assertFalse(stages.unlocked(data, '1-1'))                # 데이터가 없으면 열리지 않음


class BattleTest(unittest.TestCase):
    def make(self, ally_stats, enemy_stats):
        allies = [battle.Fighter('ally', i, s) for i, s in enumerate(ally_stats)]
        enemies = [battle.Fighter('enemy', i, s) for i, s in enumerate(enemy_stats)]
        return battle.Battle(allies, enemies, random.Random(1))

    def test_turn_order_and_win(self):
        b = self.make([{'hp': 30, 'atk': 50, 'role': 'melee'}, {'hp': 30, 'atk': 50, 'role': 'ranged'}],
                      [{'hp': 40, 'atk': 3}, {'hp': 40, 'atk': 3}])
        first = b.actor()
        self.assertIs(first, b.allies[0])
        b.attack(first, b.enemies[0])
        self.assertIs(b.actor(), b.allies[1])
        b.attack(b.actor(), b.enemies[1])
        self.assertEqual(b.turn, 'enemy')                 # 아군이 다 움직이면 적 차례
        self.assertEqual(b.result(), 'win')

    def test_enemy_turn_and_lose(self):
        b = self.make([{'hp': 5, 'atk': 1, 'role': 'melee'}], [{'hp': 100, 'atk': 10}])
        b.skip(b.actor())
        self.assertEqual(b.turn, 'enemy')
        for e, _ in b.enemy_plan():
            b.enemy_hit(e, b.pick_target())
        self.assertEqual(b.result(), 'lose')

    def test_taunt_and_support(self):
        b = self.make([{'hp': 50, 'atk': 2, 'role': 'tank'}, {'hp': 20, 'atk': 2, 'role': 'melee'},
                       {'hp': 20, 'atk': 2, 'buff': 5, 'role': 'support'}], [{'hp': 100, 'atk': 1}])
        hits = [b.pick_target().role for _ in range(200)]
        self.assertGreater(hits.count('tank'), 100)       # 탱커가 공격을 끌어온다
        melee = b.allies[1]
        melee.hp = 5
        healed = b.support(b.allies[2], melee)
        self.assertGreater(healed, 0)
        self.assertTrue(melee.boost)
        self.assertGreater(b.damage(melee, b.enemies[0]), 2)   # 힘을 받은 공격


if __name__ == '__main__':
    unittest.main()
