import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_runner

class TestAISource(unittest.TestCase):
    def test_missing_source_dir_rejected(self):
        class Args:
            action='source'
            project_dir=None
            output=None
        out=ai_runner.execute(Args())
        self.assertFalse(out['ok'])
        self.assertEqual(out['reader']['return_code'], 3)

if __name__=='__main__':
    unittest.main()
