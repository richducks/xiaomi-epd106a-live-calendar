import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_offline as kit
import ai_runner


class TestOfflineAI(unittest.TestCase):
    def test_reject_zip_slip_and_wrong_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            for entry in ('../outside.txt', 'platform-tools/../../outside', 'other/adb'):
                archive = d / 'a.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr(entry, b'hacked')
                with patch.object(kit, 'VENDOR', d):
                    with self.assertRaises(ValueError):
                        kit.extract_zip_platform_tools(archive, d / 'out')
                self.assertFalse((d / 'out').exists())

    def test_synthetic_platform_tools_extract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'source.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('platform-tools/adb', b'example harmless mock binary')
                z.writestr('platform-tools/fastboot', b'example harmless mock binary')
            with patch.object(kit, 'VENDOR', root):
                kit.extract_zip_platform_tools(archive, root / 'out')
            self.assertTrue((root / 'out' / 'adb').is_file())

    def test_synthetic_python_extract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tarpath = root / 'python.tar.gz'
            import io
            with tarfile.open(tarpath, 'w:gz') as tar:
                payload = b'NOT a real Python runtime; test extraction only'
                ti = tarfile.TarInfo('python/bin/python3.11')
                ti.size = len(payload)
                ti.mode = 0o755
                tar.addfile(ti, io.BytesIO(payload))
            with patch.object(kit, 'VENDOR', root):
                kit.extract_python(tarpath, root / 'runtime')
            self.assertEqual((root / 'runtime/bin/python3.11').read_bytes(), payload)

    def test_no_claim_offline_without_files_and_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(kit, 'VENDOR', Path(temp)), patch.object(kit, 'LOCK', Path(temp) / 'vendor-lock.json'):
                self.assertFalse(kit.check_target('linux-x64', details=True)['ready'])

    def test_restore_requires_approval_and_serial(self):
        class Opt:
            action = 'restore'
            approve_install = False
            serial = None
            bundle = 'any.zip'
        r = ai_runner.execute(Opt())
        self.assertFalse(r['ok'])
        self.assertIn('明确授权', r['blocked'])
        Opt.approve_install = True
        r = ai_runner.execute(Opt())
        self.assertFalse(r['ok'])
        self.assertIn('设备序列号', r['blocked'])

    def test_ai_json_no_dependencies(self):
        with patch('ai_runner.invoke', return_value={'return_code': 1, 'stdout': '', 'stderr': 'missing adb'}):
            class Opt: action='status'
            r = ai_runner.execute(Opt())
        self.assertEqual(r['reader']['stderr'], 'missing adb')
        self.assertFalse(r['ok'])
        json.dumps(r)


if __name__ == '__main__': unittest.main()
