"""Static regression contracts for EPD106A Xposed power/calendar wiring.

Runtime acceptance must still be performed on the rooted reader: these tests
cannot prove LSPosed interception or e-ink framebuffer behavior on their own.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = (ROOT / "xposed/src/org/epd/calendar/policy/PowerPolicyHook.java").read_text()
CALENDAR = (ROOT / "src/org/epd/calendar/MainActivity.java").read_text()


def body(source, signature, next_signature):
    start = source.index(signature)
    end = source.index(next_signature, start + len(signature))
    return source[start:end]


class RefreshRouting(unittest.TestCase):
    def test_both_entries_use_shared_transition(self):
        self.assertIn("handleShortPress(Context ctx){handleTransition(ctx,false);}", POLICY)
        self.assertIn("handleTransition(ctx,true);", POLICY)
        self.assertNotIn("if(featureEnabled(TENMIN_ENABLE))startTenMinuteCycle(ctx);\n              }", POLICY)

    def test_shared_launch_arms_sleep_cycle(self):
        transition = body(POLICY, "private static void handleTransition(", "private static void safeSleep(")
        launch = transition[transition.index("ctx.startActivity(open);"):]
        self.assertIn("startTenMinuteCycle(ctx);", launch)
        self.assertIn('TENMIN_ENTRY route=', launch)
        self.assertIn('idleTimeout?"AUTO_TIMEOUT":"POWER_KEY"', launch)

    def test_timeout_on_existing_clock_never_exits(self):
        transition = body(POLICY, "private static void handleTransition(", "private static void safeSleep(")
        case = transition[transition.index("if(isClock){"):transition.index("cancelTenMinuteCycle(ctx);")]
        self.assertIn("if(idleTimeout)", case)
        self.assertIn("startTenMinuteCycle(ctx);", case)
        self.assertIn("return;", case)

    def test_cycle_is_idempotent_and_power_exit_cancels_alarm(self):
        start = body(POLICY, "private static void startTenMinuteCycle(", "private static void scheduleNextWake(")
        self.assertIn("if(tenMinuteSession||!canTenMinuteCycle(ctx))return;", start)
        transition = body(POLICY, "private static void handleTransition(", "private static void safeSleep(")
        self.assertIn("cancelTenMinuteCycle(ctx);", transition)
        self.assertIn("ctx.sendBroadcast(exit);", transition)

    def test_power_safety_and_real_sleep_remain(self):
        self.assertIn("private static final long TEN_MINUTES_MS=600000L", POLICY)
        self.assertIn("alarm.setExact(android.app.AlarmManager.RTC_WAKEUP", POLICY)
        self.assertIn("pm.isInteractive()", POLICY)
        self.assertIn('if(!plugged && (level<LOW_BATTERY_STOCK_THRESHOLD))', POLICY)
        self.assertIn("sleep.invoke(pm,SystemClock.uptimeMillis());", POLICY)

    def test_foreground_minute_tick_still_disabled(self):
        schedule = body(CALENDAR, "void scheduleTick(){", "@Override public void onCreate(")
        self.assertIn("if(isTenMinuteExperiment())", schedule)
        self.assertIn("handler.removeCallbacks(tick)", schedule)
        self.assertIn("return;", schedule)

    def test_battery_percentage_is_preserved(self):
        update = body(CALENDAR, "void update(){", "void drawMonth(")
        self.assertIn("Intent.ACTION_BATTERY_CHANGED", update)
        self.assertIn('setIfChanged(batteryView,"电量 "+percent+"%")', update)

    def test_production_minute_mode_is_explicit_and_backwards_compatible(self):
        self.assertIn('REFRESH_MINUTES="persist.epd.clock.interval"', POLICY)
        self.assertIn('if("1".equals(minutes))return ONE_MINUTE_MS;', POLICY)
        self.assertIn('return TEN_MINUTES_MS;', POLICY)
        self.assertIn('private static final long ONE_MINUTE_MS=60000L;', POLICY)
        self.assertIn('long interval=refreshIntervalMs();', POLICY)

    def test_minute_wake_shorter_than_ten_minute_wake(self):
        self.assertIn('MINUTE_RTC_SETTLE_MS=2200L', POLICY)
        self.assertIn('interval==ONE_MINUTE_MS', POLICY)
        self.assertIn('?MINUTE_RTC_SETTLE_MS:PAINT_SETTLE_MS+1000L', POLICY)
        self.assertIn('if(trigger-now<8000L)trigger+=interval;', POLICY)

    def test_minute_changes_dirty_clock_only_not_all_static_views(self):
        self.assertIn('if(!android.text.TextUtils.equals(view.getText(),value))view.setText(value);', CALENDAR)
        self.assertIn('if(!android.text.TextUtils.equals(clock.getText(),hhmm))', CALENDAR)
        self.assertIn('DU_MINUTE_CLOCK_TEXT_UPDATED', CALENDAR)
        self.assertNotIn('clock.invalidate();', CALENDAR)
        self.assertIn('if(key!=dateKey)', CALENDAR)
        self.assertIn('setIfChanged(solar,', CALENDAR)

    def test_rtc_mode_does_not_keep_screen_on(self):
        power = body(CALENDAR, 'void applyPowerPolicy(){', '// Use the firmware')
        self.assertIn('if(isTenMinuteExperiment())', power)
        self.assertIn('getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)', power)
        self.assertIn('RTC_CLOCK_NO_KEEP_SCREEN_ON', power)
        self.assertIn('getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)', power)


if __name__ == "__main__":
    unittest.main()
