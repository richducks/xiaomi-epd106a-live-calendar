(()=>{
"use strict";
const W=758,H=1024,STORAGE_KEY="eink-studio-layout-v3",LEGACY_STORAGE_KEY="eink-studio-layout-v2";
const WEEK=["一","二","三","四","五","六","日"];
const SOLAR=["小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","夏至","小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至"];
const FULL_SOLAR=["小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种","夏至","小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至"];
const SOLAR_MINS=[0,21208,42467,63836,85337,107014,128867,150921,173149,195551,218072,240693,263343,285989,308563,331033,353350,375494,397447,419210,440795,462224,483532,504758];
const DIGITS=["一","二","三","四","五","六","七","八","九","十"];
const MONTH_NAMES=["正","二","三","四","五","六","七","八","九","十","冬","腊"];
const defs=[
 {id:"month",name:"月份标题",icon:"▱",desc:"月历上方的年份和月份",size:[18,60]},
 {id:"clock",name:"实时时钟",icon:"◷",desc:"北京时间 · HH:mm · 每分钟更新",size:[20,110]},
 {id:"grid",name:"月历网格",icon:"▦",desc:"7 列公历、农历和选中日期",size:[15,56]},
 {id:"solar",name:"二十四节气",icon:"◷",desc:"当月两个节气的估算日期",size:[12,40]}
];
const defaults={
 month:{x:379,y:171,w:650,h:62,font:35,visible:true},
 clock:{x:379,y:26,w:600,h:134,font:116,visible:true},
 grid:{x:34,y:254,w:690,h:619,font:39,visible:true},
 solar:{x:379,y:939,w:685,h:43,font:21,visible:true}
};
const presets={
 classic:{},
 minimal:{
  month:{x:379,y:211,font:33},
  clock:{x:379,y:31,font:146},
  grid:{x:42,y:290,w:674,h:529,font:40},
  solar:{x:379,y:933,font:20,visible:false}
 },
 compact:{
  month:{x:379,y:150,font:33},
  clock:{x:379,y:23,font:103},
  grid:{x:28,y:226,w:702,h:654,font:39},
  solar:{x:379,y:938,font:21}
 }
};
const $=id=>document.getElementById(id),canvas=$("calendarCanvas"),ctx=canvas.getContext("2d");
let state,active="grid",guide=true,clean=false,dragging=null,toastTimer=null,saveTimer=null;
function nowShanghai(){return new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());}
function localParts(){return new Intl.DateTimeFormat("en-US",{timeZone:"Asia/Shanghai",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());}
function todayISO(){const p=Object.fromEntries(localParts().map(x=>[x.type,x.value]));return p.year+"-"+p.month+"-"+p.day;}
function base(){return {version:3,device:"EPD106A",resolution:{width:W,height:H},date:todayISO(),preset:"classic",global:{fontFamily:"sans",palette:"normal",showLunar:true,showSolar:true,highlightToday:true},modules:structuredClone(defaults)};}
function sanitize(raw){
 if(!raw || typeof raw!=="object"||raw.device!=="EPD106A"||![1,2,3].includes(raw.version))throw Error("不是本编辑器支持的 EPD106A 配置");
 const s=base();if(/^20\d\d-\d\d-\d\d$/.test(raw.date||""))s.date=raw.date;
 if(raw.version>=2&&["classic","minimal","compact","custom"].includes(raw.preset))s.preset=raw.preset;
 for(const k of Object.keys(s.global))if(typeof raw.global?.[k]===typeof s.global[k])s.global[k]=raw.global[k];
 if(!["sans","serif","mono"].includes(s.global.fontFamily))s.global.fontFamily="sans";
 if(!["normal","soft","invert"].includes(s.global.palette))s.global.palette="normal";
 for(const key of Object.keys(defaults)){
  const candidate=raw.version>=2?raw.modules?.[key]:null;if(!candidate||typeof candidate!=="object")continue;
  for(const prop of ["x","y","w","h","font"]){
   if(Number.isFinite(candidate[prop]))s.modules[key][prop]=Math.max(prop==="font"?8:0,Math.min(prop==="font"?240:prop==="x"||prop==="w"?W:H,candidate[prop]));
  }
  if(typeof candidate.visible==="boolean")s.modules[key].visible=candidate.visible;
  if(typeof candidate.text==="string"&&"text" in s.modules[key])s.modules[key].text=candidate.text.slice(0,36);
 }
 // Layout version 3 uses the former unused title area for a large centered clock.
 // Preserve hand-edited v2 arrangements, but migrate stock v2 presets to new placements.
 if(raw.version===2 && s.preset!=="custom"){
  const fresh=structuredClone(defaults);
  for(const [key,override] of Object.entries(presets[s.preset]||{}))Object.assign(fresh[key],override);
  s.modules=fresh;
 }
 return s;
}
function load(){
 try{
  const current=localStorage.getItem(STORAGE_KEY);
  if(current)return sanitize(JSON.parse(current));
  const previous=localStorage.getItem(LEGACY_STORAGE_KEY);
  if(previous){
   const migrated=sanitize(JSON.parse(previous));
   // One-time migration keeps the user's date, colors and edited positions.
   // Built-in v2 presets move their clock into the old title area.
   localStorage.setItem(STORAGE_KEY,JSON.stringify(migrated));
   return migrated;
  }
  return base();
 }catch(e){console.warn(e);return base();}
}
state=load();
function save(silent=true){
 localStorage.setItem(STORAGE_KEY,JSON.stringify(state));
 if(!silent)notify("排版已保存到当前浏览器");
}
function scheduleSave(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>save(true),160);}
function notify(text){const t=$("toast");t.textContent=text;t.classList.add("visible");clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove("visible"),2400);}
function dayDate(iso){const p=iso.split("-").map(Number);return new Date(Date.UTC(p[0],p[1]-1,p[2],12,0,0));}
function formatISO(d){return d.getUTCFullYear()+"-"+String(d.getUTCMonth()+1).padStart(2,"0")+"-"+String(d.getUTCDate()).padStart(2,"0");}
function lunarParts(d){
 try{
  const fmt=new Intl.DateTimeFormat("zh-CN-u-ca-chinese",{month:"long",day:"numeric",timeZone:"Asia/Shanghai"});
  const map=Object.fromEntries(fmt.formatToParts(d).map(p=>[p.type,p.value]));
  const n=Number(map.day);
  const monthRaw=String(map.month||"");
  let month=monthRaw.replace(/月$/,"");
  month=month==="十一"?"冬":month==="十二"?"腊":month==="一"?"正":month;
  const str=(n===10?"初十":n===20?"二十":n===30?"三十":n<=10?"初"+DIGITS[n-1]:n<20?"十"+DIGITS[n-11]:"廿"+DIGITS[n-21]);
  return {short:n===1?month+"月":str,full:month+"月"+str};
 }catch(e){return {short:"",full:"农历不可用"};}
}
function solarDay(year,index){
 const ms=Date.UTC(1900,0,5,18,5,0)+31556925974.7*(year-1900)+SOLAR_MINS[index]*60000;
 const parts=new Intl.DateTimeFormat("en-US",{timeZone:"Asia/Shanghai",day:"numeric"}).formatToParts(new Date(ms));
 return Number(parts.find(p=>p.type==="day").value);
}
function palette(){return state.global.palette==="invert"?{bg:"#202420",ink:"#f7f8f4",sub:"#d4d8d1",muted:"#aaa"}:
 state.global.palette==="soft"?{bg:"#fff",ink:"#454a46",sub:"#666b65",muted:"#888"}:
 {bg:"#fff",ink:"#101312",sub:"#282b28",muted:"#777"};}
function fontFamily(){return state.global.fontFamily==="serif"?"'Noto Serif CJK SC','SimSun','STSong',serif":
 state.global.fontFamily==="mono"?"'Noto Sans Mono CJK SC','WenQuanYi Zen Hei Mono',monospace":
 "'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif";}
function text(s,x,y,size,weight,align="center",color){
 ctx.font=weight+" "+size+"px "+fontFamily();ctx.textBaseline="top";ctx.textAlign=align;ctx.fillStyle=color||palette().ink;
 ctx.fillText(String(s),x,y);
}
function line(x1,y1,x2,y2,color,width=2){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();}
function brushCircle(cx,cy,rx,ry,color){
 // Same asymmetric, broken brush stroke as the native Android date marker.
 const strokes=[[-.85,2.30,3.8,1,1],[2.23,5.45,2.4,.94,1.2],[5.19,5.83,1.25,.70,.9]];
 ctx.save();ctx.lineCap="round";ctx.lineJoin="round";ctx.strokeStyle=color;
 for(const [start,end,width,opacity,wobble] of strokes){
  ctx.globalAlpha=opacity;ctx.lineWidth=width;ctx.beginPath();
  for(let i=0;i<=60;i++){
   const a=start+(end-start)*i/60;
   const ripple=1+(Math.sin(3.1*a+.4)*.026+Math.sin(7.4*a-1.2)*.018)*wobble;
   const x=cx+Math.cos(a)*rx*ripple,y=cy+Math.sin(a)*ry*ripple;
   if(!i)ctx.moveTo(x,y);else ctx.lineTo(x,y);
  }
  ctx.stroke();
 }
 ctx.restore();
}
function clockText(){
 const parts=new Intl.DateTimeFormat("en-GB",{hour:"2-digit",minute:"2-digit",hour12:false,timeZone:"Asia/Shanghai"}).formatToParts(new Date());
 const map=Object.fromEntries(parts.map(p=>[p.type,p.value]));
 return map.hour+":"+map.minute;
}
function render(withUI=true){
 const pal=palette(),m=state.modules,g=state.global;
 ctx.clearRect(0,0,W,H);ctx.fillStyle=pal.bg;ctx.fillRect(0,0,W,H);
 const date=dayDate(state.date),year=date.getUTCFullYear(),month=date.getUTCMonth()+1,day=date.getUTCDate();
 const week=(date.getUTCDay()+6)%7;
 if(m.month.visible)text(year+"年 "+month+"月",m.month.x,m.month.y,m.month.font,700,"center",pal.ink);
 if(m.clock.visible)text(clockText(),m.clock.x,m.clock.y,m.clock.font,730,"center",pal.ink);
 if(m.grid.visible){
  const x=m.grid.x,y=m.grid.y,w=m.grid.w,h=m.grid.h,cellW=w/7;
  const first=new Date(Date.UTC(year,month-1,1,12)),offset=(first.getUTCDay()+6)%7;
  const daysInMonth=new Date(Date.UTC(year,month,0,12)).getUTCDate();
  const rowCount=Math.ceil((offset+daysInMonth)/7);
  const headerH=65,rowH=(h-headerH)/rowCount;
  for(let i=0;i<7;i++)text(WEEK[i],x+(i+.5)*cellW,y,m.grid.font*.70,700,"center",pal.ink);
  line(x,y+52,x+w,y+52,pal.ink,2);
  for(let n=1;n<=daysInMonth;n++){
   const ix=offset+n-1,r=Math.floor(ix/7),col=ix%7,left=x+col*cellW,top=y+headerH+r*rowH;
   const marked=g.highlightToday&&n===day;
   if(marked)brushCircle(left+cellW/2,top+16+m.grid.font*.52,Math.min(cellW*.37,m.grid.font*.83),m.grid.font*.76,pal.ink);
   text(n,left+cellW/2,top+16,m.grid.font,marked?700:520,"center",pal.ink);
   if(g.showLunar)text(lunarParts(new Date(Date.UTC(year,month-1,n,12))).short,left+cellW/2,top+21+m.grid.font+8,Math.max(12,Math.round(m.grid.font*.43)),400,"center",pal.muted);
  }
 }
 if(m.solar.visible&&g.showSolar){
  line(36,m.solar.y-20,W-36,m.solar.y-20,pal.ink,2);
  const idx=(month-1)*2;
  text("节气（估算）："+FULL_SOLAR[idx]+" "+solarDay(year,idx)+"日 · "+FULL_SOLAR[idx+1]+" "+solarDay(year,idx+1)+"日",
       m.solar.x,m.solar.y,m.solar.font,450,"center",pal.sub);
 }
 if(withUI && !clean){
  if(guide){ctx.save();ctx.strokeStyle="rgba(48,121,77,.16)";ctx.setLineDash([9,9]);ctx.lineWidth=1;ctx.strokeRect(31,31,W-62,H-62);ctx.restore();}
  const a=m[active];if(a.visible){
   const b=bounds(active,a);ctx.save();ctx.strokeStyle="rgba(26,115,77,.85)";ctx.setLineDash([8,5]);ctx.lineWidth=2;
   ctx.strokeRect(b.x,b.y,b.w,b.h);ctx.setLineDash([]);ctx.fillStyle="rgba(36,112,72,.94)";
   for(const [sx,sy] of [[b.x,b.y],[b.x+b.w,b.y],[b.x,b.y+b.h],[b.x+b.w,b.y+b.h]])ctx.fillRect(sx-4,sy-4,8,8);
   ctx.restore();
  }
 }
}
function bounds(key,v){
 switch(key){
 case "month":return{x:v.x-v.w/2,y:v.y-9,w:v.w,h:Math.max(45,v.font+17)};
 case "clock":return{x:v.x-v.w/2,y:v.y-8,w:v.w,h:Math.max(55,v.font+18)};
 case "grid":return{x:v.x-7,y:v.y-8,w:v.w+14,h:v.h+16};
 case "solar":return{x:v.x-v.w/2,y:v.y-16,w:v.w,h:Math.max(45,v.font+18)};
 }
}
function mutate(){state.preset="custom";scheduleSave();render();reflectPresets();}
function reflectPresets(){document.querySelectorAll(".preset").forEach(b=>{b.classList.toggle("active",b.dataset.preset===state.preset);});}
function buildLayers(){
 const out=$("moduleList");out.replaceChildren();
 for(const x of defs){
  const m=state.modules[x.id],btn=document.createElement("button");
  btn.type="button";btn.className="module-item"+(active===x.id?" active":"");
  btn.setAttribute("aria-pressed",active===x.id?"true":"false");
  btn.innerHTML='<span class="module-ico">'+x.icon+'</span><span class="module-label">'+x.name+'</span><span class="module-eye '+(m.visible?"":"off")+'" title="显示或隐藏模块">'+(m.visible?"◉":"○")+'</span>';
  btn.addEventListener("click",e=>{if(e.target.closest(".module-eye")){m.visible=!m.visible;mutate();buildLayers();}else select(x.id);});
  out.append(btn);
 }
 $("layerCount").textContent=defs.filter(d=>state.modules[d.id].visible).length;
}
function select(id){
 active=id;const m=state.modules[id],d=defs.find(x=>x.id===id);
 $("selectedIcon").textContent=d.icon;$("selectedName").textContent=d.name;$("selectedDescription").textContent=d.desc;
 $("textControlWrap").hidden=true;$("subtitleWrap").hidden=true;$("moduleText").value="";
 $("heightWrap").hidden=id!=="grid";
 const f=$("fontSize");f.min=d.size[0];f.max=d.size[1];
 const slides=[["fontSize","font",v=>v+" px"],["posX","x",v=>v+" px"],["posY","y",v=>v+" px"],["moduleHeight","h",v=>v+" px"]];
 for(const [el,prop,formatter] of slides){$(el).value=m[prop];$(el+"Value").textContent=formatter(m[prop]);setTrack($(el));}
 buildLayers();render();
}
function setTrack(el){const min=Number(el.min),max=Number(el.max);el.style.setProperty("--pct",((el.value-min)/(max-min)*100).toFixed(1)+"%");}
function setDate(date){if(!/^20\d\d-\d\d-\d\d$/.test(date))return;const d=dayDate(date);if(!Number.isFinite(d.valueOf())||formatISO(d)!==date)return;state.date=date;$("dateInput").value=date;scheduleSave();render();}
function applyPreset(key){
 const s=structuredClone(defaults);
 for(const [k,delta] of Object.entries(presets[key]||{}))Object.assign(s[k],delta);
 state.modules=s;state.preset=key;reflectPresets();select(active);scheduleSave();notify("已切换到「"+({classic:"标准月历",minimal:"大字留白",compact:"紧凑月历"}[key]||key)+"」排版");
}
function pointerPos(e){const r=canvas.getBoundingClientRect();return {x:(e.clientX-r.left)*W/r.width,y:(e.clientY-r.top)*H/r.height};}
function intersects(pt,rect){return pt.x>=rect.x&&pt.x<=rect.x+rect.w&&pt.y>=rect.y&&pt.y<=rect.y+rect.h;}
canvas.addEventListener("pointerdown",e=>{
 if(clean)return;
 const pt=pointerPos(e),ids=[active,...defs.map(d=>d.id).filter(id=>id!==active)].reverse();
 // Check already active first to ease dragging selected group.
 const order=[active,...defs.map(d=>d.id).filter(id=>id!==active).reverse()];
 const found=order.find(k=>state.modules[k].visible&&intersects(pt,bounds(k,state.modules[k])));
 if(!found)return;
 select(found);dragging={id:found,start:pt,x:state.modules[found].x,y:state.modules[found].y};
 canvas.setPointerCapture(e.pointerId);canvas.classList.add("is-dragging");
});
canvas.addEventListener("pointermove",e=>{
 if(!dragging)return;
 const point=pointerPos(e),m=state.modules[dragging.id];
 m.x=Math.max(0,Math.min(W,Math.round(dragging.x+point.x-dragging.start.x)));
 m.y=Math.max(0,Math.min(H,Math.round(dragging.y+point.y-dragging.start.y)));
 $("posX").value=m.x;$("posY").value=m.y;$("posXValue").textContent=m.x+" px";$("posYValue").textContent=m.y+" px";
 setTrack($("posX"));setTrack($("posY"));mutate();
});
canvas.addEventListener("pointerup",()=>{dragging=null;canvas.classList.remove("is-dragging");});
canvas.addEventListener("pointercancel",()=>{dragging=null;canvas.classList.remove("is-dragging");});
for(const [element,prop] of [["fontSize","font"],["posX","x"],["posY","y"],["moduleHeight","h"]]){
 $(element).addEventListener("input",e=>{const m=state.modules[active];m[prop]=+e.target.value;$(element+"Value").textContent=m[prop]+" px";setTrack(e.target);mutate();});
}
$("moduleText").addEventListener("input",e=>{state.modules[active].text=e.target.value;mutate();});
$("fontFamily").value=state.global.fontFamily;
$("fontFamily").addEventListener("change",e=>{state.global.fontFamily=e.target.value;render();scheduleSave();});
for(const [id,attr] of [["showLunar","showLunar"],["showSolar","showSolar"],["highlightToday","highlightToday"]]){
 $(id).checked=state.global[attr];$(id).addEventListener("change",e=>{state.global[attr]=e.target.checked;render();scheduleSave();});
}
function reflectPalette(){document.querySelectorAll(".palette").forEach(b=>b.classList.toggle("active",b.dataset.palette===state.global.palette));}
reflectPalette();
document.querySelectorAll(".palette").forEach(b=>b.addEventListener("click",()=>{state.global.palette=b.dataset.palette;reflectPalette();render();scheduleSave();}));
document.querySelectorAll(".preset").forEach(b=>b.addEventListener("click",()=>applyPreset(b.dataset.preset)));
document.querySelectorAll("[data-nudge]").forEach(b=>b.addEventListener("click",()=>{
 const [dx,dy]=b.dataset.nudge.split(",").map(Number),m=state.modules[active];m.x=Math.max(0,Math.min(W,m.x+dx));m.y=Math.max(0,Math.min(H,m.y+dy));select(active);mutate();
}));
document.addEventListener("keydown",e=>{
 if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(e.key))return;
 if(["INPUT","SELECT","TEXTAREA"].includes(e.target.tagName))return;
 if(e.ctrlKey||e.metaKey||e.altKey)return;
 const delta=e.shiftKey?10:1,m=state.modules[active];
 if(e.key==="ArrowLeft")m.x=Math.max(0,m.x-delta);
 else if(e.key==="ArrowRight")m.x=Math.min(W,m.x+delta);
 else if(e.key==="ArrowUp")m.y=Math.max(0,m.y-delta);
 else m.y=Math.min(H,m.y+delta);
 e.preventDefault();select(active);mutate();
});
$("dateInput").addEventListener("change",e=>setDate(e.target.value));
$("prevDay").addEventListener("click",()=>{const d=dayDate(state.date);d.setUTCDate(d.getUTCDate()-1);setDate(formatISO(d));});
$("nextDay").addEventListener("click",()=>{const d=dayDate(state.date);d.setUTCDate(d.getUTCDate()+1);setDate(formatISO(d));});
$("todayBtn").addEventListener("click",()=>setDate(todayISO()));
$("guideToggle").addEventListener("click",()=>{guide=!guide;$("guideToggle").classList.toggle("active",guide);$("guideToggle").setAttribute("aria-pressed",String(guide));render();});
$("previewToggle").addEventListener("click",()=>{clean=!clean;$("previewToggle").classList.toggle("active",clean);$("previewToggle").setAttribute("aria-pressed",String(clean));$("previewState").textContent=clean?"成品预览 · 不显示辅助线":"编辑模式 · 可拖动模块";render();});
$("saveBtn").addEventListener("click",()=>save(false));
$("resetModule").addEventListener("click",()=>{Object.assign(state.modules[active],structuredClone(defaults[active]));mutate();select(active);notify("当前模块已恢复默认");});
$("resetAllBtn").addEventListener("click",()=>{if(!window.confirm("恢复默认排版？当前自定义位置将被重置。"))return;state=base();syncAll();save();notify("已恢复默认排版");});
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
$("exportBtn").addEventListener("click",()=>{
 render(false);
 canvas.toBlob(blob=>{render(true);if(!blob){notify("PNG 导出失败");return;}download(blob,"墨水历-"+state.date+"-758x1024.png");notify("PNG 已按阅读器原生尺寸导出");},"image/png");
});
$("exportConfigBtn").addEventListener("click",()=>{
 const blob=new Blob([JSON.stringify({...state,exportedAt:new Date().toISOString()},null,2)],{type:"application/json;charset=utf-8"});
 download(blob,"墨水历-排版方案-"+state.date+".json");notify("排版配置已导出，可发给我同步到阅读器");
});
$("importBtn").addEventListener("click",()=>$("importInput").click());
$("importInput").addEventListener("change",async(e)=>{
 const file=e.target.files?.[0];if(!file)return;
 try{const raw=JSON.parse(await file.text());state=sanitize(raw);syncAll();save();notify("排版方案已导入");}
 catch(err){notify("导入失败："+err.message);}
 e.target.value="";
});
function syncAll(){
 $("dateInput").value=state.date;$("fontFamily").value=state.global.fontFamily;
 for(const id of ["showLunar","showSolar","highlightToday"])$(id).checked=state.global[id];
 reflectPalette();reflectPresets();select(active);
}
syncAll();
// Update the Canvas clock only when the minute has changed (also catches tab resume).
let lastMinute=clockText();
setInterval(()=>{
 const current=clockText();
 if(current!==lastMinute){lastMinute=current;if(state.modules.clock.visible)render();}
},10000);
document.addEventListener("visibilitychange",()=>{
 if(!document.hidden){lastMinute=clockText();render();}
});
})();
