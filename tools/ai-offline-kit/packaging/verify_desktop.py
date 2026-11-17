#!/usr/bin/env python3
"""Minimal packaged executable tests, intentionally no attached Android device needed."""
import argparse
import json
import subprocess
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--target',required=True);args=p.parse_args()
root=Path(__file__).resolve().parents[1]
exe='.exe' if args.target.startswith('windows') else ''
app=root/'dist'/('XiaomiReader'+exe)
ai=root/'dist'/('XiaomiReaderAI'+exe)
print('Verify executable:',app)
res=subprocess.run([str(app),'--self-test'],capture_output=True,timeout=60)
assert res.returncode==0, f'GUI smoke failure: {res.returncode} {res.stderr[:500]!r}'
if res.stdout:
    d=json.loads(res.stdout.decode('utf-8','replace'))
    assert d['application']=='XiaomiReader'
print('Verify AI executable:',ai)
res=subprocess.run([str(ai),'status'],capture_output=True,timeout=60)
data=json.loads(res.stdout.decode('utf-8','replace'))
assert data['tool']=='xiaomi-reader-ai-runner'
assert data['action']=='status'
print('OK: desktop launcher and AI JSON entrypoint are executable')
