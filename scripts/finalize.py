#!/usr/bin/env python3
"""Assemble install helpers and checksums after all acceptance gates pass."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile

root=Path(__file__).resolve().parents[1]
flavor=sys.argv[1]
assert flavor in ('standard','minimal')
out=root/'out'/flavor
inputs=json.loads((root/'tracks'/flavor/'inputs.json').read_text())
assert list(out.glob('*-sources.tar.gz')), 'Source archive is a required release gate'
with tarfile.open(out/'pi-runc-tools.tar.gz','w:gz') as tf:
    for name in ['scripts/prepare-runc.py','config/seccomp.json','LICENSE','NOTICE','licenses','docs/USAGE.md']:
        tf.add(root/name,arcname='pi-oci/'+name)
info=json.loads((out/'build-info.json').read_text())
info['ci_run']=os.getenv('GITHUB_SERVER_URL','https://github.com')+'/'+os.getenv('GITHUB_REPOSITORY','kengbailey/pi-oci')+'/actions/runs/'+os.getenv('GITHUB_RUN_ID','local')
info['validation']='ARMv7 runtime/TUI/tool-loop suite; not a new physical-device benchmark'
(out/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
files=sorted(p for p in out.iterdir() if p.is_file() and p.name!='SHA256SUMS')
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
tag=f'{flavor}-v{inputs["pi"]}-r{inputs["revision"]}'
if os.getenv('GITHUB_OUTPUT'):
    with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('tag='+tag+'\n')
print(tag)
