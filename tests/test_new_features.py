import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
SOURCE=BASE/"neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java"

class BatteryAndNeatZonesTest(unittest.TestCase):
    def test_battery_comes_from_android_sticky_broadcast(self):
        s=(BASE/"src/org/epd/calendar/MainActivity.java").read_text()
        self.assertIn('batteryView.setText("电量 "+percent+"%")',s)
        self.assertIn('Intent.ACTION_BATTERY_CHANGED',s)
        self.assertIn("BatteryManager.EXTRA_LEVEL",s)
        self.assertIn("BatteryManager.EXTRA_SCALE",s)
        self.assertIn("Math.min(100",s)

    def test_battery_reuses_footer(self):
        s=(BASE/"src/org/epd/calendar/MainActivity.java").read_text()
        self.assertIn("footer.addView(batteryView",s)
        self.assertIn("add(root,footer,40)",s)

    def test_app_only_scope_no_system_server_hook(self):
        s=SOURCE.read_text()
        self.assertIn('PACKAGE="com.gzhi.neatreader.r2.main"',s)
        self.assertIn('READER="com.gzhi.neatreader.r2.navigator.reader.BookReaderActivity"',s)
        self.assertIn('PACKAGE.equals(p.processName)',s)
        self.assertNotIn("PhoneWindowManager",s)
        self.assertNotIn("new PopupWindow(",s)

    def test_center_uses_neatreader_original_menu_not_custom_buttons(self):
        s=SOURCE.read_text()
        self.assertIn('control(a,"ll_layer_top")',s)
        self.assertIn('control(a,"ll_layer_bot")',s)
        self.assertIn('top.setVisibility(show?View.VISIBLE:View.GONE)',s)
        self.assertIn('bottom.setVisibility(show?View.VISIBLE:View.GONE)',s)
        self.assertIn("toggleNativeMenu()",s)
        self.assertNotIn('addButton("上一页"',s)
        self.assertNotIn('addButton("更多设置"',s)
        self.assertNotIn("new PopupWindow(",s)
        self.assertIn("ZONE_X=.33f",s)
        self.assertIn("ZONE_Y=.35f",s)

    def test_enabled_opt_in_fail_closed(self):
        s=SOURCE.read_text()
        self.assertIn('"persist.epd.neatzones","0"',s)
        self.assertIn('return false; // opt-in only',s)
        self.assertIn("if(!enabled()",s)

    def test_native_gesture_handoff_and_cleanup(self):
        s=SOURCE.read_text()
        for snippet in ("HOLD_FORWARD_MS=320L","ViewConfiguration.get(activity)",
                        "ACTION_MOVE","ACTION_POINTER_DOWN",
                        "MotionEvent.obtain(e)","dispatchUnder(e)","forwardDown()",
                        "onPause","old.detach()","originalDown.recycle()",
                        "copy.offsetLocation(center.getLeft(),center.getTop())",
                        "copy.recycle()"):
            self.assertIn(snippet,s)

    def test_scope_not_power_policy(self):
        s=(BASE/"neat-zones/AndroidManifest.xml").read_text()
        self.assertIn('package="org.epd.neat.touchzones"',s)
        self.assertIn("xposedmodule",s)
        self.assertTrue((BASE/"build-neat-zones.sh").is_file())

if __name__=="__main__":
    unittest.main()
