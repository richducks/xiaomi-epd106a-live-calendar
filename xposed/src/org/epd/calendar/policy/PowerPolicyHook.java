package org.epd.calendar.policy;

import android.app.ActivityManager;
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
            // The intercepted private method returns boolean, NOT void.
            // Returning false skips both sleep and OEM SuspendLogo.
            p.setResult(Boolean.FALSE);
            Log.i(TAG,"AUTO_TIMEOUT_INTERCEPT level="+level+" plugged="+plugged);
            worker.post(()->{
              try{handleTransition(ctx,true);}
              catch(Throwable ex){
                circuitOpen=true;
                Log.e(TAG,"AUTO_TIMEOUT_FAILED; falling back to stock sleep",ex);
                safeSleep(ctx);
              }finally{BUSY.set(false);}
            });
          }catch(Throwable ex){
            BUSY.set(false);
            circuitOpen=true;
            Log.e(TAG,"AUTO_TIMEOUT_GUARD_FAILED; letting stock sleep execute",ex);
          }
        }
      });
      XposedBridge.log("EPD_POLICY_AUTO_TIMEOUT_HOOK_READY opt-in "+AUTO_ENABLE);
    }catch(Throwable e){
      Log.e(TAG,"Idle timeout hook unavailable; stock sleep unchanged",e);
    }
    XposedBridge.log("EPD_POLICY_POWERPRESS_HOOK_INSTALLED disabled_by_default");
    Log.i(TAG,"LegacyPolicyHook installed; disabled by default unless "+ENABLE+"=1");
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
