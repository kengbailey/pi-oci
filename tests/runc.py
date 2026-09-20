#!/usr/bin/env python3
"""Validate the generated OCI config with real runc on a Linux CI host."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1]
flavor=sys.argv[1]
assert flavor in ('standard','minimal') and os.geteuid()==0
spec=importlib.util.spec_from_file_location('prepare',ROOT/'scripts/prepare-runc.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='pi-oci-runc-') as tmp:
    root=Path(tmp);runtime=root/'rootfs';runtime.mkdir()
    # This archive was just built by CI, not supplied by a PR author as a binary.
    with tarfile.open(next((ROOT/'out'/flavor).glob('*-rootfs.tar.gz'))) as tf:
        tf.extractall(runtime,filter='fully_trusted')
    for name in ('home','work'):
        (root/name).mkdir();os.chown(root/name,1000,1000)
    cfg=m.specification(runtime,root/'home',root/'work',terminal=False,memory=512,
        command=['node','-e',"const f=require('fs'),a=require('assert/strict');a.equal(process.getuid(),1000);a.throws(()=>f.writeFileSync('/usr/no','x'));a.match(f.readFileSync('/proc/self/status','utf8'),/Seccomp:\\s+2/);f.writeFileSync('/workspace/ok','RUNC_OK');console.log('RUNC_OK')"])
    (root/'config.json').write_text(json.dumps(cfg))
    subprocess.run(['runc','--root',str(root/'run'),'run','--bundle',str(root),'pi-oci-test'],check=True,timeout=180)
    assert (root/'work/ok').read_text()=='RUNC_OK'
print('DIRECT_RUNC_SPEC_OK')
