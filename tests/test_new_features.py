import unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
class BatteryAndNeatZonesTest(unittest.TestCase):
    def test_calendar_percentage_uses_android_sticky_broadcast(self):
        text=(BASE/"src/org/epd/calendar/MainActivity.java").read_text()
        self.assertIn('batteryView.setText("电量 "+percent+"%")',text)
        self.assertIn("BatteryManager.EXTRA_LEVEL",text)
        self.assertIn("BatteryManager.EXTRA_SCALE",text)
        self.assertIn("Math.min(100",text)
        self.assertIn('batteryView.setText("电量 --%")',text)
        self.assertIn('Intent.ACTION_BATTERY_CHANGED',text)
    def test_calendar_reuses_compact_footer(self):
        text=(BASE/"src/org/epd/calendar/MainActivity.java").read_text()
        self.assertIn("footer.addView(batteryView",text)
        self.assertIn("add(root,footer,40)",text)
    def test_neat_scope_and_no_system_wide_touch_hook(self):
        source=(BASE/"neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java").read_text()
        self.assertIn('PKG="com.gzhi.neatreader.r2.main"',source)
        self.assertIn('READER="com.gzhi.neatreader.r2.navigator.reader.BookReaderActivity"',source)
        self.assertIn('PKG.equals(p.processName)',source)
        self.assertNotIn('Activity.class,"dispatchTouchEvent"',source)
        self.assertNotIn("PhoneWindowManager",source)
        self.assertNotIn("new PopupWindow(",source)
    def test_neat_small_tap_zones_in_existing_window(self):
        source=(BASE/"neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java").read_text()
        self.assertIn('decor.addView(zone,params)',source)
        self.assertIn('decor.addView(menu,lp)',source)
        self.assertIn('case MotionEvent.ACTION_UP:',source)
        self.assertIn('SystemClock.uptimeMillis()-started<420',source)
        self.assertIn('Math.round(w*.32f)',source)
        self.assertIn('Math.round(h*.34f)',source)
        self.assertIn('top=zone("top"',source)
        self.assertIn('center=zone("center"',source)
        self.assertIn('toggleMenu()',source)
        self.assertIn('"上一页"',source)
        self.assertIn('"下一页"',source)
        self.assertIn('"更多设置"',source)
    def test_optional_refresh_is_device_scoped_and_opt_in(self):
        source=(BASE/"neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java").read_text()
        self.assertIn('persist.epd.neatfast',source)
        self.assertIn('if(!"1".equals(opt))return;',source)
        self.assertIn('setRefreshMode',source)
        self.assertNotIn('persist.sys.mRefreshMode',source)
    def test_app_hook_separate_apk_and_scope(self):
        manifest=(BASE/"neat-zones/AndroidManifest.xml").read_text()
        self.assertIn('package="org.epd.neat.touchzones"',manifest)
        self.assertIn("xposedmodule",manifest)
        self.assertTrue((BASE/"build-neat-zones.sh").is_file())
if __name__=="__main__":unittest.main()
