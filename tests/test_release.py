"""Offline Brooks engineering checks: original code, recovery package, safety."""
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("recovery", ROOT / "tools/build_recovery_ota.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)

class SourceTests(unittest.TestCase):
    def test_lockscreen_manifest_is_only_one_activity(self):
        text = (ROOT / "AndroidManifest.xml").read_text()
        self.assertIn('android:name=".MainActivity"', text)
        self.assertNotIn("DreamService", text)
        self.assertNotIn("ScreenOffProbe", text)
    def test_app_has_minute_tick_and_battery_cutoff(self):
        text = (ROOT / "src/org/epd/calendar/MainActivity.java").read_text()
        self.assertIn("60000L-(now%60000L)", text)
        self.assertIn("MIN_BATTERY_TO_REMAIN_ON=25", text)
        self.assertIn("setRefreshMode", text)
        self.assertNotIn("backgroundRefreshProbe", text)
    def test_hook_is_opt_in_and_preserves_long_press(self):
        text = (ROOT / "xposed/src/org/epd/calendar/policy/PowerPolicyHook.java").read_text()
        self.assertIn('persist.epd.liveclock', text)
        self.assertIn('powerPress",long.class,boolean.class,int.class', text)
        self.assertIn('((Number)p.args[2]).intValue()!=1', text)
        self.assertIn('previousTask', text)
        self.assertNotIn('EVIOCGRAB', text)
        self.assertNotIn('Uinput', text)
    def test_recovery_guard_only_responds_to_exact_marker(self):
        text = (ROOT / "recovery/00-eink-livecalendar-recovery-guard.sh").read_text()
        self.assertIn("DISABLE_EINK_CALENDAR_V1", text)
        self.assertIn('VALUE=', text)
        self.assertIn('TARGET=', text)
        self.assertNotIn("rm -rf", text)
    def test_all_first_party_licenses_present(self):
        self.assertTrue((ROOT / "LICENSE").is_file())
        self.assertIn("Apache License", (ROOT / "LICENSE").read_text())
    def test_vendor_artifacts_are_absent(self):
        for p in ROOT.rglob("*"):
            if p.is_file():
                relative=p.relative_to(ROOT)
                if relative.parts[0] in ("build","dist",".git","__pycache__"):
                    continue  # generated products, never tracked source
                self.assertNotIn(p.suffix.lower(), {".img", ".vdex", ".odex", ".apk", ".keystore"})
                self.assertNotIn("system-lockscreen-before-modification", str(p))
    def test_device_guard_in_installers(self):
        for f in ("install.sh","enable.sh","disable.sh","status.sh","test-device.sh","uninstall.sh"):
            self.assertIn('device_check', (ROOT / "scripts" / f).read_text(), f)

class RecoveryTests(unittest.TestCase):
    def test_unsigned_rescue_has_no_flash_commands(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            binary=d/"update-binary";binary.write_bytes(b"SYNTHETIC_FIXTURE")
            unsigned=d/"rescue.zip"
            recovery.build_zip("rescue",binary,unsigned)
            with ZipFile(unsigned) as f:
                cmd=f.read("META-INF/com/google/android/updater-script").decode()
                self.assertIn("virgo-perf1",cmd)
                self.assertIn("/cache/eink-calendar-rescue.disable",cmd)
                self.assertNotIn('"/dev/block/by-name/boot"',cmd)
                self.assertEqual(f.read("rescue.flag"),b"DISABLE_EINK_CALENDAR_V1\n")
    def test_flash_requires_valid_user_boot_magic(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            binary=d/"update-binary";binary.write_bytes(b"TEST")
            boot=d/"boot.img"
            boot.write_bytes(b"NOT-BOOT")
            with self.assertRaises(ValueError):
                recovery.build_zip("root-flash",binary,d/"unsafe.zip",boot)
            self.assertFalse((d/"unsafe.zip").exists())
    def test_flash_contains_device_check_and_boot_sha(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            binary=d/"update-binary";binary.write_bytes(b"TEST")
            boot=d/"boot.img"
            header=bytearray(48)
            header[:8]=b"ANDROID!"
            struct.pack_into("<I",header,8,1000000)
            struct.pack_into("<I",header,16,320000)
            struct.pack_into("<I",header,36,2048)
            with boot.open("wb") as f:
                f.write(header)
                f.truncate(32*1024*1024)
            unsigned=d/"root.zip"
            digest=recovery.build_zip("root-flash",binary,unsigned,boot)
            with ZipFile(unsigned) as f:
                cmd=f.read("META-INF/com/google/android/updater-script").decode()
                self.assertIn(digest,cmd)
                self.assertIn("virgo-perf1",cmd)
                self.assertIn('package_extract_file("boot.img"',cmd)
                self.assertEqual(f.getinfo("boot.img").file_size,32*1024*1024)
    def test_root_flash_requires_user_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            # Argparse enforces --accept-root-flash-risk BEFORE touching any image.
            import subprocess,sys
            r=subprocess.run([sys.executable,str(ROOT/"tools/build_recovery_ota.py"),
                  "--mode","root-flash","--update-binary","missing",
                  "--output",str(Path(d)/"root.zip")],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn("--accept-root-flash-risk",r.stderr)
            self.assertFalse((Path(d)/"root.zip").exists())
if __name__=="__main__":
    unittest.main()
