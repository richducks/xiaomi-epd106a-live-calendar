"""Regression checks for dual menu: native reader controls + slim OEM system bar."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java"
MANIFEST = ROOT / "neat-zones/AndroidManifest.xml"


class DualMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = SOURCE.read_text(encoding="utf-8")
        cls.manifest = MANIFEST.read_text(encoding="utf-8")

    def test_center_tap_shows_both_native_and_oem_bars(self):
        for fragment in (
            'else toggleNativeMenu();',
            'control(a,"ll_layer_top")',
            'control(a,"ll_layer_bot")',
            'if(show)showSystemBar();',
            'top.setVisibility(show?View.VISIBLE:View.GONE);',
            'bottom.setVisibility(show?View.VISIBLE:View.GONE);',
            'WindowManager.LayoutParams.FLAG_FULLSCREEN',
            'decor.setSystemUiVisibility(originalSystemUiFlags & ~HIDDEN_BAR_FLAGS);',
        ):
            self.assertIn(fragment, self.code)

    def test_closing_or_pausing_restores_original_fullscreen_state(self):
        for fragment in (
            'originalSystemUiFlags=decor.getSystemUiVisibility();',
            'void detach(){\n      restoreSystemBar();',
            'else restoreSystemBar();',
            'window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);',
            'decor.setSystemUiVisibility(originalSystemUiFlags);',
        ):
            self.assertIn(fragment, self.code)

    def test_does_not_cover_reading_page_with_notifications(self):
        self.assertNotIn('expandNotificationsPanel', self.code)
        self.assertNotIn('sendBroadcast(', self.code)
        self.assertNotIn('EXPAND_STATUS_BAR', self.manifest)
        self.assertNotIn('<receiver', self.manifest)

    def test_paging_zone_and_touch_passthrough_remain_native(self):
        for fragment in (
            'ZONE_X=.33f', 'ZONE_Y=.35f', 'ZONE_W=.34f',
            'ACTION_POINTER_DOWN', 'ACTION_MOVE',
            'forwardDown();', 'dispatchUnder(e);',
            'copy.offsetLocation(center.getLeft(),center.getTop());',
        ):
            self.assertIn(fragment, self.code)


if __name__ == "__main__":
    unittest.main()
