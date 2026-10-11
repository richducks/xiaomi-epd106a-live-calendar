package org.epd.calendar.policy;

import android.app.ActivityManager;
import android.app.AlarmManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;
import java.lang.reflect.Method;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

public final class PowerPolicyHook implements IXposedHookLoadPackage {
  private static final String TAG="EinkLivePowerPolicy";
  private static final String ENABLE="persist.epd.liveclock";
  private static final String AUTO_ENABLE="persist.epd.autoclock";
  private static final int GO_TO_SLEEP_REASON_TIMEOUT=2;
  private static final int LOW_BATTERY_STOCK_THRESHOLD=30;
  private static final String CLOCK_PACKAGE="org.epd.calendar";
  private static final String CLOCK_ACTIVITY="org.epd.calendar.MainActivity";
  private static final String ACTION_EXIT="org.epd.calendar.EXIT_CLOCK";
  private static final AtomicBoolean BUSY=new AtomicBoolean(false);
  // Short-lived guard for the vendor SuspendLogo async drawable; never global.
  private static volatile long suppressLogoUntilUptimeMs=0;
  private static volatile boolean circuitOpen=false;
  private static volatile int previousTask=-1;
  private static Handler worker;
  private static Method propGet;

  @Override public void handleLoadPackage(XC_LoadPackage.LoadPackageParam lpparam) throws Throwable {
    // LSPosed emits callbacks for other packages hosted inside system_server.
    // PhoneWindowManager is available only for the exact initial "android"
    // framework callback. Never try to hook Telecom, Settings, or other APKs.
    if(!"android".equals(lpparam.packageName))return;
    if(android.os.Process.myUid()!=1000)return;
    XposedBridge.log("EPD_POLICY_FRAMEWORK_ENTRY process="+lpparam.processName);
    Log.i(TAG,"MODULE_ENTRY pkg="+lpparam.packageName+" process="+lpparam.processName);
    // Only the system-server policy, never other processes or hardware /dev/input.
    Class<?> policy=XposedHelpers.findClass("com.android.server.policy.PhoneWindowManager",lpparam.classLoader);
    propGet=Class.forName("android.os.SystemProperties").getMethod("get",String.class,String.class);
    HandlerThread thread=new HandlerThread("EinkNativeCalendarPolicy");
    thread.start();
    worker=new Handler(thread.getLooper());
    XposedHelpers.findAndHookMethod(policy,"powerPress",long.class,boolean.class,int.class,
      new XC_MethodHook(){
        @Override protected void beforeHookedMethod(MethodHookParam p) {
          try {
            if(circuitOpen || !Boolean.TRUE.equals(p.args[1]))return;
            if(((Number)p.args[2]).intValue()!=1)return;
            if(!"1".equals((String)propGet.invoke(null,ENABLE,"0")))return;
            if(!BUSY.compareAndSet(false,true))return; // allow stock press while busy
            final Context c=(Context)XposedHelpers.getObjectField(p.thisObject,"mContext");
            if(c==null){BUSY.set(false);return;}
            if(worker==null){BUSY.set(false);return;}
            // Skip stock goToSleep BEFORE it creates the static SuspendLogo.
            p.setResult(null);
            worker.post(new Runnable(){
              @Override public void run(){
                try{handleShortPress(c);}
                catch(Throwable e){
                  Log.e(TAG,"Transition failed; restoring stock behavior",e);
                  circuitOpen=true;
                  safeSleep(c);
                }finally{BUSY.set(false);}
              }
            });
          }catch(Throwable e){
            // When hook setup is invalid, let the original policy handle power.
            BUSY.set(false);
            circuitOpen=true;
            Log.e(TAG,"Policy guard failed, default power behavior retained",e);
          }
        }
      });
    // On this Android 8.1 firmware idle timeout goes straight through
    // PowerManagerService, bypassing PhoneWindowManager.powerPress().
    // Explicit opt-in and reason guard keep every other sleep path native.
    try{
      Class<?> powerService=XposedHelpers.findClass(
          "com.android.server.power.PowerManagerService",lpparam.classLoader);
      XposedHelpers.findAndHookMethod(powerService,"goToSleepNoUpdateLocked",
          long.class,int.class,int.class,int.class,new XC_MethodHook(){
        @Override protected void beforeHookedMethod(MethodHookParam p){
          try{
            if(circuitOpen||worker==null)return;
            if(((Number)p.args[1]).intValue()!=GO_TO_SLEEP_REASON_TIMEOUT
                ||((Number)p.args[2]).intValue()!=0
                ||((Number)p.args[3]).intValue()!=android.os.Process.SYSTEM_UID)return;
            if(!featureEnabled(ENABLE)||!featureEnabled(AUTO_ENABLE))return;
            final Context ctx=(Context)XposedHelpers.getObjectField(p.thisObject,"mContext");
            if(ctx==null)return;
            Intent battery=ctx.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            boolean plugged=battery!=null
                &&battery.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)!=0;
            int level=battery==null?-1:battery.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
            // A live, updating e-ink calendar requires an ON display. Below
            // 30%, or when battery state is unknown, preserve stock standby.
            if(!plugged&&(level<0||level<LOW_BATTERY_STOCK_THRESHOLD)){
              Log.i(TAG,"AUTO_TIMEOUT_STOCK_SLEEP_BATTERY level="+level);
              return;
            }
            if(!BUSY.compareAndSet(false,true))return;
            // The OEM sometimes queues showSuspendLogo separately, even
            // when goToSleepNoUpdateLocked returns false. Suppress only the
            // pending timeout transition, never normal / low-battery sleep.
            suppressLogoUntilUptimeMs=SystemClock.uptimeMillis()+2500L;
            // The intercepted private method returns boolean, NOT void.
            p.setResult(Boolean.FALSE);
            Log.i(TAG,"AUTO_TIMEOUT_INTERCEPT level="+level+" plugged="+plugged);
            worker.post(()->{
              try{
                handleTransition(ctx,true);
                if(featureEnabled(TENMIN_ENABLE))startTenMinuteCycle(ctx);
              }
              catch(Throwable ex){
                suppressLogoUntilUptimeMs=0;
                circuitOpen=true;
                Log.e(TAG,"AUTO_TIMEOUT_FAILED; falling back to stock sleep",ex);
                safeSleep(ctx);
              }finally{BUSY.set(false);}
            });
          }catch(Throwable ex){
            suppressLogoUntilUptimeMs=0;
            BUSY.set(false);
            circuitOpen=true;
            Log.e(TAG,"AUTO_TIMEOUT_GUARD_FAILED; letting stock sleep execute",ex);
          }
        }
      });
      // showSuspendLogo() is OEM-specific: a second async route can create
      // its full-screen Window after the sleep decision was already skipped.
      // Hook only this exact private void method. Any absent OEM signature
      // leaves the rest of Android and the clock hook untouched.
      try{
        XposedHelpers.findAndHookMethod(powerService,"showSuspendLogo",new XC_MethodHook(){
          @Override protected void beforeHookedMethod(MethodHookParam p){
            long now=SystemClock.uptimeMillis();
            if(!circuitOpen&&suppressLogoUntilUptimeMs>now
                &&featureEnabled(ENABLE)&&featureEnabled(AUTO_ENABLE)){
              p.setResult(null);
              Log.i(TAG,"AUTO_TIMEOUT_VENDOR_SUSPEND_LOGO_SKIPPED");
            }
          }
        });
        XposedBridge.log("EPD_POLICY_VENDOR_SUSPEND_LOGO_GUARD_READY");
      }catch(Throwable logoError){
        Log.w(TAG,"OEM suspend logo hook unavailable; timeout policy still active",logoError);
      }
      XposedBridge.log("EPD_POLICY_AUTO_TIMEOUT_HOOK_READY opt-in "+AUTO_ENABLE);
    }catch(Throwable e){
      Log.e(TAG,"Idle timeout hook unavailable; stock sleep unchanged",e);
    }
    XposedBridge.log("EPD_POLICY_POWERPRESS_HOOK_INSTALLED disabled_by_default");
    Log.i(TAG,"LegacyPolicyHook installed; disabled by default unless "+ENABLE+"=1");
  }


  // EXPERIMENT: RTC wake, repaint the existing Activity, return to real sleep.
  // This is intentionally opt-in because OEM e-ink framebuffer persistence and
  // wakeUp policy must be verified on each firmware.
  private static final String TENMIN_ENABLE="persist.epd.tenmin";
  private static final String TENMIN_TEST="persist.epd.tenmin.test";
  private static final long TEN_MINUTES_MS=600000L;
  private static final long EXPERIMENT_TEST_MS=60000L;
  private static final long PAINT_SETTLE_MS=2500L;
  private static volatile boolean tenMinuteSession=false;
  private static android.app.AlarmManager.OnAlarmListener scheduledWake;
  private static int tenMinuteGeneration=0;

  private static boolean isClockForeground(Context ctx){
    ActivityManager am=(ActivityManager)ctx.getSystemService(Context.ACTIVITY_SERVICE);
    if(am==null)return false;
    List<ActivityManager.RunningTaskInfo> tasks=am.getRunningTasks(1);
    ComponentName top=tasks==null||tasks.isEmpty()?null:tasks.get(0).topActivity;
    return top!=null && CLOCK_PACKAGE.equals(top.getPackageName())
        && CLOCK_ACTIVITY.equals(top.getClassName());
  }

  private static boolean canTenMinuteCycle(Context ctx){
    if(!featureEnabled(ENABLE)||!featureEnabled(AUTO_ENABLE)
        ||!featureEnabled(TENMIN_ENABLE)||circuitOpen)return false;
    Intent b=ctx.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
    int level=b==null?-1:b.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
    boolean external=b!=null&&b.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)!=0;
    return external || level>=LOW_BATTERY_STOCK_THRESHOLD;
  }
  private static void cancelTenMinuteCycle(Context ctx){
    tenMinuteSession=false;
    tenMinuteGeneration++;
    if(scheduledWake!=null){
      android.app.AlarmManager alarms=(android.app.AlarmManager)ctx.getSystemService(Context.ALARM_SERVICE);
      if(alarms!=null)alarms.cancel(scheduledWake);
      scheduledWake=null;
    }
  }
  private static void startTenMinuteCycle(Context ctx){
    if(!canTenMinuteCycle(ctx))return;
    final int generation=++tenMinuteGeneration;
    tenMinuteSession=true;
    // Schedule before sleeping so a process crash or unexpected sleep won't
    // leave the experiment holding a wake lock.
    scheduleNextWake(ctx,generation);
    worker.postDelayed(()->enterTenMinuteSleep(ctx,generation),PAINT_SETTLE_MS);
  }
  private static void scheduleNextWake(Context ctx,int generation){
    android.app.AlarmManager alarm=(android.app.AlarmManager)ctx.getSystemService(Context.ALARM_SERVICE);
    if(alarm==null){cancelTenMinuteCycle(ctx);return;}
    long interval=featureEnabled(TENMIN_TEST)?EXPERIMENT_TEST_MS:TEN_MINUTES_MS;
    long now=System.currentTimeMillis();
    long trigger=(now/interval+1L)*interval;
    if(trigger-now<8000L)trigger+=interval;
    if(scheduledWake!=null)alarm.cancel(scheduledWake);
    scheduledWake=()->{
      if(!tenMinuteSession||generation!=tenMinuteGeneration)return;
      if(!canTenMinuteCycle(ctx)||!isClockForeground(ctx)){
        Log.i(TAG,"TENMIN_CANCEL_NOT_CLOCK_OR_LOW_BATTERY");
        cancelTenMinuteCycle(ctx);return;
      }
      try{
        PowerManager pm=(PowerManager)ctx.getSystemService(Context.POWER_SERVICE);
        if(pm==null)throw new IllegalStateException("power manager unavailable");
        if(!pm.isInteractive()){
          Method wake=PowerManager.class.getDeclaredMethod("wakeUp",long.class);
          wake.setAccessible(true);
          wake.invoke(pm,SystemClock.uptimeMillis());
          Log.i(TAG,"TENMIN_RTC_WAKE_DISPLAY_ON");
          // Force the existing reader-clock Activity to paint fresh HH:mm.
          // Waking the display alone does not guarantee onResume is called.
          worker.postDelayed(()->{
            if(tenMinuteSession&&generation==tenMinuteGeneration&&isClockForeground(ctx)){
              Intent refresh=new Intent();
              refresh.setComponent(new ComponentName(CLOCK_PACKAGE,CLOCK_ACTIVITY));
              refresh.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK |
                  Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_NO_ANIMATION);
              refresh.putExtra("tenmin_rtc_refresh",true);
              ctx.startActivity(refresh);
              Log.i(TAG,"TENMIN_RTC_REFRESH_ACTIVITY_REQUESTED");
            }
          },450L);
        }else Log.i(TAG,"TENMIN_RTC_ALREADY_INTERACTIVE");
        // Activity.onResume() repaints HH:mm using the actual RTC time.
        // Do not sleep if reader has replaced clock or user has left it.
        worker.postDelayed(()->{
          if(tenMinuteSession&&generation==tenMinuteGeneration&&isClockForeground(ctx)){
            scheduleNextWake(ctx,generation);
            enterTenMinuteSleep(ctx,generation);
          }else cancelTenMinuteCycle(ctx);
        },PAINT_SETTLE_MS+1000L);
      }catch(Throwable e){
        Log.e(TAG,"TENMIN_RTC_WAKE_FAILED; disable experiment",e);
        cancelTenMinuteCycle(ctx);
      }
    };
    alarm.setExact(android.app.AlarmManager.RTC_WAKEUP,trigger,
        "EpdCalendar10MinuteRTC",scheduledWake,worker);
    Log.i(TAG,"TENMIN_RTC_WAKE_SCHEDULED epoch="+trigger+" interval="+interval);
  }
  private static void enterTenMinuteSleep(Context ctx,int generation){
    if(!tenMinuteSession||generation!=tenMinuteGeneration||!canTenMinuteCycle(ctx)
        ||!isClockForeground(ctx)){cancelTenMinuteCycle(ctx);return;}
    try{
      PowerManager pm=(PowerManager)ctx.getSystemService(Context.POWER_SERVICE);
      if(pm==null)throw new IllegalStateException("power manager missing");
      // Keep the E-Ink framebuffer; the OEM's separate static SuspendLogo
      // window must not replace the just-drawn calendar during this sleep.
      suppressLogoUntilUptimeMs=SystemClock.uptimeMillis()+2500L;
      Method sleep=PowerManager.class.getDeclaredMethod("goToSleep",long.class);
      sleep.setAccessible(true);
      sleep.invoke(pm,SystemClock.uptimeMillis());
      Log.i(TAG,"TENMIN_REAL_SLEEP_REQUESTED");
    }catch(Throwable e){
      suppressLogoUntilUptimeMs=0;
      Log.e(TAG,"TENMIN_SLEEP_FAILED; disable experimental cycle",e);
      cancelTenMinuteCycle(ctx);
    }
  }

  private static boolean featureEnabled(String prop){
    try{return "1".equals((String)propGet.invoke(null,prop,"0"));}
    catch(Throwable e){return false;}
  }
  private static void handleShortPress(Context ctx){handleTransition(ctx,false);}
  private static void handleTransition(Context ctx,boolean idleTimeout){
    ActivityManager am=(ActivityManager)ctx.getSystemService(Context.ACTIVITY_SERVICE);
    if(am==null){circuitOpen=true;safeSleep(ctx);return;}
    List<ActivityManager.RunningTaskInfo> tasks=am.getRunningTasks(1);
    ActivityManager.RunningTaskInfo t=(tasks==null||tasks.isEmpty())?null:tasks.get(0);
    ComponentName top=t==null?null:t.topActivity;
    boolean isClock=top!=null && CLOCK_PACKAGE.equals(top.getPackageName())
                    && CLOCK_ACTIVITY.equals(top.getClassName());
    if(isClock){
      if(idleTimeout){
        Log.i(TAG,"AUTO_TIMEOUT_CLOCK_ALREADY_VISIBLE");
        return; // Timeout must never close the clock.
      }
      cancelTenMinuteCycle(ctx);
      Log.i(TAG,"CLOCK_EXIT broadcasting finish; saved reading task="+previousTask);
      Intent exit=new Intent(ACTION_EXIT);
      exit.setPackage(CLOCK_PACKAGE);
      ctx.sendBroadcast(exit);
      final int id=previousTask;
      previousTask=-1;
      if(id>0){
        worker.postDelayed(new Runnable(){
          @Override public void run(){
            try{
              am.moveTaskToFront(id,0);
              Log.i(TAG,"RESTORED_READING_TASK id="+id);
            }catch(Throwable e){Log.w(TAG,"Task restore fallback to Android recents",e);}
          }
        },450);
      }
      return;
    }

    Intent battery=ctx.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
    boolean plugged=battery!=null && battery.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)!=0;
    int level=battery==null?-1:battery.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
    if(!plugged && (level<LOW_BATTERY_STOCK_THRESHOLD)){
      Log.i(TAG,"LOW_BATTERY_STOCK_SLEEP level="+level);
      safeSleep(ctx);
      return;
    }
    previousTask=t==null?-1:t.id;
    Intent open=new Intent();
    open.setComponent(new ComponentName(CLOCK_PACKAGE,CLOCK_ACTIVITY));
    open.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP |
                  Intent.FLAG_ACTIVITY_NO_ANIMATION);
    ctx.startActivity(open);
    Log.i(TAG,(idleTimeout?"AUTO_TIMEOUT_CALENDAR_LAUNCHED":"OPENED_NATIVE_LIVE_CALENDAR")
        +" previousTask="+previousTask+" battery="+level+" plugged="+plugged);
  }

  private static void safeSleep(Context ctx){
    // Native sleep must never inherit the temporary auto-clock logo guard.
    suppressLogoUntilUptimeMs=0;
    try{
      PowerManager pm=(PowerManager)ctx.getSystemService(Context.POWER_SERVICE);
      if(pm!=null){
        Method sleep=PowerManager.class.getDeclaredMethod("goToSleep",long.class);
        sleep.setAccessible(true);
        sleep.invoke(pm,SystemClock.uptimeMillis());
      }
    }catch(Throwable e){Log.e(TAG,"Stock sleep fallback failed",e);}
  }
}
