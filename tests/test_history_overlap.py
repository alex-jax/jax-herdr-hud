import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hud import Hud


class HistoryOverlapTests(unittest.TestCase):
    def test_downward_scroll_omits_stationary_controls(self):
        before = ['header', 'a', 'b', 'c', 'd', 'input', 'footer']
        after = ['header', 'c', 'd', 'e', 'f', 'input', 'footer']
        self.assertEqual(Hud.scrolled_rows(before, after, 1),
                         (1, 2, ['a', 'b', 'c', 'd'], ['c', 'd', 'e', 'f'], 2))

    def test_upward_scroll_retains_overlap(self):
        self.assertEqual(Hud.scrolled_rows(['c', 'd', 'e', 'f'], ['a', 'b', 'c', 'd'], -1),
                         (0, 0, ['c', 'd', 'e', 'f'], ['a', 'b', 'c', 'd'], -2))

    def test_redraw_without_overlap_is_not_concatenated(self):
        self.assertIsNone(Hud.scrolled_rows(['a', 'b', 'c'], ['x', 'y', 'z'], 1))

    def test_blank_overlap_is_not_enough(self):
        self.assertIsNone(Hud.scrolled_rows(['a', '', ''], ['', '', 'b'], 1))

    def test_transcript_scroll_with_replaced_footer(self):
        before = ['header'] + [f'line {i}' for i in range(20)] + ['Back to bottom', 'input', 'earlier messages']
        after = ['header'] + [f'line {i}' for i in range(3, 23)] + ['', 'input', 'shortcuts']
        result = Hud.scrolled_rows(before, after, 1)
        self.assertEqual(result, (1, 3, before[1:21], after[1:21], 3))
        reverse = Hud.scrolled_rows(after, before, -1)
        self.assertEqual(reverse, (1, 3, after[1:21], before[1:21], -3))
