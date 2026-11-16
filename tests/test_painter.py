"""painter · frames · save_data 유닛 테스트.  실행: python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import frames  # noqa: E402
import painter  # noqa: E402
import save_data  # noqa: E402
from painter import Paper  # noqa: E402

PLENTY = {c: 10 ** 6 for c in painter.COLORS}


class PaperTest(unittest.TestCase):
    def test_stroke_is_continuous_even_when_fast(self):
        p = Paper(200, 100)
        p.begin(10, 50, 'black', PLENTY)
        p.drag(190, 50, 'black', PLENTY)   # 한 번에 멀리 움직여도
        p.end()
        self.assertTrue((p.labels[50, 10:191] == 1).all())   # 사이가 끊기지 않는다

    def test_counts_match_pixels(self):
        p = Paper(120, 80)
        p.begin(30, 40, 'red', PLENTY)
        p.drag(90, 40, 'red', PLENTY)
        self.assertEqual(p.count('red'), int((p.labels == 2).sum()))
        self.assertEqual(p.count('black'), 0)
        self.assertEqual(p.ink_used()['red'], painter.ink_for(p.count('red')))

    def test_overpaint_moves_pixels_between_colors(self):
        p = Paper(100, 100)
        p.begin(50, 50, 'black', PLENTY)
        before = p.count('black')
        p.begin(50, 50, 'blue', PLENTY)
        self.assertEqual(p.count('black') + p.count('blue'), before)
        self.assertEqual(p.count('black'), 0)

    def test_eraser(self):
        p = Paper(100, 100)
        p.begin(50, 50, 'black', PLENTY)
        p.begin(50, 50, painter.ERASER, PLENTY)
        self.assertTrue(p.is_empty())

    def test_ink_limit_blocks_painting(self):
        p = Paper(400, 100)
        limit = {'black': 2, 'red': 0, 'green': 0, 'blue': 0}
        p.begin(10, 50, 'black', limit)
        p.drag(390, 50, 'black', limit)
        self.assertTrue(p.blocked)
        self.assertLessEqual(p.ink_used()['black'], 2)
        p.begin(50, 20, 'red', limit)   # 없는 색은 한 점도 못 칠한다
        self.assertEqual(p.count('red'), 0)

    def test_png_round_trip(self):
        p = Paper(80, 60)
        p.begin(20, 30, 'green', PLENTY)
        p.drag(60, 30, 'green', PLENTY)
        p.begin(40, 10, 'black', PLENTY)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'u.png')
            p.save_png(path)
            q = Paper(80, 60)
            q.load_png(path)
        self.assertEqual(q.counts_dict(), p.counts_dict())

    def test_undo_strokes_clear_and_load(self):
        p = Paper(100, 60)
        p.begin(20, 30, 'black', PLENTY); p.drag(80, 30, 'black', PLENTY); p.end()
        one = p.counts_dict()
        p.begin(50, 10, 'red', PLENTY); p.end()
        self.assertTrue(p.undo())                       # 붓질 하나
        self.assertEqual(p.counts_dict(), one)
        p.clear()
        self.assertTrue(p.undo())                       # 다 지우기
        self.assertEqual(p.counts_dict(), one)
        self.assertTrue(p.undo())
        self.assertTrue(p.is_empty())
        self.assertFalse(p.undo())                      # 더 없음
        for i in range(painter.MAX_UNDO + 5):
            p.begin(i, 5, 'black', PLENTY)
        self.assertEqual(len(p.history), painter.MAX_UNDO)

    def test_clear_and_dirty(self):
        p = Paper(50, 50)
        p.dirty = None
        p.begin(25, 25, 'black', PLENTY)
        self.assertIsNotNone(p.dirty)
        p.clear()
        self.assertTrue(p.is_empty())


class FramesTest(unittest.TestCase):
    def test_four_frames_with_parts(self):
        self.assertEqual(frames.IDS, ('tank', 'melee', 'ranged', 'support'))
        for fid in frames.IDS:
            m = frames.part_mask(fid)
            self.assertEqual(m.shape, (frames.PAPER_H, frames.PAPER_W))
            self.assertEqual(set(m.ravel()) - {0}, set(range(1, len(frames.part_names(fid)) + 1)))

    def test_every_part_shows(self):
        for fid in frames.IDS:   # 뒤 부위에 완전히 가려진 부위가 없어야 한다
            counts = np.bincount(frames.part_mask(fid).ravel(), minlength=len(frames.part_names(fid)) + 1)
            self.assertTrue((counts[1:] > 50).all(), fid)


    def test_gear_is_apart_from_body(self):
        """무기·방패는 몸·손과 떨어져 있어야 한다 (따로 애니메이션 하려고)."""
        from PIL import Image, ImageFilter
        for fid in frames.IDS:
            mask = frames.part_mask(fid)
            names = frames.part_names(fid)
            gear_ids = [names.index(g) + 1 for g in frames.gear_names(fid)]
            gear = np.isin(mask, gear_ids)
            body = (mask > 0) & ~gear
            near = np.asarray(Image.fromarray((gear * 255).astype(np.uint8)).filter(
                ImageFilter.MaxFilter(frames.GEAR_GAP * 2 + 1))) > 0
            self.assertFalse((near & body).any(), fid)


class UnitSaveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        save_data.current = None

    def tearDown(self):
        self.tmp.cleanup()
        save_data.current = None

    def test_add_unit_records_cost_without_spending(self):
        data = save_data.new_game(1, self.dir, now=0.0)
        unit = save_data.add_unit(data, 'tank', {'black': 250}, {'black': 10}, self.dir)
        self.assertEqual(unit['id'], 1)
        self.assertEqual(unit['ink'], {'black': 10})
        self.assertEqual(data['ink']['black'], save_data.START_INK)   # 가진 잉크는 그대로
        self.assertTrue(os.path.isdir(save_data.units_dir(1, self.dir)))
        self.assertEqual(save_data.add_unit(data, 'melee', {}, {}, self.dir)['id'], 2)

    def test_delete_unit(self):
        data = save_data.new_game(1, self.dir, now=0.0)
        a = save_data.add_unit(data, 'tank', {}, {'black': 1}, self.dir)
        b = save_data.add_unit(data, 'melee', {}, {'black': 1}, self.dir)
        open(save_data.unit_path(1, a['id'], self.dir), 'wb').close()
        save_data.add_to_party(data, a['id'])
        save_data.add_to_party(data, b['id'])
        save_data.add_to_party(data, a['id'])
        self.assertTrue(save_data.delete_unit(data, a['id'], self.dir))
        self.assertEqual([u['id'] for u in data['units']], [b['id']])
        self.assertEqual(data['party'], [None, b['id'], None, None, None, None])   # 놓은 자리도 빈다
        self.assertFalse(os.path.exists(save_data.unit_path(1, a['id'], self.dir)))
        self.assertFalse(save_data.delete_unit(data, a['id'], self.dir))

    def test_party_slots_within_ink(self):
        data = save_data.new_game(1, self.dir, now=0.0)          # 검정 START_INK
        big = save_data.add_unit(data, 'tank', {}, {'black': 200}, self.dir)
        small = save_data.add_unit(data, 'melee', {}, {'black': 60}, self.dir)
        red = save_data.add_unit(data, 'ranged', {}, {'red': 5}, self.dir)
        self.assertEqual(save_data.add_to_party(data, big['id']), 0)    # 앞자리부터
        self.assertIsNone(save_data.add_to_party(data, big['id']))       # 400 > 300
        self.assertTrue(save_data.place(data, 4, small['id']))           # 고른 자리에
        self.assertFalse(save_data.place(data, 2, red['id']))            # 빨강은 없다
        self.assertEqual(data['party'], [big['id'], None, None, None, small['id'], None])
        self.assertEqual(save_data.party_cost(data)['black'], 260)
        self.assertTrue(save_data.place(data, 0, small['id']))           # 바꿔 놓기: 있던 유닛은 빠진다고 친다
        self.assertEqual(save_data.party_cost(data)['black'], 120)
        save_data.swap_slots(data, 0, 5)
        self.assertEqual(data['party'], [None, None, None, None, small['id'], small['id']])
        save_data.remove_from_party(data, 4)
        self.assertEqual(data['party'][4], None)

    def test_party_full(self):
        data = save_data.new_game(1, self.dir, now=0.0)
        u = save_data.add_unit(data, 'tank', {}, {'black': 1}, self.dir)
        for i in range(save_data.PARTY_MAX):
            self.assertEqual(save_data.add_to_party(data, u['id']), i)
        self.assertIsNone(save_data.add_to_party(data, u['id']))
        self.assertTrue(save_data.place(data, 3, u['id']))               # 꽉 차도 바꿔 놓기는 된다

    def test_old_party_list_becomes_slots(self):
        data = save_data.new_game(1, self.dir, now=0.0)
        u = save_data.add_unit(data, 'tank', {}, {}, self.dir)
        data['party'] = [u['id'], 99]                                    # 예전 세이브: id 목록, 없어진 프리셋
        save_data.write(data, self.dir)
        self.assertEqual(save_data.load(1, self.dir)['party'], [u['id'], None, None, None, None, None])

    def test_delete_removes_unit_images(self):
        data = save_data.new_game(3, self.dir, now=0.0)
        save_data.add_unit(data, 'tank', {}, {}, self.dir)
        open(save_data.unit_path(3, 1, self.dir), 'wb').close()
        save_data.delete(3, self.dir)
        self.assertFalse(os.path.exists(save_data.units_dir(3, self.dir)))


if __name__ == '__main__':
    unittest.main()
