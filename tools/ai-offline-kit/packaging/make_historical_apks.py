#!/usr/bin/env python3
"""Fetch only this repository's three previously published first-party APKs.

Hash pinned to `device/release-apks.sha256`. Does not include third-party binaries.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import urllib.request
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[3]
KIT=pathlib.Path(__file__).resolve().parents[1]
PIN=ROOT/'device'/'release-apks.sha256'
TAG='v0.3.0-ten-minute-alpha.2'
REPO='richducks/xiaomi-epd106a-live-calendar'

def main():
    lines=PIN.read_text(encoding='utf-8').strip().splitlines()
    expected={}
    for ln in lines:
        digest,name=ln.strip().split(None,1)
        if len(digest)!=64 or not name.endswith('.apk') or '/' in name or '\\' in name:
            raise RuntimeError('invalid APK pin entry')
        expected[name]=digest
    if set(expected)!={'eink-calendar.apk','eink-livecalendar-policy.apk','eink-neat-touchzones.apk'}:
        raise RuntimeError('pin list differs from expected three first-party apps')
    folder=KIT/'release-output';folder.mkdir(exist_ok=True)
    out=folder/'EPD106A-first-party-APKs-2026-10-11.zip'
    if out.exists(): raise RuntimeError('refuse overwrite '+str(out))
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,digest in expected.items():
            url=f'https://github.com/{REPO}/releases/download/{TAG}/{name}'
            req=urllib.request.Request(url,headers={'User-Agent':'XiaomiReaderFirstPartyRelease/0.3'})
            with urllib.request.urlopen(req,timeout=75) as response:
                data=response.read(20*1024*1024)
            actual=hashlib.sha256(data).hexdigest()
            if actual!=digest:
                raise RuntimeError(f'APK SHA-256 mismatch: {name} {actual}')
            z.writestr('historical-first-party-apks/'+name,data)
        z.write(PIN,'historical-first-party-apks/release-apks.sha256')
        z.writestr('historical-first-party-apks/README.txt',
            'These are exact SHA-256-pinned self-developed experimental APKs published 2026-10-11.\n'
            'NOT the latest source, NOT a complete system image. Existing APK signing keys may differ.\n'
            'Do NOT uninstall apps merely to bypass a signature mismatch; this can erase data.\n'
            'Magisk, LSPosed, NeatReader, Google Platform-Tools and vendor firmware are NOT included.\n')
    print(json.dumps({'asset':str(out),'bytes':out.stat().st_size},ensure_ascii=False))

if __name__=='__main__':main()
