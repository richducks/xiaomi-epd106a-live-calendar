import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MOCK_ADB = r'''#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
if args and args[0] == 'devices':
    print('List of devices attached\nMOCK123\tdevice')
    sys.exit(0)
if args == ['version']:
    print('Android Debug Bridge version 1.0.mock')
    sys.exit(0)
if len(args) < 3 or args[:2] != ['-s','MOCK123']:
    print('bad serial',file=sys.stderr);sys.exit(4)
a=args[2:]
if a[:2] == ['shell','getprop']:
    values = {'ro.product.model': os.environ.get('MOCK_MODEL','EPD106A'),
      'ro.product.device':'virgo_perf1', 'ro.build.version.sdk':'29',
      'ro.build.fingerprint':'vendor/mock/build', 'ro.build.version.release':'10'}
    print(values.get(a[2], '') if len(a)>2 else '[ro.product.model]: [EPD106A]');sys.exit(0)
if a == ['shell','su','-c','id']:
    print('uid=0(root) gid=0(root)');sys.exit(0)
if a[:3] == ['shell','su','-c'] and 'test -e' in a[-1]:
    if 'data/adb/service.d' in a[-1]: print('PRESENT')
    sys.exit(0)
if a[:3] == ['shell','pm','list']:
    print('package:com.example.calendar');sys.exit(0)
if a[:3] == ['shell','pm','path']:
    print('package:/data/app/com.example.calendar/base.apk');sys.exit(0)
if a[:1] == ['pull']:
    import zipfile
    with zipfile.ZipFile(a[-1], 'w') as z:z.writestr('AndroidManifest.xml', 'A'*1200)
    sys.exit(0)
if a[:3] == ['exec-out','su','-c']:
    import io, tarfile
    b = io.BytesIO()
    with tarfile.open(fileobj=b,mode='w') as t:
        data=b'#!/system/bin/sh\necho mock'
        info=tarfile.TarInfo('data/adb/service.d/mock.sh');info.size=len(data)
        t.addfile(info,io.BytesIO(data))
    sys.stdout.buffer.write(b.getvalue());sys.exit(0)
if a[0] in ('install','install-multiple'):
    print('Success');sys.exit(0)
print('MOCK_INFO');sys.exit(0)
'''


@unittest.skipUnless(os.environ.get('RUN_READER_E2E') == '1', '较慢的模拟 ADB 集成测试，手动设置 RUN_READER_E2E=1')
class TestIntegrationMockADB(unittest.TestCase):
    def test_backup_verify_install_and_model_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            if os.name == 'nt':
                mock_script = temp / 'mock_adb.py'
                mock_script.write_text(MOCK_ADB, encoding='utf-8')
                executable = temp / 'adb.cmd'
                executable.write_text('@echo off\r\n"%s" -S "%s" %%*\r\n' % (sys.executable, mock_script), encoding='utf-8')
            else:
                executable = temp / 'adb'
                executable.write_text('#!' + sys.executable + ' -S\n' + MOCK_ADB.split('\n', 1)[1], encoding='utf-8')
                executable.chmod(0o755)
            env = dict(os.environ, ADB_PATH=str(executable))
            main = str(Path(__file__).parents[1] / 'reader_clone.py')
            folder = temp / 'snap'
            doctor = subprocess.run([sys.executable, main, 'doctor'], text=True,
                                    capture_output=True, env=env, timeout=35)
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            cap = subprocess.run([sys.executable, main, 'backup', '--output', str(folder), '--zip'],
                                 text=True, capture_output=True, env=env, timeout=35)
            self.assertEqual(cap.returncode, 0, cap.stdout+cap.stderr+str(__import__("json").loads((folder/"manifest.json").read_text())["errors"]))
            self.assertTrue((folder/'root_overlays.tar').is_file())
            self.assertTrue((folder.with_suffix('.zip')).is_file())
            self.assertTrue((folder/'manifest.json').is_file())
            verify = subprocess.run([sys.executable, main, 'verify', str(folder.with_suffix('.zip'))],
                                    text=True, capture_output=True, env=env, timeout=35)
            self.assertEqual(verify.returncode, 0, verify.stdout+verify.stderr)
            install = subprocess.run([sys.executable, main, 'restore', str(folder), '--install-apks', '--yes'],
                                     text=True, capture_output=True, env=env, timeout=35)
            self.assertEqual(install.returncode, 0, install.stdout+install.stderr)
            wrong = subprocess.run([sys.executable, main, 'restore', str(folder), '--install-apks', '--yes'],
                                   text=True, capture_output=True, env=dict(env,MOCK_MODEL='WRONG'), timeout=35)
            self.assertNotEqual(wrong.returncode, 0)
            self.assertIn('不匹配', wrong.stderr)

if __name__ == '__main__':
    unittest.main()
