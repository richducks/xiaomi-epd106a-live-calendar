"""Automatic idle timeout must show live calendar without affecting stock sleep safeguards."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"xposed/src/org/epd/calendar/policy/PowerPolicyHook.java").read_text()
MAIN=(ROOT/"src/org/epd/calendar/MainActivity.java").read_text()
PROVISION=(ROOT/"scripts/provision-clone.sh").read_text()

class AutoTimeoutTests(unittest.TestCase):
    def test_scoped_to_exact_firmware_observed_timeout_method(self):
        for fragment in (
            '"android".equals(lpparam.packageName)', 'Process.myUid()!=1000',
            'goToSleepNoUpdateLocked', 'long.class,int.class,int.class,int.class',
            'GO_TO_SLEEP_REASON_TIMEOUT=2',
            '((Number)p.args[2]).intValue()!=0',
            '((Number)p.args[3]).intValue()!=android.os.Process.SYSTEM_UID',
        ):
            self.assertIn(fragment,SOURCE)

    def test_explicit_user_opt_in_and_disable_controls(self):
        self.assertIn('AUTO_ENABLE="persist.epd.autoclock"', SOURCE)
        self.assertIn('!featureEnabled(ENABLE)||!featureEnabled(AUTO_ENABLE)',SOURCE)
        self.assertIn('persist.epd.autoclock 0',PROVISION)
        self.assertIn('persist.epd.autoclock 1',PROVISION)
        self.assertIn('resetprop persist.epd.autoclock 0',(ROOT/"scripts/disable.sh").read_text())

    def test_no_stock_sleep_for_allowed_timeout_only(self):
        self.assertIn('p.setResult(Boolean.FALSE);',SOURCE)
        self.assertIn('worker.post(()->{',SOURCE)
        self.assertIn('handleTransition(ctx,true);',SOURCE)
        self.assertIn('AUTO_TIMEOUT_CALENDAR_LAUNCHED',SOURCE)
        self.assertIn('handleTransition(ctx,false)',SOURCE)
        self.assertIn('AUTO_TIMEOUT_CLOCK_ALREADY_VISIBLE',SOURCE)

    def test_battery_and_failure_fallback_to_stock(self):
        for fragment in (
            'LOW_BATTERY_STOCK_THRESHOLD=30', 'AUTO_TIMEOUT_STOCK_SLEEP_BATTERY',
            'level<0||level<LOW_BATTERY_STOCK_THRESHOLD', 'catch(Throwable ex)',
            'circuitOpen=true;', 'safeSleep(ctx);',
            'return; // Timeout must never close the clock.',
        ):
            self.assertIn(fragment,SOURCE)

    def test_neatreader_releases_only_its_own_keep_screen_on_during_auto_idle(self):
        zones=(ROOT/'neat-zones/src/org/epd/neat/touchzones/NeatTouchZones.java').read_text()
        for fragment in ('autoIdleEnabled()', 'persist.epd.autoclock',
                         'FLAG_KEEP_SCREEN_ON',
                         'window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)',
                         'void detach(){\n      restoreReaderKeepOn();',
                         'NEAT_ALLOW_IDLE_TIMEOUT_KEEP_ON_CLEARED'):
            self.assertIn(fragment,zones)

    def test_live_display_and_exit_restore_native_reader(self):
        self.assertIn('FLAG_KEEP_SCREEN_ON',MAIN)
        self.assertIn('MIN_BATTERY_TO_REMAIN_ON=25',MAIN)
        self.assertIn('previousTask=t==null?-1:t.id',SOURCE)
        self.assertIn('RESTORED_READING_TASK',SOURCE)
        self.assertIn('clock.setText(hhmm);',MAIN)

if __name__=="__main__":
    unittest.main()
