#!/usr/bin/env python3
"""Refresh Standard only; stays within the selected Alpine release series."""
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
from sources import apk_records

ROOT=Path(__file__).resolve().parents[1]
track=ROOT/'tracks/standard'
inputs=json.loads((track/'inputs.json').read_text())
before=json.dumps(inputs,sort_keys=True)
with urllib.request.urlopen('https://registry.npmjs.org/@earendil-works/pi-coding-agent/latest') as r:
    version=json.load(r)['version']
assert re.fullmatch(r'\d+\.\d+\.\d+',version), 'Refusing pre-release or malformed npm version'
series=re.search(r'alpine:(\d+\.\d+)',inputs['alpine'])[1]
manifest=json.loads(subprocess.check_output(['docker','buildx','imagetools','inspect','alpine:'+series,'--format','{{json .Manifest}}'],text=True))
if not inputs['alpine'].endswith('@'+manifest['digest']):
    inputs['alpine']='alpine:'+series+'@'+manifest['digest']
inputs['pi']=version
packages=[x.split('=')[0] for x in inputs['packages']]
result=subprocess.check_output(['docker','run','--rm','--platform','linux/arm/v7',inputs['alpine'],'sh','-c',
    'apk add --no-cache "$@" >/dev/null && cat /lib/apk/db/installed','sh',*packages],text=True)
versions={p['name']:p['version'] for p in apk_records(result)}
assert all(name in versions for name in packages)
inputs['packages']=[name+'='+versions[name] for name in packages]
changed=json.dumps(inputs,sort_keys=True)!=before
if changed:
    inputs['revision']+=1
    package=json.loads((track/'package.json').read_text())
    package['dependencies']['@earendil-works/pi-coding-agent']=version
    (track/'package.json').write_text(json.dumps(package,indent=2)+'\n')
    subprocess.run(['npm','install','--package-lock-only','--ignore-scripts','--omit=optional','--no-audit','--no-fund'],cwd=track,check=True)
    (track/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
if os.getenv('GITHUB_OUTPUT'):
    with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('changed='+str(changed).lower()+'\n')
print('Standard update candidate:',changed)
