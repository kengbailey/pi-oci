#!/usr/bin/env python3
"""Collect source and recipes matching the *installed* APK inventory.

Never execute downloaded APKBUILDs. Save the exact recipe directory, then fetch
every sha512sums entry from Alpine distfiles and verify it. Missing source fails
the release. Also retain integrity-checked npm tarballs and upstream Pi source.
"""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(url):
    headers = {'User-Agent': 'pi-oci-source-collector'}
    if urllib.parse.urlparse(url).netloc == 'api.github.com' and os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180) as r:
        return r.read()


def download(url, path, algorithm=None, expected=None):
    if path.exists():
        data = path.read_bytes()
    else:
        data = fetch(url)
    if expected and hashlib.new(algorithm, data).digest() != expected:
        raise ValueError('Source checksum mismatch: ' + url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def apk_records(text):
    for block in text.split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines() if len(line) > 1 and line[1] == ':')
        if fields.get('P'):
            yield {k: fields.get(v) for k, v in {'name':'P','version':'V','origin':'o','license':'L','commit':'c','arch':'A'}.items()}


def recipe(package, root):
    origin, commit = package['origin'], package['commit']
    assert re.fullmatch(r'[a-z0-9+_.-]+', origin or '') and re.fullmatch('[a-f0-9]{40}', commit or '')
    destination = root / 'alpine' / f'{origin}-{commit}'
    if (destination / '.complete').exists():
        return
    tree = None
    for repository in ('main', 'community'):
        try:
            tree = json.loads(fetch(f'https://api.github.com/repos/alpinelinux/aports/contents/{repository}/{origin}?ref={commit}'))
            break
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    if not tree:
        raise RuntimeError('Missing aports recipe: ' + origin)
    def get_tree(entries, dest):
        for item in entries:
            path = dest / item['name']
            if item['type'] == 'dir':
                get_tree(json.loads(fetch(item['url'])), path)
            elif item['type'] == 'file':
                download(item['download_url'], path)
            else:
                raise RuntimeError('Unsupported recipe entry: ' + str(item))
    get_tree(tree, destination)
    apkbuild = (destination / 'APKBUILD').read_text()
    match = re.search(r'(?ms)^sha512sums="(.*?)"', apkbuild)
    if not match and re.search(r'(?m)^source=', apkbuild):
        raise RuntimeError('Unrecognized source checksums for ' + origin)
    for line in (match[1] if match else '').splitlines():
        if not line.strip():
            continue
        checksum, filename = line.split(None, 1)
        assert re.fullmatch('[a-f0-9]{128}', checksum) and Path(filename).name == filename
        path = destination / filename
        if path.exists():
            assert hashlib.sha512(path.read_bytes()).hexdigest() == checksum, path
        else:
            download('https://distfiles.alpinelinux.org/distfiles/v3.24/' + urllib.parse.quote(filename), path,
                     'sha512', bytes.fromhex(checksum))
    (destination / '.complete').write_text(commit + '\n')
    print('Source verified:', origin, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('flavor', choices=['standard','minimal'])
    args = parser.parse_args()
    output = ROOT / 'out' / args.flavor
    cache = ROOT / '.build' / 'source-cache'
    cache.mkdir(parents=True, exist_ok=True)
    records = list(apk_records((output / 'apk-installed.txt').read_text()))
    unique = {(p['origin'], p['commit']): p for p in records}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda p: recipe(p, cache), unique.values()))
    track = ROOT / 'tracks' / args.flavor
    locks = [track / 'package-lock.json', ROOT / 'build-tools/package-lock.json']
    # Published shrinkwraps can contain deps not expanded in the outer lock.
    locks.extend((track / 'node_modules').rglob('npm-shrinkwrap.json'))
    npm = {}
    for lock in locks:
        for path, package in json.loads(lock.read_text()).get('packages', {}).items():
            url, integrity = package.get('resolved'), package.get('integrity')
            if not url or not integrity:
                continue
            assert url.startswith('https://registry.npmjs.org/'), url
            algorithm, encoded = integrity.split('-', 1)
            key = hashlib.sha256(url.encode()).hexdigest()[:12] + '-' + url.rsplit('/',1)[1]
            npm[key] = {'url': url, 'integrity': integrity, 'license': package.get('license'), 'version': package.get('version')}
            download(url, cache / 'npm' / key, algorithm, base64.b64decode(encoded))
    inputs = json.loads((track / 'inputs.json').read_text())
    # Record the resolved upstream commit, not only a potentially mutable tag.
    commit = json.loads(fetch('https://api.github.com/repos/earendil-works/pi/commits/v' + inputs['pi']))['sha']
    upstream = cache / f'pi-{commit}.tar.gz'
    download(f'https://codeload.github.com/earendil-works/pi/tar.gz/{commit}', upstream)
    inventory = {'apk': records, 'npm': npm, 'pi_source_commit': commit,
                 'note': 'Full build-input inventory; Minimal does not ship every npm build dependency.'}
    (output / 'dependency-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    bundle = output / f'pi-{args.flavor}-{inputs["pi"]}-r{inputs["revision"]}-sources.tar.gz'
    with tarfile.open(bundle, 'w:gz') as tf:
        for origin, rev in sorted(unique):
            tf.add(cache / 'alpine' / f'{origin}-{rev}', arcname=f'alpine/{origin}-{rev}')
        for key in sorted(npm):
            tf.add(cache / 'npm' / key, arcname='npm/' + key)
        tf.add(upstream, arcname=upstream.name)
        for name in ('Dockerfile','LICENSE','NOTICE','scripts','config','tracks','build-tools','tests','docs'):
            def clean(member):
                return None if 'node_modules' in Path(member.name).parts or '__pycache__' in Path(member.name).parts else member
            tf.add(ROOT / name, arcname='pi-oci/' + name, filter=clean)
        tf.add(output / 'dependency-inventory.json', arcname='dependency-inventory.json')
    print('Complete source bundle:', bundle)


if __name__ == '__main__':
    main()
