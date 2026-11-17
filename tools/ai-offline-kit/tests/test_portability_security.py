import importlib.util
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('reader_clone', Path(__file__).parents[1] / 'reader_clone.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class TestPortabilityAndSecurity(unittest.TestCase):
    def test_portable_archive_paths(self):
        invalid = ['C:/Windows/system.ini', 'C:\\Windows\\a', '../secret', 'a/../b',
                   '//server/file', 'a//b', 'x/.', 'x/./y', 'x\\y', 'a:b', 'hello/']
        for name in invalid:
            with self.subTest(name=name):
                self.assertFalse(r.safe_rel(name))
        self.assertTrue(r.safe_rel('apks/com.example.calendar/00_base.apk'))

    def test_reject_zip_traversal_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename in ['../outside.txt', 'C:/Windows/a.txt', 'a/../b']:
                path = Path(tmp) / 'test.zip'
                with zipfile.ZipFile(path, 'w') as z:
                    z.writestr(filename, 'X')
                with self.assertRaises(RuntimeError):
                    with r.bundle_dir(path):
                        pass
            path = Path(tmp) / 'dup.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('dup.txt', 'A')
                with __import__('warnings').catch_warnings():
                    __import__('warnings').simplefilter('ignore', UserWarning)
                    z.writestr('dup.txt', 'B')
            with self.assertRaises(RuntimeError):
                with r.bundle_dir(path):
                    pass

    def test_reject_zip_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'symlink.zip'
            with zipfile.ZipFile(path, 'w') as z:
                info = zipfile.ZipInfo('lnk')
                info.create_system = 3
                info.external_attr = (0o120777 << 16)
                z.writestr(info, 'target')
            with self.assertRaises(RuntimeError):
                with r.bundle_dir(path):
                    pass

    def test_reject_symlink_in_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'diagnostics').mkdir()
            (base / 'real.txt').write_text('secret')
            try:
                (base / 'diagnostics' / 'link.txt').symlink_to(base / 'real.txt')
            except (OSError, NotImplementedError):
                self.skipTest('Windows 当前用户无符号链接权限')
            manifest = {'schema_version': 1, 'snapshot_complete': True, 'files': [
                {'path': 'diagnostics/link.txt', 'size': 6, 'sha256': r.sha256(base / 'real.txt')},
                {'path': 'real.txt', 'size': 6, 'sha256': r.sha256(base / 'real.txt')}]}
            r.dump_json(manifest, base / 'manifest.json')
            _, errors = r.verify_dir(base)
            self.assertTrue(any('符号链接' in e for e in errors), errors)

    def test_v01_manifest_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            r.dump_json({'schema_version': 1, 'snapshot_complete': True, 'files': []}, base / 'manifest.json')
            self.assertEqual(r.verify_dir(base)[1], [])

    def test_explicit_adb_path_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            adb = Path(tmp) / ('adb.exe' if os.name == 'nt' else 'adb')
            adb.write_bytes(b'mock')
            self.assertEqual(r.find_adb(str(adb)), str(adb.resolve()))
            with patch.dict(os.environ, {'ADB_PATH': str(adb)}):
                self.assertEqual(r.find_adb(), str(adb.resolve()))


if __name__ == '__main__':
    unittest.main()
