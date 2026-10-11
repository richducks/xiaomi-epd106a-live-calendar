package org.epd.neat.touchzones;

import android.app.Activity;
import android.graphics.Color;
import android.util.Log;
import android.view.Window;
import android.view.WindowManager;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.Gravity;
import android.widget.FrameLayout;
import java.util.WeakHashMap;
import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

/**
 * App-specific compatibility layer. Do not hook system_server, Duokan,
 * key events or NeatReader's protected ebook parsing engine.
 *
 * A center tap shows the two native NeatReader toolbars together with
 * the OEM status bar (Home, Back, Wi-Fi and battery). Neither menu obscures
 * the other: the notification shade is never expanded.
 * Outside the center zone, original paging and gestures are unchanged.
 */
public final class NeatTouchZones implements IXposedHookLoadPackage {
  private static final String TAG="NeatDuokanZones";
  private static final String PACKAGE="com.gzhi.neatreader.r2.main";
  private static final String READER="com.gzhi.neatreader.r2.navigator.reader.BookReaderActivity";
  private static final WeakHashMap<Activity,Zone> ZONES=new WeakHashMap<>();
  private static final long HOLD_FORWARD_MS=320L;
  private static final float ZONE_X=.33f,ZONE_Y=.35f,ZONE_W=.34f,ZONE_H=.30f;

  private static boolean isReader(Activity a){
    return READER.equals(a.getClass().getName());
  }
  private static boolean enabled(){
    try{
      Class<?> p=Class.forName("android.os.SystemProperties");
      String value=(String)p.getMethod("get",String.class,String.class)
          .invoke(null,"persist.epd.neatzones","0");
      return "1".equals(value);
    }catch(Throwable t){
      return false; // opt-in only: failure leaves NeatReader fully native
    }
  }
  private static boolean autoIdleEnabled(){
    try{
      Class<?> p=Class.forName("android.os.SystemProperties");
      String value=(String)p.getMethod("get",String.class,String.class)
          .invoke(null,"persist.epd.autoclock","0");
      return "1".equals(value);
    }catch(Throwable t){return false;}
  }
  @Override public void handleLoadPackage(XC_LoadPackage.LoadPackageParam p) throws Throwable {
    if(!PACKAGE.equals(p.packageName)||!PACKAGE.equals(p.processName))return;
    XposedHelpers.findAndHookMethod(Activity.class,"onResume",new XC_MethodHook(){
      @Override protected void afterHookedMethod(MethodHookParam p){
        Activity a=(Activity)p.thisObject;
        if(!isReader(a))return;
        View decor=a.getWindow().getDecorView();
        decor.postDelayed(()->attach(a),250L);
        decor.postDelayed(()->attach(a),900L);
      }
    });
    XposedHelpers.findAndHookMethod(Activity.class,"onWindowFocusChanged",
        boolean.class,new XC_MethodHook(){
      @Override protected void afterHookedMethod(MethodHookParam p){
        Activity a=(Activity)p.thisObject;
        if(isReader(a)&&Boolean.TRUE.equals(p.args[0]))
          a.getWindow().getDecorView().postDelayed(()->attach(a),200L);
      }
    });
    XposedHelpers.findAndHookMethod(Activity.class,"onPause",new XC_MethodHook(){
      @Override protected void beforeHookedMethod(MethodHookParam p){
        Activity a=(Activity)p.thisObject;
        if(isReader(a)){
          Zone old=ZONES.remove(a);
          if(old!=null)old.detach();
        }
      }
    });
    XposedBridge.log("NEAT_DUAL_MENU_HOOK_LOADED reader-scoped only");
  }
  private static int id(Activity a,String name){
    return a.getResources().getIdentifier(name,"id",PACKAGE);
  }
  private static View control(Activity a,String name){
    int i=id(a,name);
    return i==0?null:a.findViewById(i);
  }
  private static void attach(Activity a){
    try{
      if(!enabled()||a.isFinishing()||!isReader(a)||ZONES.containsKey(a))return;
      View decor=a.getWindow().getDecorView();
      if(!(decor instanceof FrameLayout)||decor.getWidth()<200||decor.getHeight()<200)return;
      View top=control(a,"ll_layer_top");
      View bottom=control(a,"ll_layer_bot");
      if(top==null||bottom==null){
        XposedBridge.log("NEAT_NATIVE_LAYERS_MISSING top="+(top!=null)+" bottom="+(bottom!=null));
        return; // No interception if native menus are absent.
      }
      Zone zone=new Zone(a,(FrameLayout)decor,top,bottom);
      zone.attach();
      ZONES.put(a,zone);
      zone.allowIdleTimeout();
      XposedBridge.log("NEAT_DUAL_MENU_READY "+decor.getWidth()+"x"+decor.getHeight());
    }catch(Throwable t){
      Log.e(TAG,"Failed to attach optional reader zone; native paging preserved",t);
    }
  }
  private static final class Zone implements View.OnTouchListener {
    final Activity activity;
    final FrameLayout decor;
    final View top,bottom;
    View center;
    boolean systemBarShown;
    boolean originallyFullscreen;
    int originalSystemUiFlags;
    boolean originalReaderKeepOn;
    MotionEvent originalDown;
    Runnable holdForward;
    boolean forwarding;
    float downX,downY;

    Zone(Activity a,FrameLayout d,View t,View b){
      activity=a;decor=d;top=t;bottom=b;
    }
    void attach(){
      center=new View(activity);
      center.setBackgroundColor(Color.TRANSPARENT);
      center.setClickable(true);
      int w=decor.getWidth(),h=decor.getHeight();
      FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(
          Math.round(w*ZONE_W),Math.round(h*ZONE_H),Gravity.LEFT|Gravity.TOP);
      lp.leftMargin=Math.round(w*ZONE_X);
      lp.topMargin=Math.round(h*ZONE_Y);
      decor.addView(center,lp);
      center.setOnTouchListener(this);
    }
    void allowIdleTimeout(){
      if(!autoIdleEnabled())return;
      android.view.Window window=activity.getWindow();
      originalReaderKeepOn=(window.getAttributes().flags &
          WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)!=0;
      if(originalReaderKeepOn){
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        XposedBridge.log("NEAT_ALLOW_IDLE_TIMEOUT_KEEP_ON_CLEARED");
      }
    }
    void restoreReaderKeepOn(){
      if(originalReaderKeepOn){
        activity.getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        originalReaderKeepOn=false;
        XposedBridge.log("NEAT_RESTORE_READER_KEEP_ON");
      }
    }
    void detach(){
      restoreReaderKeepOn();
      restoreSystemBar();
      stopHold();
      if(center!=null && center.getParent()==decor) decor.removeView(center);
      center=null;
    }
    void stopHold(){
      if(center!=null&&holdForward!=null)center.removeCallbacks(holdForward);
      holdForward=null;
      if(originalDown!=null){originalDown.recycle();originalDown=null;}
      forwarding=false;
    }
    void dispatchUnder(MotionEvent event){
      if(center==null)return;
      // Events from the center View are in its LOCAL coordinates. The
      // Activity's dispatchTouchEvent expects WINDOW coordinates instead.
      // Translate a COPY so native word selection and swipes still hit the
      // exact original point, without mutating the caller's MotionEvent.
      MotionEvent copy=MotionEvent.obtain(event);
      copy.offsetLocation(center.getLeft(),center.getTop());
      center.setVisibility(View.GONE);
      try{activity.dispatchTouchEvent(copy);}
      finally{center.setVisibility(View.VISIBLE);copy.recycle();}
    }
    void forwardDown(){
      if(forwarding||originalDown==null)return;
      forwarding=true;
      if(holdForward!=null&&center!=null)center.removeCallbacks(holdForward);
      dispatchUnder(originalDown);
    }
    private static final int HIDDEN_BAR_FLAGS =
        View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
        View.SYSTEM_UI_FLAG_IMMERSIVE | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY |
        View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
        View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
        View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
        View.SYSTEM_UI_FLAG_LOW_PROFILE;
    private void showSystemBar(){
      if(systemBarShown)return;
      Window window=activity.getWindow();
      originallyFullscreen=(window.getAttributes().flags &
          WindowManager.LayoutParams.FLAG_FULLSCREEN)!=0;
      originalSystemUiFlags=decor.getSystemUiVisibility();
      systemBarShown=true;
      // Expose the slim OEM bar, not an opaque notification shade.
      window.clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
      decor.setSystemUiVisibility(originalSystemUiFlags & ~HIDDEN_BAR_FLAGS);
      XposedBridge.log("NEAT_OEM_STATUS_BAR_SHOW");
    }
    private void restoreSystemBar(){
      if(!systemBarShown)return;
      Window window=activity.getWindow();
      if(originallyFullscreen)window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
      else window.clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
      decor.setSystemUiVisibility(originalSystemUiFlags);
      systemBarShown=false;
      XposedBridge.log("NEAT_OEM_STATUS_BAR_RESTORE");
    }
    private void toggleNativeMenu(){
      boolean show=top.getVisibility()!=View.VISIBLE
          ||bottom.getVisibility()!=View.VISIBLE;
      if(show)showSystemBar();
      else restoreSystemBar();
      top.setVisibility(show?View.VISIBLE:View.GONE);
      bottom.setVisibility(show?View.VISIBLE:View.GONE);
      top.invalidate();bottom.invalidate();
      XposedBridge.log("NEAT_ORIGINAL_READER_MENU_"+(show?"OPEN":"CLOSE"));
    }
    @Override public boolean onTouch(View view,MotionEvent e){
      try{
        int action=e.getActionMasked();
        switch(action){
          case MotionEvent.ACTION_DOWN:
            stopHold();
            originalDown=MotionEvent.obtain(e);
            downX=e.getX();downY=e.getY();
            forwarding=false;
            holdForward=()->{if(originalDown!=null)forwardDown();};
            center.postDelayed(holdForward,HOLD_FORWARD_MS);
            return true;
          case MotionEvent.ACTION_MOVE:
            if(!forwarding){
              int slop=ViewConfiguration.get(activity).getScaledTouchSlop();
              if(Math.abs(e.getX()-downX)>slop||Math.abs(e.getY()-downY)>slop)
                forwardDown();
            }
            if(forwarding)dispatchUnder(e);
            return true;
          case MotionEvent.ACTION_POINTER_DOWN:
          case MotionEvent.ACTION_POINTER_UP:
            if(!forwarding)forwardDown();
            if(forwarding)dispatchUnder(e);
            return true;
          case MotionEvent.ACTION_UP:
            if(forwarding)dispatchUnder(e);
            else toggleNativeMenu();
            stopHold();
            return true;
          case MotionEvent.ACTION_CANCEL:
            if(forwarding)dispatchUnder(e);
            stopHold();
            return true;
        }
        if(forwarding)dispatchUnder(e);
      }catch(Throwable t){
        Log.e(TAG,"Center touch failed; disabling this event only",t);
        stopHold();
      }
      return true;
    }
  }
}
