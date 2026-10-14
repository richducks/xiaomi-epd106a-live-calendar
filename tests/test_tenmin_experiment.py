"""RTC experimental mode: exact 10-min wake, repaint, suspend, and rollback safety."""
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
POLICY=(BASE/"xposed/src/org/epd/calendar/policy/PowerPolicyHook.java").read_text()
CLOCK=(BASE/"src/org/epd/calendar/MainActivity.java").read_text()
DISABLE=(BASE/"scripts/disable.sh").read_text()

class TenMinuteRtcTests(unittest.TestCase):
    def test_repaint_requests_target_existing_calendar_activity(self):
        for chunk in ('TENMIN_RTC_REFRESH_ACTIVITY_REQUESTED',
                      'refresh.setComponent(new ComponentName(CLOCK_PACKAGE,CLOCK_ACTIVITY))',
                      'refresh.putExtra("tenmin_rtc_refresh",true)',
                      'Intent.FLAG_ACTIVITY_SINGLE_TOP',
                      'setIntent(intent)',
                      'TENMIN_RTC_REFRESH_APPLIED text=',
                      'update();'):
            self.assertIn(chunk,POLICY+CLOCK)
        self.assertNotIn('clock.invalidate();',CLOCK)

    def test_disable_regular_minute_updates_only_in_opt_in(self):
        self.assertIn('TENMIN_FOREGROUND_MINUTE_TICK_DISABLED',CLOCK)
        self.assertIn('if(isTenMinuteExperiment())',CLOCK)
        self.assertIn('return;',CLOCK)
        self.assertIn('handler.removeCallbacks(tick);',CLOCK)

    def test_default_10min_not_test_1min(self):
        self.assertIn('TEN_MINUTES_MS=600000L',POLICY)
        self.assertIn('long interval=refreshIntervalMs();',POLICY)
        self.assertIn('return TEN_MINUTES_MS;',POLICY)
        self.assertIn('android.app.AlarmManager.RTC_WAKEUP',POLICY)
        self.assertIn('TENMIN_RTC_WAKE_SCHEDULED',POLICY)

    def test_low_battery_scope_rollback_and_no_global_wake(self):
        self.assertIn('level>=LOW_BATTERY_STOCK_THRESHOLD',POLICY)
        self.assertIn('!isClockForeground(ctx)',POLICY)
        self.assertIn('cancelTenMinuteCycle(ctx)',POLICY)
        self.assertIn('persist.epd.tenmin',DISABLE)
        self.assertNotIn('fastboot flash',POLICY)
        self.assertNotIn('su -c',POLICY)

if __name__=="__main__":unittest.main()
