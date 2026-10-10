#!/usr/bin/env python3
"""Local smoke test: real headless Chrome, no web/app dependencies."""
import base64, hashlib, json, os, subprocess, tempfile, time, urllib.request, sys
from pathlib import Path
from websockets.sync.client import connect
from PIL import Image
ROOT=Path(__file__).resolve().parent
URL="http://127.0.0.1:8786/"
PORT=9339
out=ROOT.parent/"build"/"web-browser-qa.png"
chromedir=tempfile.TemporaryDirectory(prefix="eink-chrome-")
downloads=ROOT.parent/"build"/"web-download-qa"
downloads.mkdir(parents=True,exist_ok=True)
for stale in downloads.iterdir():
    if stale.is_file():stale.unlink()
proc=subprocess.Popen(["/usr/bin/google-chrome","--headless=new","--disable-gpu","--no-sandbox",
    "--disable-dev-shm-usage","--remote-debugging-port="+str(PORT),"--remote-allow-origins=*",
    "--user-data-dir="+chromedir.name,"--window-size=1650,1020","--force-device-scale-factor=1",URL],
    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    tab=None
    for tries in range(70):
        try:
            tabs=json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list",timeout=2))
            tab=next((x for x in tabs if x.get("type")=="page" and x.get("url", "").startswith(URL)),None)
            if tab:break
        except Exception: pass
        time.sleep(.2)
    assert tab, "Chrome CDP did not open editor"
    with connect(tab["webSocketDebuggerUrl"],origin="http://localhost",open_timeout=7,max_size=20_000_000) as ws:
        serial=[0]
        def rpc(method,params=None):
            serial[0]+=1
            ident=serial[0];ws.send(json.dumps({"id":ident,"method":method,"params":params or {}}))
            while True:
                r=json.loads(ws.recv(timeout=20))
                if r.get("id")==ident:
                    if "error" in r: raise RuntimeError(str(r["error"]))
                    return r.get("result",{})
        def eval(expression):
            r=rpc("Runtime.evaluate",{"expression":expression,"returnByValue":True,"awaitPromise":True})
            if "exceptionDetails" in r:raise RuntimeError(str(r["exceptionDetails"]))
            return r.get("result",{}).get("value")
        rpc("Runtime.enable");rpc("Page.enable")
        rpc("Page.setDownloadBehavior",{"behavior":"allow","downloadPath":str(downloads)})
        for tries in range(50):
            if eval("document.readyState==='complete' && document.querySelectorAll('#moduleList .module-item').length===4"):break
            time.sleep(.2)
        assert eval("document.querySelectorAll('#moduleList .module-item').length") == 4
        assert eval("document.getElementById('calendarCanvas').width")==758
        assert eval("document.getElementById('calendarCanvas').height")==1024
        assert eval("document.querySelectorAll('#presetList button').length")==3
        print("PASS baseline 758x1024 4 modules 3 presets",flush=True)
        # Capture clean initial screenshot.
        shot=rpc("Page.captureScreenshot",{"format":"png","captureBeyondViewport":False})
        out.write_bytes(base64.b64decode(shot["data"]))
        with Image.open(out) as im:
            print("SCREENSHOT",out,im.size,flush=True)
            assert im.width>=1300 and im.height>=800
        fingerprint=eval("document.getElementById('calendarCanvas').toDataURL('image/png').slice(-120)")
        eval("document.querySelector('[data-preset=minimal]').click()")
        assert eval("document.querySelector('[data-preset=minimal]').classList.contains('active')") is True
        assert fingerprint!=eval("document.getElementById('calendarCanvas').toDataURL('image/png').slice(-120)")
        print("PASS presets canvas redraw",flush=True)
        eval("document.querySelector('[data-preset=classic]').click()")
        eval("""(()=>{let e=document.querySelector('#dateInput');e.value='2026-11-01';e.dispatchEvent(new Event('change',{bubbles:true}));return true})()""")
        assert eval("document.getElementById('dateInput').value")=="2026-11-01"
        print("PASS date change 2026-11-01",flush=True)
        eval("document.querySelector('#fontSize').value=39;document.querySelector('#fontSize').dispatchEvent(new Event('input',{bubbles:true}));true")
        assert eval("document.querySelector('#fontSizeValue').textContent").strip()=="39 px"
        print("PASS font slider rerender",flush=True)
        # Real pointer interaction on the date grid, not a synthetic DOM event.
        rect=eval("""(()=>{let r=document.querySelector('#calendarCanvas').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()""")
        x=rect["x"]+150/758*rect["w"]; y=rect["y"]+560/1024*rect["h"]
        initial=float(eval("document.querySelector('#posXValue').textContent.replace(' px','')"))
        rpc("Input.dispatchMouseEvent",{"type":"mouseMoved","x":x,"y":y})
        rpc("Input.dispatchMouseEvent",{"type":"mousePressed","x":x,"y":y,"button":"left","clickCount":1})
        rpc("Input.dispatchMouseEvent",{"type":"mouseMoved","x":x+34,"y":y+14,"button":"left","buttons":1})
        rpc("Input.dispatchMouseEvent",{"type":"mouseReleased","x":x+34,"y":y+14,"button":"left","clickCount":1})
        next_x=float(eval("document.querySelector('#posXValue').textContent.replace(' px','')"))
        assert next_x>initial+10, f"Drag did not update X coordinate: {initial} -> {next_x}"
        print("PASS real mouse drag",initial,"->",next_x,flush=True)
        eval("document.querySelector('#exportBtn').click()")
        target=downloads/"墨水历-2026-11-01-758x1024.png"
        for i in range(50):
            if target.exists() and target.stat().st_size>10000:break
            time.sleep(.2)
        assert target.is_file(), "PNG export missing"
        with Image.open(target) as im:
            assert im.size==(758,1024) and im.format=="PNG"
            print("PASS PNG export",im.size,target.stat().st_size,flush=True)
        eval("document.querySelector('#exportConfigBtn').click()")
        j=downloads/"墨水历-排版方案-2026-11-01.json"
        for i in range(50):
            if j.is_file():break
            time.sleep(.2)
        assert j.is_file(),"JSON export missing"
        cfg=json.loads(j.read_text());assert cfg["date"]=="2026-11-01"
        assert cfg["device"]=="EPD106A"
        assert cfg["version"]==3
        assert set(cfg["modules"])=={"month","clock","grid","solar"}
        print("PASS JSON export",len(cfg["modules"]),"modules",flush=True)
        # Resizing/toggling and local persistence
        eval("document.querySelector('#showLunar').click()")
        assert eval("document.querySelector('#showLunar').checked") is False
        print("PASS show/hide options",flush=True)
        errs=eval("document.querySelector('#toast').textContent")
        print("PASS browser end-to-end",flush=True)
finally:
    proc.terminate()
    try:proc.wait(timeout=8)
    except subprocess.TimeoutExpired:proc.kill()
    try: chromedir.cleanup()
    except OSError: pass  # Chrome may still flush its async profile cache after process termination
