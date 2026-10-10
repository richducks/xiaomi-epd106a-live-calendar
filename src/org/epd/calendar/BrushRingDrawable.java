package org.epd.calendar;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;

/**
 * Hand-drawn asymmetric ink circle around the current solar date.
 * Transparent: the printed date and lunar text stay dark, not white-on-black.
 * Pure vector Canvas drawing; no wallpaper and no bitmap dependencies.
 */
public final class BrushRingDrawable extends Drawable {
  private final Paint ink = new Paint(Paint.ANTI_ALIAS_FLAG);

  private float px(float dp,float density){ return dp*density; }

  private void stroke(Canvas c,float cx,float cy,float rx,float ry,
                      float from,float to,float width,int alpha,float wobble) {
    Path path=new Path();
    final int steps=60;
    for(int i=0;i<=steps;i++){
      float f=i/(float)steps;
      float a=from+(to-from)*f;
      float ripple=1f+(float)(Math.sin(3.1*a+0.4)*.026
                           +Math.sin(7.4*a-1.2)*.018)*wobble;
      float x=cx+(float)Math.cos(a)*rx*ripple;
      float y=cy+(float)Math.sin(a)*ry*ripple;
      if(i==0)path.moveTo(x,y);else path.lineTo(x,y);
    }
    ink.reset();
    ink.setAntiAlias(true);
    ink.setStyle(Paint.Style.STROKE);
    ink.setStrokeCap(Paint.Cap.ROUND);
    ink.setStrokeJoin(Paint.Join.ROUND);
    ink.setStrokeWidth(width);
    ink.setColor(Color.BLACK);
    ink.setAlpha(alpha);
    c.drawPath(path,ink);
  }

  @Override public void draw(Canvas canvas) {
    Rect b=getBounds();
    float density=android.content.res.Resources.getSystem().getDisplayMetrics().density;
    float cx=b.exactCenterX(), cy=b.exactCenterY();
    float rx=Math.min(b.width()*.32f,px(31,density));
    float ry=Math.min(b.height()*.44f,px(23,density));
    if(rx<8||ry<8)return;
    // Distinct brush strokes with a slight gap at 2 o'clock, intentional
    // non-circular wobble and variable density: no solid boxed highlight.
    stroke(canvas,cx,cy,rx,ry,-.85f,2.30f,px(3.4f,density),235,1f);
    stroke(canvas,cx-1.1f,cy+.8f,rx*.97f,ry*1.02f,2.23f,5.45f,px(2.15f,density),222,1.2f);
    stroke(canvas,cx+1f,cy-1f,rx*.985f,ry*.97f,5.19f,5.83f,px(1.2f,density),150,.9f);
    // Dry-brush trailing line. Never covers digits in the center.
    stroke(canvas,cx-1.5f,cy-1f,rx*1.032f,ry*.972f,1.88f,2.56f,
           px(.9f,density),115,1.6f);
  }
  @Override public void setAlpha(int alpha){ink.setAlpha(alpha);invalidateSelf();}
  @Override public void setColorFilter(ColorFilter filter){ink.setColorFilter(filter);invalidateSelf();}
  @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
}
