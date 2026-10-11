package org.epd.calendar;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import android.icu.util.ChineseCalendar;
import android.icu.util.ULocale;
import java.text.SimpleDateFormat;
import java.util.*;

public class MainActivity extends Activity {
  static final TimeZone TZ=TimeZone.getTimeZone("Asia/Shanghai");
  static final String[] W={"一","二","三","四","五","六","日"};
  static final String[] WEEK={"日","一","二","三","四","五","六"};
  static final String[] MONTH={"正","二","三","四","五","六","七","八","九","十","冬","腊"};
  static final String[] D={"一","二","三","四","五","六","七","八","九","十"};
  static final String[] SOL={"小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种","夏至","小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至"};
  static final int[] SOLMIN={0,21208,42467,63836,85337,107014,128867,150921,173149,195551,218072,240693,263343,285989,308563,331033,353350,375494,397447,419210,440795,462224,483532,504758};
  TextView clock,solar,batteryView;
  LinearLayout calendar;
  int dateKey=-1;
  int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
  TextView text(String s,int size,boolean bold,int color){
    TextView v=new TextView(this);v.setText(s);v.setTextColor(color);v.setTextSize(size);v.setGravity(Gravity.CENTER);v.setIncludeFontPadding(false);
    if(bold)v.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);
    return v;
  }
  LinearLayout vert(){LinearLayout v=new LinearLayout(this);v.setOrientation(1);v.setBackgroundColor(Color.WHITE);return v;}
  void add(LinearLayout p,View v,int h){p.addView(v,new LinearLayout.LayoutParams(-1,dp(h)));}
  final Handler handler=new Handler(Looper.getMainLooper());
  final Runnable tick=new Runnable(){@Override public void run(){
    android.util.Log.i("EinkCalendar","foreground per-minute refresh");
    update();applyPowerPolicy();scheduleTick();
  }};
  final BroadcastReceiver powerChanges=new BroadcastReceiver(){
    @Override public void onReceive(Context c,Intent i){applyPowerPolicy();update();}
  };
  // System lockscreen integration: finish only this Activity on the second
  // power-key press; previous reader task remains in Android's task stack.
  final BroadcastReceiver requestExit=new BroadcastReceiver(){
    @Override public void onReceive(Context c,Intent i){
      android.util.Log.i("EinkCalendar","EXIT_CLOCK_REQUEST_FROM_SYSTEM_POLICY");
      finish();
    }
  };
  static final int MIN_BATTERY_TO_REMAIN_ON=25;
  boolean batteryCutoffApplied=false;
  void applyPowerPolicy(){
    // While this is the visible clock, keep the e-ink panel active for real HH:mm.
    // Unlike the vendor's static lock wallpaper, an Android Activity cannot repaint
    // while Display Power is OFF.  Low-battery fail-safe avoids full discharge.
    Intent b=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
    boolean external=b!=null&&b.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)!=0;
    int level=b==null?-1:b.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
    if(!external&&(level<0||level<=MIN_BATTERY_TO_REMAIN_ON)){
      getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
      if(!batteryCutoffApplied){
        batteryCutoffApplied=true;
        android.util.Log.w("EinkCalendar","BATTERY_CLOCK_STOP level="+level+" power="+external);
        finish();
      }
      return;
    }
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    android.util.Log.d("EinkCalendar","CLOCK_STAYS_ON external="+external+" battery="+level);
  }
  // Use the firmware's per-layer EINK DU mode when available (no direct kernel ioctl).
  boolean triedEinkMode=false;
  void setupEinkMode(){
    if(triedEinkMode)return;
    triedEinkMode=true;
    try {
      View decor=getWindow().getDecorView();
      java.lang.reflect.Method get=View.class.getDeclaredMethod("getViewRootImpl");
      get.setAccessible(true);
      Object root=get.invoke(decor);
      if(root==null)throw new IllegalStateException("View root not ready");
      // EPD106A's firmware directly exposes ViewRootImpl.setRefreshMode(int).
      java.lang.reflect.Method mode=root.getClass().getDeclaredMethod("setRefreshMode",int.class);
      mode.setAccessible(true);
      mode.invoke(root,1); // Allwinner EINK_DU_MODE; affects only this application's layer.
      android.util.Log.i("EinkCalendar","EINK_PARTIAL_LAYER_ENABLED (ViewRootImpl DU mode=1)");
    }catch(Throwable e){
      android.util.Log.w("EinkCalendar","EINK_PARTIAL_LAYER_UNAVAILABLE: "+e);
    }
  }
  @Override public void onWindowFocusChanged(boolean focused){
    super.onWindowFocusChanged(focused);
    if(focused)getWindow().getDecorView().postDelayed(this::setupEinkMode,500);
  }
  boolean isTenMinuteExperiment(){
    try{
      Class<?> p=Class.forName("android.os.SystemProperties");
      String value=(String)p.getMethod("get",String.class,String.class)
          .invoke(null,"persist.epd.tenmin","0");
      return "1".equals(value);
    }catch(Throwable e){return false;}
  }
  void scheduleTick(){
    handler.removeCallbacks(tick);
    if(isTenMinuteExperiment()){
      android.util.Log.i("EinkCalendar","TENMIN_FOREGROUND_MINUTE_TICK_DISABLED");
      return;
    }
    long now=System.currentTimeMillis();
    long delay=60000L-(now%60000L);
    handler.postDelayed(tick,delay);
    android.util.Log.i("EinkCalendar","next foreground tick in "+delay+" ms");
  }
  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,WindowManager.LayoutParams.FLAG_FULLSCREEN);
    // Draw the native clock above the keyguard. This app never modifies a vendor PNG.
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                         WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
    layout();update();
    // Normal app launch opens a real live clock until the user touches to exit.
    // An explicit test_lifespan_ms extra retains the bounded four-minute test mode.
    int lifespan=getIntent().getIntExtra("test_lifespan_ms",0);
    if(lifespan>=20000 && lifespan<=240000){
      final int testLifespan=lifespan;
      handler.postDelayed(()->{
        android.util.Log.i("EinkCalendar","AUTO_STOP_PREVIEW_AFTER_TEST lifespan="+testLifespan);
        finish();
      },testLifespan);
    }
  }
  @Override protected void onNewIntent(Intent intent){
    super.onNewIntent(intent);
    setIntent(intent);
    if(intent!=null&&intent.getBooleanExtra("tenmin_rtc_refresh",false)){
      update();
      clock.invalidate();
      android.util.Log.i("EinkCalendar","TENMIN_RTC_REFRESH_APPLIED text="+clock.getText());
    }
  }
  @Override protected void onResume(){
    super.onResume();
    IntentFilter powerFilter=new IntentFilter(Intent.ACTION_POWER_CONNECTED);
    powerFilter.addAction(Intent.ACTION_POWER_DISCONNECTED);
    powerFilter.addAction(Intent.ACTION_BATTERY_CHANGED);
    registerReceiver(powerChanges,powerFilter);
    registerReceiver(requestExit,new IntentFilter("org.epd.calendar.EXIT_CLOCK"));
    applyPowerPolicy();update();scheduleTick();
  }
  @Override protected void onPause(){
    handler.removeCallbacks(tick);
    unregisterReceiver(powerChanges);
    unregisterReceiver(requestExit);
    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    super.onPause();
  }
  void layout(){
    LinearLayout root=vert();
    root.setPadding(dp(16),dp(15),dp(16),dp(28));
    setContentView(root);
    // One tap returns to the previous reading page; there are no controls on the clock face.
    root.setOnClickListener(v->finish());
    // The top title was redundant: time now occupies the whole top region.
    clock=text("--:--",112,true,Color.BLACK);
    clock.setTypeface(Typeface.create("sans-serif-condensed",Typeface.BOLD));
    add(root,clock,153);
    View line=new View(this);line.setBackgroundColor(Color.BLACK);add(root,line,2);
    calendar=vert();
    root.addView(calendar,new LinearLayout.LayoutParams(-1,0,1));
    View line2=new View(this);line2.setBackgroundColor(Color.BLACK);add(root,line2,2);
    // Compact footer: solar terms on the left, live battery percentage on the right.
    // Reuse the existing 40dp footer rather than adding another screen section.
    LinearLayout footer=new LinearLayout(this);
    footer.setOrientation(LinearLayout.HORIZONTAL);
    footer.setGravity(Gravity.CENTER_VERTICAL);
    footer.setBackgroundColor(Color.WHITE);
    solar=text("",15,false,Color.DKGRAY);
    solar.setGravity(Gravity.CENTER_VERTICAL | Gravity.LEFT);
    footer.addView(solar,new LinearLayout.LayoutParams(0,dp(40),1));
    batteryView=text("电量 --%",15,true,Color.BLACK);
    batteryView.setGravity(Gravity.CENTER_VERTICAL | Gravity.RIGHT);
    footer.addView(batteryView,new LinearLayout.LayoutParams(dp(124),dp(40)));
    add(root,footer,40);
  }
  static String dayName(int d){
    if(d==10)return "初十";if(d==20)return "二十";if(d==30)return "三十";
    return new String[]{"初","十","廿"}[(d-1)/10]+D[(d-1)%10];
  }
  static ChineseCalendar chinese(long millis){
    ChineseCalendar c=new ChineseCalendar(android.icu.util.TimeZone.getTimeZone("Asia/Shanghai"),ULocale.SIMPLIFIED_CHINESE);
    c.setTimeInMillis(millis);return c;
  }
  static String lunarName(long millis,boolean shortForm){
    ChineseCalendar c=chinese(millis);
    int m=c.get(ChineseCalendar.MONTH),d=c.get(ChineseCalendar.DAY_OF_MONTH);
    if(m<0||m>11||d<1||d>30)return "?";
    String mname=(c.get(ChineseCalendar.IS_LEAP_MONTH)==1?"闰":"")+MONTH[m]+"月";
    if(shortForm)return d==1?mname:dayName(d);
    return mname+dayName(d);
  }
  static int solarDay(int y,int term){
    GregorianCalendar utc=new GregorianCalendar(TZ);utc.clear();utc.set(1900,0,6,2,5);
    long ms=utc.getTimeInMillis()+(long)(31556925974.7*(y-1900))+(long)SOLMIN[term]*60000L;
    GregorianCalendar cn=new GregorianCalendar(TZ);cn.setTimeInMillis(ms);return cn.get(Calendar.DAY_OF_MONTH);
  }
  void update(){
    Calendar n=Calendar.getInstance(TZ,Locale.CHINA);
    int y=n.get(Calendar.YEAR),m=n.get(Calendar.MONTH),d=n.get(Calendar.DAY_OF_MONTH);
    SimpleDateFormat fmt=new SimpleDateFormat("HH:mm",Locale.CHINA);fmt.setTimeZone(TZ);
    String hhmm=fmt.format(n.getTime());
    clock.setText(hhmm);
    solar.setText("节气（估） "+SOL[m*2]+solarDay(y,m*2)+"日 · "+SOL[m*2+1]+solarDay(y,m*2+1)+"日");
    // Sticky ACTION_BATTERY_CHANGED is the Android source of truth.
    // Avoid hard-coded percentages and avoid polling a privileged battery service.
    Intent status=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
    int level=status==null?-1:status.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
    int scale=status==null?-1:status.getIntExtra(BatteryManager.EXTRA_SCALE,-1);
    if(batteryView!=null){
      if(level>=0 && scale>0){
        int percent=Math.max(0,Math.min(100,(level*100+scale/2)/scale));
        batteryView.setText("电量 "+percent+"%");
      }else{
        batteryView.setText("电量 --%");
      }
    }
    int key=y*10000+(m+1)*100+d;
    if(key!=dateKey){drawMonth(y,m,d);dateKey=key;}
  }
  void drawMonth(int year,int month,int today){
    calendar.removeAllViews();
    add(calendar,text(year+" 年 "+(month+1)+" 月",23,true,Color.BLACK),39);
    LinearLayout weekday=new LinearLayout(this);
    for(String w:W)weekday.addView(text(w,17,true,Color.DKGRAY),new LinearLayout.LayoutParams(0,dp(30),1));
    add(calendar,weekday,30);
    GregorianCalendar start=new GregorianCalendar(TZ,Locale.CHINA);start.clear();start.set(year,month,1,12,0);
    start.add(Calendar.DAY_OF_MONTH,-((start.get(Calendar.DAY_OF_WEEK)+5)%7));
    for(int r=0;r<6;r++){
      LinearLayout row=new LinearLayout(this);
      for(int col=0;col<7;col++){
        Calendar c=(Calendar)start.clone();c.add(Calendar.DAY_OF_MONTH,r*7+col);
        boolean same=c.get(Calendar.MONTH)==month,selected=same&&c.get(Calendar.DAY_OF_MONTH)==today;
        int color=same?Color.BLACK:0xFF999999;
        LinearLayout box=vert();box.setGravity(Gravity.CENTER);
        // Brush-ring only around the solar date; lunar stays outside.
        TextView number=text(""+c.get(Calendar.DAY_OF_MONTH),21,selected,color);
        if(selected)number.setBackground(new BrushRingDrawable());
        add(box,number,46);
        add(box,text(lunarName(c.getTimeInMillis(),true),11,false,color),18);
        row.addView(box,new LinearLayout.LayoutParams(0,-1,1));
      }
      calendar.addView(row,new LinearLayout.LayoutParams(-1,0,1));
    }
  }
}
