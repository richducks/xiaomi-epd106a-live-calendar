package org.epd.neat.touchzones;

import android.app.Activity;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.SystemClock;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.lang.ref.WeakReference;
import java.util.WeakHashMap;
import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

/**
 * Small, NeatReader-only compatibility layer; no vendor code.
 *
 * All touch handling is by TWO transparent child Views in the NeatReader
 * window (not a global Activity.dispatchTouchEvent hook).
 * Center or upper-region tap -> lightweight in-window menu.
 * Native left/right pagination elsewhere remains untouched.
 * No PopupWindow / Dialog / separate full-screen Surface to flash on E Ink.
 */
public final class NeatTouchZones implements IXposedHookLoadPackage {
  static final String PKG="com.gzhi.neatreader.r2.main";
  static final String READER="com.gzhi.neatreader.r2.navigator.reader.BookReaderActivity";
  static final String TAG="NeatDuokanZones";
  static final WeakHashMap<Activity,Zones> ZONES=new WeakHashMap<>();
  static final ThreadLocal<Boolean> NATIVE_DISPATCH=new ThreadLocal<>();
  static int dp(Context c,int v){return Math.round(v*c.getResources().getDisplayMetrics().density);}
  static boolean isReader(Activity a){return READER.equals(a.getClass().getName());}
  @Override public void handleLoadPackage(XC_LoadPackage.LoadPackageParam p) throws Throwable {
    if(!PKG.equals(p.packageName)||!PKG.equals(p.processName))return;
    XposedHelpers.findAndHookMethod(Activity.class,"onWindowFocusChanged",boolean.class,new XC_MethodHook(){
      @Override protected void afterHookedMethod(MethodHookParam p){
        Activity a=(Activity)p.thisObject;
        if(!isReader(a)||!Boolean.TRUE.equals(p.args[0]))return;
        a.getWindow().getDecorView().postDelayed(()->attach(a),180);
      }
    });
    XposedHelpers.findAndHookMethod(Activity.class,"onPause",new XC_MethodHook(){
      @Override protected void afterHookedMethod(MethodHookParam p){
        Activity a=(Activity)p.thisObject;
        if(isReader(a)){Zones z=ZONES.remove(a);if(z!=null)z.detach();}
      }
    });
    XposedBridge.log("NEAT_MINIMAL_VIEW_OVERLAY_HOOK_LOADED NeatReader only");
  }
  static void attach(Activity a){
    try{
      if(a.isFinishing()||!isReader(a))return;
      if(ZONES.containsKey(a))return;
      View decor=a.getWindow().getDecorView();
      if(!(decor instanceof FrameLayout)||decor.getWidth()<200||decor.getHeight()<250)return;
      Zones z=new Zones(a,(FrameLayout)decor);
      ZONES.put(a,z);
      z.attach();
      XposedBridge.log("NEAT_IN_WINDOW_TOUCH_ZONES_ATTACHED "+decor.getWidth()+"x"+decor.getHeight());
      decor.postDelayed(()->applyFastRefreshIfEnabled(a),250);
    }catch(Throwable t){Log.e(TAG,"attach failed; stock reader remains",t);}
  }
  static void applyFastRefreshIfEnabled(Activity a){
    try{
      Class<?> system=Class.forName("android.os.SystemProperties");
      String opt=(String)system.getMethod("get",String.class,String.class)
          .invoke(null,"persist.epd.neatfast","0");
      if(!"1".equals(opt))return;
      View decor=a.getWindow().getDecorView();
      java.lang.reflect.Method get=View.class.getDeclaredMethod("getViewRootImpl");
      get.setAccessible(true);
      Object root=get.invoke(decor);
      if(root==null)return;
      java.lang.reflect.Method set=root.getClass().getDeclaredMethod("setRefreshMode",int.class);
      set.setAccessible(true);
      set.invoke(root,1); // only NeatReader window; no global refresh prop.
      XposedBridge.log("NEAT_DU_FAST_REFRESH_APPLIED");
    }catch(Throwable t){Log.w(TAG,"Optional DU mode unsupported",t);}
  }
  static final class Zones {
    final Activity a;
    final FrameLayout decor;
    View center,top;
    LinearLayout menu;
    Zones(Activity a,FrameLayout decor){this.a=a;this.decor=decor;}
    void attach(){
      final int w=decor.getWidth(),h=decor.getHeight();
      // Intentional small center zone: most of page remains native for
      // selecting words, swiping, and long pressing.
      center=zone("center",Math.round(w*.32f),Math.round(h*.34f),
          Math.round(w*.36f),Math.round(h*.32f));
      top=zone("top",Math.round(w*.19f),Math.round(h*.06f),
          Math.round(w*.62f),Math.round(h*.11f));
      buildMenuOnce();
    }
    View zone(String type,int x,int y,int w,int h){
      View zone=new View(a);
      zone.setBackgroundColor(Color.TRANSPARENT);
      zone.setClickable(true);
      FrameLayout.LayoutParams params=new FrameLayout.LayoutParams(w,h,Gravity.TOP|Gravity.LEFT);
      params.leftMargin=x;params.topMargin=y;
      decor.addView(zone,params);
      zone.setOnTouchListener(new View.OnTouchListener(){
        float downX,downY;
        long started;
        boolean moved;
        @Override public boolean onTouch(View v,MotionEvent e){
          switch(e.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
              downX=e.getX();downY=e.getY();started=SystemClock.uptimeMillis();moved=false;return true;
            case MotionEvent.ACTION_MOVE:
              int slop=ViewConfiguration.get(a).getScaledTouchSlop();
              if(Math.abs(e.getX()-downX)>slop||Math.abs(e.getY()-downY)>slop)moved=true;
              return true;
            case MotionEvent.ACTION_UP:
              if(!moved&&SystemClock.uptimeMillis()-started<420){
                toggleMenu();
                XposedBridge.log("NEAT_SMALL_ZONE_TAPPED "+type);
              }
              return true;
            case MotionEvent.ACTION_CANCEL:return true;
          }
          return true;
        }
      });
      return zone;
    }
    void detach(){
      if(menu!=null && menu.getParent()==decor)decor.removeView(menu);
      if(center!=null && center.getParent()==decor)decor.removeView(center);
      if(top!=null && top.getParent()==decor)decor.removeView(top);
      menu=null;
    }
    void closeMenu(){
      // INVISIBLE retains the exact layout slot; repeated add/remove of a View
      // can force WebView layout and provoke a reload/white blink on E-Ink.
      if(menu!=null)menu.setVisibility(View.INVISIBLE);
    }
    void toggleMenu(){
      if(menu==null)return;
      if(menu.getVisibility()==View.VISIBLE)closeMenu();else showMenu();
    }
    void buildMenuOnce(){
      // Render in NeatReader's existing window and KEEP the row attached.
      // No PopupWindow, dialog, additional Surface, or relayout on each tap.
      menu=new LinearLayout(a);
      menu.setOrientation(LinearLayout.HORIZONTAL);
      menu.setBackgroundColor(Color.WHITE);
      menu.setVisibility(View.INVISIBLE);
      FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(-1,dp(a,58),Gravity.BOTTOM);
      lp.bottomMargin=dp(a,70);
      decor.addView(menu,lp);
      addButton("上一页",()->pageTap(.14f));
      addButton("下一页",()->pageTap(.86f));
      addButton("更多设置",()->nativeTopMenu());
      addButton("关闭",this::closeMenu);
    }
    void showMenu(){
      if(menu==null)buildMenuOnce();
      menu.setVisibility(View.VISIBLE);
      menu.invalidate();
      XposedBridge.log("NEAT_IN_WINDOW_MENU_OPENED");
    }
    void addButton(String label,Runnable action){
      TextView v=new TextView(a);
      v.setText(label);v.setTextSize(15);v.setTypeface(Typeface.DEFAULT,Typeface.NORMAL);
      v.setTextColor(Color.BLACK);v.setGravity(Gravity.CENTER);
      menu.addView(v,new LinearLayout.LayoutParams(0,-1,1));
      v.setOnClickListener(view->action.run());
    }
    void pageTap(float fraction){
      closeMenu();
      // Use NeatReader's native left/right paging implementation, do not
      // reimplement pagination, network IO or protected EPUB internals.
      injectNativeTap(decor.getWidth()*fraction,decor.getHeight()*.5f);
    }
    void nativeTopMenu(){
      closeMenu();
      // Explicit opt-in to original NeatReader settings: may still trigger
      // its original full-screen refresh, unlike this fast in-window menu.
      injectNativeTap(decor.getWidth()*.50f,decor.getHeight()*.08f);
    }
    void injectNativeTap(float x,float y){
      a.getWindow().getDecorView().postDelayed(()->{
        boolean hiddenC=center!=null && center.getVisibility()==View.VISIBLE;
        boolean hiddenT=top!=null && top.getVisibility()==View.VISIBLE;
        if(hiddenC)center.setVisibility(View.GONE);
        if(hiddenT)top.setVisibility(View.GONE);
        long time=SystemClock.uptimeMillis();
        MotionEvent down=MotionEvent.obtain(time,time,MotionEvent.ACTION_DOWN,x,y,0);
        MotionEvent up=MotionEvent.obtain(time,time+60,MotionEvent.ACTION_UP,x,y,0);
        try{a.dispatchTouchEvent(down);a.dispatchTouchEvent(up);}
        catch(Throwable t){Log.e(TAG,"native page tap failed",t);}
        finally{
          down.recycle();up.recycle();
          if(hiddenC)center.setVisibility(View.VISIBLE);
          if(hiddenT)top.setVisibility(View.VISIBLE);
        }
      },50);
    }
  }
}
