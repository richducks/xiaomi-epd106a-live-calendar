import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestDesktopDistribution(unittest.TestCase):
    def test_gui_self_test_headless(self):
        with tempfile.TemporaryDirectory() as temp:
            out = subprocess.run([sys.executable, str(ROOT / 'desktop_gui.py'), '--self-test'],
                                 capture_output=True, encoding='utf-8', errors='replace', timeout=20,
                                 env={**os.environ, 'XIAOMI_READER_DATA_DIR': temp})
            self.assertEqual(out.returncode, 0, out.stderr)
            status = json.loads(out.stdout)
            self.assertEqual(status['application'], 'XiaomiReader')
            self.assertEqual(status['version'], '0.3.1')
            self.assertFalse(status['runtime'] == 'bundled')

    def test_gui_avoids_rom_flashing(self):
        src = (ROOT / 'desktop_gui.py').read_text(encoding='utf-8')
        self.assertNotIn('fastboot flash', src)
        self.assertNotIn('dd if=', src)
        self.assertIn('INSTALL', src)
        self.assertIn('backup', src)

    def test_frozen_root_is_user_writable(self):
        for file in ('reader_clone.py', 'prepare_offline.py', 'ai_runner.py'):
            self.assertIn("getattr(sys, 'frozen', False)", (ROOT / file).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
