#!/usr/bin/env python3
"""Publish only a completed, checksummed artifact set from a trusted build."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def run(*args,**kwargs):return subprocess.run(args,check=True,**kwargs)


def main():
    p=argparse.ArgumentParser();p.add_argument('flavor',choices=['standard','minimal']);p.add_argument('directory',type=Path)
    a=p.parse_args();out=a.directory.resolve()
    run('sha256sum','-c','SHA256SUMS',cwd=out)
    info=json.loads((out/'build-info.json').read_text());inputs=info['inputs'];assert info['flavor']==a.flavor
    tag=f'{a.flavor}-v{inputs["pi"]}-r{inputs["revision"]}'
    repo=os.environ['GITHUB_REPOSITORY'];registry='ghcr.io/'+repo.lower()
    previous=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True)
    if previous.returncode==0:
        print('Immutable release already exists:',tag);return
    assert list(out.glob('*-sources.tar.gz'))
    rootfs=next(out.glob('*-rootfs.tar.gz'))
    image=registry+':'+tag
    run('docker','import','--platform','linux/arm/v7',
        '--change','USER 1000:1000','--change','WORKDIR /workspace',
        '--change','ENV HOME=/home/pi PI_OFFLINE=1 NODE_OPTIONS=--max-old-space-size=96 NODE_COMPILE_CACHE=/home/pi/.cache/node TERM=xterm-256color',
        '--change','ENTRYPOINT ["/usr/local/bin/pi"]',
        '--change','LABEL org.opencontainers.image.source=https://github.com/'+repo,
        str(rootfs),image)
    run('docker','login','ghcr.io','-u',os.environ['GITHUB_ACTOR'],'--password-stdin',input=os.environ['GH_TOKEN'].encode())
    try:
        run('docker','push',image)
        run('docker','tag',image,registry+':'+a.flavor)
        run('docker','push',registry+':'+a.flavor)
    finally:run('docker','logout','ghcr.io')
    body=f'''Pi {inputs['pi']} · {a.flavor.title()} · ARMv7 · packaging revision {inputs['revision']}.

Complete rootfs for direct runc and a single-layer OCI image: `{image}`.

See [usage](https://github.com/{repo}/blob/main/docs/USAGE.md), [compatibility](https://github.com/{repo}/blob/main/docs/COMPATIBILITY.md), and [release policy](https://github.com/{repo}/blob/main/docs/RELEASES.md).

CI gates: deterministic streaming model with all seven tools, session resume, TypeScript extension, TUI render/exit, WASM, non-root/read-only/seccomp checks, and structured connection-failure handling. Minimal additionally checks patched transport and highlighting. No live cloud account is used in CI. QEMU uses a larger test memory allowance than the 192 MiB device profile.

Verify `SHA256SUMS` before extraction. Source archive and dependency inventory correspond to this build. No keys, model accounts, firmware, or inference model weights are included. Nothing auto-installs or starts at boot.

Source commit: `{info['git_commit']}`. Build: {info['ci_run']}.
'''
    with tempfile.NamedTemporaryFile('w',suffix='.md') as f:
        f.write(body);f.flush()
        run('gh','release','create',tag,'--repo',repo,'--target',info['git_commit'],'--title',f'Pi {inputs["pi"]} {a.flavor.title()} (r{inputs["revision"]})','--notes-file',f.name,*[str(x) for x in sorted(out.iterdir()) if x.is_file()])


if __name__=='__main__':main()
