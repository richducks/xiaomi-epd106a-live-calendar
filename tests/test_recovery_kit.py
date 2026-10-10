"""EPD106A recovery/deployment guards: offline, never flash automatically."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "device/current-profile.json"
PROVISION = ROOT / "scripts/provision-clone.sh"
SNAPSHOT = ROOT / "scripts/snapshot-private.sh"
PINNED = ROOT / "device/release-apks.sha256"


class RecoveryKitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(DEVICE.read_text())
        cls.provision = PROVISION.read_text()
        cls.snapshot = SNAPSHOT.read_text()

    def test_only_matching_device_and_exact_firmware(self):
        self.assertEqual(self.profile["device_model"], "EPD106A")
        self.assertEqual(self.profile["android_sdk"], 27)
        self.assertIn("ro.build.fingerprint", self.provision)
        self.assertIn("PROFILE_FINGERPRINT", self.provision)
        self.assertIn("exactly one authorized ADB", self.provision)
        self.assertIn("if [[ \"$MODE\" == --check ]]", self.provision)

    def test_all_first_party_apks_pinned(self):
        pins = PINNED.read_text().splitlines()
        self.assertEqual(len(pins), 3)
        self.assertEqual(set(line.split()[1] for line in pins),
                         set(self.profile["first_party_apks"]))
        self.assertTrue(all(re.fullmatch(r"[a-f0-9]{64}", line.split()[0]) for line in pins))

    def test_scope_split_and_safe_activation(self):
        self.assertEqual(self.profile["lsposed_scopes"]["org.epd.calendar.policy"], ["android"])
        self.assertEqual(self.profile["lsposed_scopes"]["org.epd.neat.touchzones"], ["com.gzhi.neatreader.r2.main"])
        self.assertIn("EPD_SCOPES_CONFIRMED", self.provision)
        self.assertIn("persist.epd.liveclock 0", self.provision)
        self.assertIn("persist.epd.neatzones 0", self.provision)
        self.assertIn("resetprop persist.epd.liveclock 1", self.provision)
        self.assertIn("resetprop persist.epd.neatzones 1", self.provision)

    def test_scripts_never_write_to_raw_partitions(self):
        for script in (self.provision, self.snapshot):
            self.assertNotIn("of=/dev/block/", script)
            self.assertNotIn("fastboot flash", script)
            self.assertNotIn("wipe data", script.lower())
            self.assertNotIn("pm clear", script)
        self.assertIn("if=/dev/block", self.snapshot) if "if=/dev/block" in self.snapshot else self.assertIn('block="/dev/block/by-name/', self.snapshot)

    def test_checkpoint_is_private_and_integrity_checked(self):
        self.assertIn("umask 077", self.snapshot)
        self.assertIn('chmod 700', self.snapshot)
        self.assertIn('sha256sum', self.snapshot)
        self.assertIn('sha256sum --check', self.snapshot)
        self.assertNotIn('github.com/', self.snapshot)
        self.assertNotIn('curl ', self.snapshot)


if __name__ == "__main__":
    unittest.main()
