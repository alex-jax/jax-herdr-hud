import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal_display import DisplayFilter


class DisplayTests(unittest.TestCase):
    def test_colors_preserved_across_every_chunk_boundary(self):
        source = b'\x1b[1;38;2;12;34;56;48;5;237mAsk Codex\x1b[0m'
        expected = source
        for boundary in range(len(source) + 1):
            filtering = DisplayFilter()
            self.assertEqual(filtering.feed(source[:boundary]) + filtering.feed(source[boundary:]), expected)

    def test_colon_colors_and_standard_palette(self):
        filtering = DisplayFilter()
        self.assertEqual(filtering.feed(b'\x1b[38:2::255:0:0;48:5:16;4mhello\x1b[31;107m!'),
                         b'\x1b[38:2::255:0:0;48:5:16;4mhello\x1b[31;107m!')

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

    def test_background_modes_preserve_foreground_components(self):
        data = b'\x1b[38;2;40;100;107;48;2;55;57;65;1mtext\x1b[0m'
        self.assertEqual(DisplayFilter().feed(data),
                         data)
        for code in list(range(40, 48)) + list(range(100, 108)):
            self.assertEqual(DisplayFilter().feed(f'\x1b[{code}m'.encode()), f'\x1b[{code}m'.encode())
        self.assertEqual(DisplayFilter().feed(b'\x1b[48;2;1m'), b'\x1b[48;2;1m')

    def test_plain_output_is_unchanged(self):
        self.assertEqual(DisplayFilter().feed(b'hello\r\n\tworld'), b'hello\r\n\tworld')

    def test_black_highlight_text_keeps_its_light_background(self):
        for style in (b'30;107', b'38;5;0;48;5;255',
                      b'38;2;0;0;0;48;2;220;220;220'):
            source = b'\x1b[' + style + b'mBack to bottom / pasted text\x1b[0m'
            filtering = DisplayFilter()
            self.assertEqual(b''.join(filtering.feed(bytes([b])) for b in source), source)
