#!/usr/bin/env python3
"""Build from one independently locked track. Never use the private prototype."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('flavor', choices=['standard', 'minimal'])
    p.add_argument('--prepare-only', action='store_true')
    args = p.parse_args()
    os.chdir(ROOT)
    track = ROOT / 'tracks' / args.flavor
    inputs = json.loads((track / 'inputs.json').read_text())
    assert json.loads((track / 'package.json').read_text())['dependencies']['@earendil-works/pi-coding-agent'] == inputs['pi']
    work = ROOT / '.build' / args.flavor
    # These are generated outputs only, never user files.
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    run('npm', 'ci', '--ignore-scripts', '--omit=optional', '--no-audit', '--no-fund', cwd=track)
    app = work / 'app'
    if args.flavor == 'standard':
        shutil.copytree(track / 'node_modules', app / 'node_modules', symlinks=True)
        removed = 0
        retained = 0
        for path in (app / 'node_modules').rglob('*'):
            if path.is_file() and not path.is_symlink():
                if path.name.endswith(('.map', '.d.ts', '.d.mts', '.d.cts')):
                    path.unlink()
                    removed += 1
                else:
                    # Check the full retained payload, not just the CLI entry.
                    assert digest(path) == digest(track / path.relative_to(app))
                    retained += 1
        (work / 'packaging-proof.json').write_text(json.dumps({'retained_files_verified': retained, 'removed_debug_type_files': removed, 'runtime_bytes_modified': 0}, indent=2))
    else:
        run('npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund', cwd=ROOT / 'build-tools')
        run('node', 'scripts/build-minimal.mjs', env={**os.environ, 'PI_BUILD_DIR': str(work)})
        (work / 'app-compact').rename(app)
        # Exercise the exact patched transport / registries with no credentials.
        run('node', 'scripts/build-probe.mjs', env={**os.environ, 'PI_BUILD_DIR': str(work)})
        run('node', 'tests/http.mjs', env={**os.environ, 'PI_HTTP_PROBE': str(work / 'probe-module.mjs')})
    shutil.copytree(ROOT / 'licenses', app / 'licenses')
    shutil.copy(ROOT / 'NOTICE', app / 'NOTICE')
    if args.prepare_only:
        return
    tag = f'pi-oci:{args.flavor}-test'
    run('docker', 'buildx', 'build', '--load', '--platform', inputs['platform'],
        '--build-arg', 'ALPINE_IMAGE=' + inputs['alpine'], '--build-arg', 'FLAVOR=' + args.flavor,
        '--build-arg', 'APK_PACKAGES=' + ' '.join(inputs['packages']), '-t', tag, '.')
    output = ROOT / 'out' / args.flavor
    output.mkdir(parents=True, exist_ok=True)
    cid = subprocess.check_output(['docker', 'create', tag], text=True).strip()
    raw = work / 'rootfs.tar'
    try:
        run('docker', 'export', '-o', str(raw), cid)
    finally:
        run('docker', 'rm', cid)
    archive = output / f'pi-{args.flavor}-{inputs["pi"]}-r{inputs["revision"]}-armv7-rootfs.tar.gz'
    # Exporting a single rootfs avoids VFS's multilayer copies on old kernels.
    # Fixed tar/gzip metadata improves comparability; package feeds are not a
    # promise of reproducibility. The installed inventory is published too.
    import gzip
    with raw.open('rb') as src, archive.open('wb') as dest:
        with gzip.GzipFile(fileobj=dest, mode='wb', mtime=0, compresslevel=6) as gz:
            shutil.copyfileobj(src, gz)
    with tarfile.open(raw) as tf:
        inventory = tf.extractfile('lib/apk/db/installed').read()
    (output / 'apk-installed.txt').write_bytes(inventory)
    shutil.copy(track / 'package-lock.json', output / 'package-lock.json')
    report = {'flavor': args.flavor, 'inputs': inputs, 'sha256': digest(archive), 'archive': archive.name,
              'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'npm_lock_sha256': digest(track / 'package-lock.json')}
    (output / 'build-info.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
