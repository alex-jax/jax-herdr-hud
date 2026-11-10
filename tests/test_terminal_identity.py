import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hud import terminal_identity


class TerminalIdentityTests(unittest.TestCase):
    def test_extracts_valid_user_host_prefixes(self):
        self.assertEqual(terminal_identity('root@server:/app'), 'root@server')
        self.assertEqual(terminal_identity('jax@mac.local ~'), 'jax@mac.local')
        for title in ('', 'Codex', 'mail user@example.com', 'root@host!bad'):
            self.assertIsNone(terminal_identity(title))
        self.assertIsNone(terminal_identity(None))


if __name__ == '__main__':
    unittest.main()
