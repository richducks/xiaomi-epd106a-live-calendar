import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('reader_clone', Path(__file__).parents[1] / 'reader_clone.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class TestCloneKit(unittest.TestCase):
    def test_safe_paths(self):
        self.assertTrue(r.safe_rel('apks/com.example.test/00_base.apk'))
        for path in ('../x', '/etc/passwd', 'foo/../x', 'foo\\bar'):
            self.assertFalse(r.safe_rel(path))

    def test_compatibility(self):
        src = {'ro.product.model': 'EPD106A', 'ro.product.device': 'virgo_perf1', 'ro.build.version.sdk': '29'}
        self.assertFalse(r.validate_device(src, src))
        tgt = dict(src, **{'ro.product.model': 'EPD106B'})
        self.assertTrue(r.validate_device(src, tgt))

    def test_checksum_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'diagnostics').mkdir()
            (base / 'diagnostics' / 'properties.txt').write_bytes(b'xyz')
            manifest = {'schema_version': 1, 'files': r.inventory_files(base), 'snapshot_complete': True, 'apk_saved_count': 0}
            r.dump_json(manifest, base / 'manifest.json')
            self.assertEqual(r.verify_dir(base)[1], [])
            (base / 'diagnostics' / 'properties.txt').write_bytes(b'xyz2')
            self.assertTrue(any('不一致' in e for e in r.verify_dir(base)[1]))

    def test_incomplete_snapshot_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r.dump_json({'schema_version': 1, 'files': [], 'snapshot_complete': False, 'errors': ['root']}, base / 'manifest.json')
            self.assertTrue(any('遗漏' in e for e in r.verify_dir(base)[1]))

if __name__ == '__main__':
    unittest.main()
