import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class TestReleasePolicy(unittest.TestCase):
    def test_public_package_does_not_vendor_restricted_binaries(self):
        text=(ROOT/'packaging'/'package_desktop.py').read_text(encoding='utf-8')
        self.assertNotIn("'vendor/",text)
        self.assertNotIn("'reader-backups/",text)
        self.assertIn('AGENTS.md',text)

    def test_release_manifest_has_target_matrix(self):
        value=json.loads((ROOT/'packaging'/'release.json').read_text(encoding='utf-8'))
        self.assertEqual(len(value['published_assets']),4)
        self.assertTrue(value['tag'].startswith('ai-kit-'))

if __name__=='__main__':unittest.main()
