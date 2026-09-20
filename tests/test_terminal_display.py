import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal_display import DisplayFilter


class DisplayTests(unittest.TestCase):
    def test_colors_removed_across_every_chunk_boundary(self):
        source = b'\x1b[1;38;2;12;34;56;48;5;237mAsk Codex\x1b[0m'
        expected = b'\x1b[1mAsk Codex\x1b[0m'
        for boundary in range(len(source) + 1):
            filtering = DisplayFilter()
            self.assertEqual(filtering.feed(source[:boundary]) + filtering.feed(source[boundary:]), expected)

    def test_colon_colors_and_standard_palette(self):
        filtering = DisplayFilter()
        self.assertEqual(filtering.feed(b'\x1b[38:2::255:0:0;48:5:16;4mhello\x1b[31;107m!'),
                         b'\x1b[4mhello!')

    def test_controls_utf8_links_and_images_preserved(self):
        data = ('\x1b[?1000h\x1b[?1006h\x1b[?2004h\x1b[2;3H'
                '\x1b]8;;https://example.com\x1b\\café\x1b]8;;\x1b\\'
                '\x1bPimage\x1b[31m\x1b\\\x1b[7mSelected\x1b[27m').encode()
        filtering = DisplayFilter()
        self.assertEqual(b''.join(filtering.feed(bytes([b])) for b in data), data)

    def test_color_assignments_blocked_queries_preserved(self):
        filtering = DisplayFilter()
        data = b'\x1b]11;#000000\x07\x1b]10;?\x07\x1b]104\x1b\\\x1b]2;Title\x07'
        self.assertEqual(filtering.feed(data), b'\x1b]10;?\x07\x1b]2;Title\x07')

    def test_plain_output_is_unchanged(self):
        self.assertEqual(DisplayFilter().feed(b'hello\r\n\tworld'), b'hello\r\n\tworld')
