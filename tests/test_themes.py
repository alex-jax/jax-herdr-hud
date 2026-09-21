import unittest
from terminal_themes import palettes, palette


class PaletteTests(unittest.TestCase):
    def test_complete_bundled_collection(self):
        themes = palettes()
        self.assertEqual(len(themes), 244)
        self.assertEqual({p['name'] for p in themes.values() if p['primary']}, {
            'Campbell', 'Dracula', 'GNOME', 'High Contrast', 'Horizon', 'Linux',
            'Nord', 'Solarized', 'Tango', 'Ubuntu', 'VS Code', 'XTerm'})
        for key in themes:
            for dark in (False, True):
                colors = palette(key, dark)
                self.assertEqual(len(colors['colors']), 16)
                for value in [colors['foreground'], colors['background'], colors['cursor'], *colors['colors']]:
                    self.assertRegex(value, r'^#[0-9a-fA-F]{6}$')

    def test_original_variants_and_fallback(self):
        self.assertEqual(palette('Ubuntu', True)['background'], '#300A24')
        self.assertEqual(palette('Ubuntu', False)['background'], '#F8F8F8')
        self.assertEqual(palette('Aci', False), palette('Aci', True))
        self.assertIsNone(palette('missing', True))
        self.assertIsNone(palette('hud', True))
