"""save_data 테스트.  실행: python -m unittest discover tests"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import save_data  # noqa: E402


class SaveDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        save_data.current = None

    def tearDown(self):
        self.tmp.cleanup()
        save_data.current = None

    def test_empty_slot(self):
        self.assertFalse(save_data.exists(1, self.dir))
        self.assertIsNone(save_data.load(1, self.dir))
        self.assertIsNone(save_data.summary(1, self.dir))

    def test_new_game_writes_and_selects(self):
        data = save_data.new_game(2, self.dir, now=100.0)
        self.assertTrue(save_data.exists(2, self.dir))
        self.assertIs(save_data.current, data)
        self.assertEqual(data['ink']['black'], save_data.START_INK)
        self.assertEqual(save_data.load(2, self.dir)['created_at'], 100.0)

    def test_play_time_accumulates(self):
        save_data.new_game(1, self.dir, now=0.0)
        save_data.save_current(self.dir, now=90.0)
        save_data.save_current(self.dir, now=150.0)
        loaded = save_data.load(1, self.dir)
        self.assertAlmostEqual(loaded['play_time'], 150.0)
        self.assertEqual(loaded['saved_at'], 150.0)

    def test_continue_game(self):
        save_data.new_game(3, self.dir, now=0.0)
        save_data.current['stage'] = 2
        save_data.save_current(self.dir, now=10.0)
        save_data.current = None
        data = save_data.continue_game(3, self.dir, now=20.0)
        self.assertEqual(data['stage'], 2)
        save_data.save_current(self.dir, now=50.0)
        self.assertAlmostEqual(save_data.load(3, self.dir)['play_time'], 40.0)

    def test_continue_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            save_data.continue_game(1, self.dir)

    def test_delete(self):
        save_data.new_game(1, self.dir)
        save_data.delete(1, self.dir)
        self.assertFalse(save_data.exists(1, self.dir))
        self.assertIsNone(save_data.current)
        save_data.delete(1, self.dir)  # 없는 걸 지워도 괜찮다

    def test_broken_file_is_empty(self):
        with open(os.path.join(self.dir, 'slot_1.json'), 'w', encoding='utf-8') as f:
            f.write('{not json')
        self.assertIsNone(save_data.load(1, self.dir))

    def test_missing_keys_filled(self):
        with open(os.path.join(self.dir, 'slot_1.json'), 'w', encoding='utf-8') as f:
            json.dump({'stage': 4, 'unknown': 1}, f)
        data = save_data.load(1, self.dir)
        self.assertEqual(data['stage'], 4)
        self.assertIn('ink', data)
        self.assertNotIn('unknown', data)

    def test_bad_slot(self):
        with self.assertRaises(ValueError):
            save_data.load(0, self.dir)
        with self.assertRaises(ValueError):
            save_data.load(save_data.SLOTS + 1, self.dir)

    def test_save_without_current(self):
        self.assertFalse(save_data.save_current(self.dir))

    def test_format(self):
        self.assertEqual(save_data.format_play_time(59), '0분')
        self.assertEqual(save_data.format_play_time(125 * 60), '2시간 5분')
        self.assertEqual(save_data.stage_name(0), '여정을 떠나기 전')
        self.assertEqual(save_data.stage_name(3), '여정 3단계')


if __name__ == '__main__':
    unittest.main()
