"""painter · frames · save_data 유닛 테스트.  실행: python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest

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

    def test_silhouette_is_faint(self):
        s = frames.silhouette('tank')
        self.assertEqual(s.shape, (frames.PAPER_H, frames.PAPER_W, 4))
        self.assertGreater(s[..., 3].max(), 0)
        self.assertLess(s[..., 3].max(), 200)


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

    def test_delete_removes_unit_images(self):
        data = save_data.new_game(3, self.dir, now=0.0)
        save_data.add_unit(data, 'tank', {}, {}, self.dir)
        open(save_data.unit_path(3, 1, self.dir), 'wb').close()
        save_data.delete(3, self.dir)
        self.assertFalse(os.path.exists(save_data.units_dir(3, self.dir)))


if __name__ == '__main__':
    unittest.main()
