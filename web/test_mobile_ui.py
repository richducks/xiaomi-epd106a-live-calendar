#!/usr/bin/env python3
"""Independent Jobs product acceptance: mobile viewport and reachable primary actions."""
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from websockets.sync.client import connect
from PIL import Image
ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8786/"
PORT = 9349
chrome_dir = tempfile.TemporaryDirectory(prefix="epd-mobile-")
proc = subprocess.Popen(
    ["/usr/bin/google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
     "--disable-dev-shm-usage", "--remote-debugging-port="+str(PORT),
     "--remote-allow-origins=*", "--user-data-dir="+chrome_dir.name,
     "--window-size=960,900", URL],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tab = None
    for _ in range(70):
        try:
            tabs=json.load(urllib.request.urlopen("http://127.0.0.1:"+str(PORT)+"/json/list",timeout=2))
            tab=next((t for t in tabs if t.get("url","").startswith(URL)),None)
            if tab:break
        except Exception:
            pass
        time.sleep(.2)
    assert tab, "Chrome did not start"
    with connect(tab["webSocketDebuggerUrl"],origin="http://localhost",open_timeout=7,max_size=30_000_000) as ws:
        ident=0
        def rpc(method, params=None):
            global ident
            ident+=1
            ws.send(json.dumps({"id":ident,"method":method,"params":params or {}}))
            while True:
                got=json.loads(ws.recv(timeout=20))
                if got.get("id")==ident:
                    if "error" in got:raise RuntimeError(got["error"])
                    return got.get("result",{})
        def js(code):
            r=rpc("Runtime.evaluate",{"expression":code,"returnByValue":True,"awaitPromise":True})
            if "exceptionDetails" in r:raise RuntimeError(r["exceptionDetails"])
            return r.get("result",{}).get("value")
        rpc("Page.enable")
        for width,height in ((375,812),(690,950),(768,1024)):
            rpc("Emulation.setDeviceMetricsOverride",{"width":width,"height":height,"deviceScaleFactor":1,"mobile":True})
            rpc("Emulation.setTouchEmulationEnabled",{"enabled":True})
            for _ in range(40):
                if js("document.readyState==='complete' && !!document.getElementById('calendarCanvas')"):
                    break
                time.sleep(.15)
            time.sleep(.3)
            metrics=js("""(()=>{
              const r=id=>document.getElementById(id).getBoundingClientRect();
              return {inner:window.innerWidth,document:document.documentElement.scrollWidth,
               export:r('exportBtn').width,canvas:r('calendarCanvas').width,
               presets:document.querySelectorAll('#presetList button').length,
               actions:document.querySelectorAll('.top-actions button').length};
            })()""")
            print("MOBILE_VIEW",width,metrics,flush=True)
            assert metrics["document"] <= metrics["inner"] + 2, "horizontal overflow on "+str(width)
            assert metrics["export"] >= 65 and metrics["canvas"]>160
            assert metrics["presets"] ==3 and metrics["actions"]==3
            if width==375:
                shot=rpc("Page.captureScreenshot",{"format":"png","captureBeyondViewport":False})
                out=ROOT.parent/"build/web-mobile-qa.png"
                out.parent.mkdir(exist_ok=True)
                out.write_bytes(base64.b64decode(shot["data"]))
                with Image.open(out) as im:print("MOBILE_SCREENSHOT",str(out),im.size,flush=True)
        print("PASS MOBILE RESPONSIVE 375/690/768 + critical action sizes",flush=True)
finally:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill()
    chrome_dir.cleanup()
