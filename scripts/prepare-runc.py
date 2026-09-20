#!/usr/bin/env python3
"""One-time OCI bundle setup; Python is not needed at launch time.

Unpack a verified release as root first. The runtime stays read-only; only the
explicit home/workspace are writable. Does not mount cgroups or change boot.
"""
import argparse
import json
import os
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]


def specification(rootfs, home, workspace, *, terminal=True, inet=False, memory=192, command=None):
    return {
        'ociVersion': '1.0.2',
        'process': {
            'terminal': terminal, 'user': {'uid':1000,'gid':1000,'additionalGids':[3003] if inet else []},
            'args': command or ['/usr/local/bin/pi'], 'cwd':'/workspace',
            'env':['PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','HOME=/home/pi',
                   'TERM=xterm-256color','PI_OFFLINE=1','NODE_OPTIONS=--max-old-space-size=96',
                   'NODE_COMPILE_CACHE=/home/pi/.cache/node'],
            'capabilities': {k:[] for k in ['bounding','effective','inheritable','permitted','ambient']},
            'rlimits':[{'type':'RLIMIT_NOFILE','hard':1024,'soft':1024}], 'noNewPrivileges':True,
        },
        'root': {'path': str(rootfs), 'readonly':True}, 'hostname':'pi-oci',
        'mounts':[
            {'destination':'/proc','type':'proc','source':'proc','options':['nosuid','noexec','nodev']},
            {'destination':'/dev','type':'tmpfs','source':'tmpfs','options':['nosuid','strictatime','mode=755','size=65536k']},
            {'destination':'/dev/pts','type':'devpts','source':'devpts','options':['nosuid','noexec','newinstance','ptmxmode=0666','mode=0620','gid=5']},
            {'destination':'/dev/shm','type':'tmpfs','source':'shm','options':['nosuid','noexec','nodev','mode=1777','size=32768k']},
            {'destination':'/tmp','type':'tmpfs','source':'tmpfs','options':['nosuid','nodev','mode=1777','size=32768k']},
            {'destination':'/home/pi','type':'bind','source':str(home),'options':['rbind','rw','nosuid','nodev']},
            {'destination':'/workspace','type':'bind','source':str(workspace),'options':['rbind','rw','nosuid','nodev']},
            {'destination':'/etc/resolv.conf','type':'bind','source':'/etc/resolv.conf','options':['bind','ro','nosuid','nodev']},
        ],
        'linux': {
            'namespaces':[{'type':n} for n in ['pid','ipc','uts','mount']],
            'resources':{'memory':{'limit':memory*1024*1024,'swap':memory*1024*1024},
                         'cpu':{'quota':100000,'period':100000},'pids':{'limit':64}},
            'maskedPaths':['/proc/acpi','/proc/asound','/proc/kcore','/proc/keys','/proc/latency_stats','/proc/timer_list','/proc/timer_stats','/proc/sched_debug','/sys/firmware'],
            'readonlyPaths':['/proc/bus','/proc/fs','/proc/irq','/proc/sys','/proc/sysrq-trigger'],
            'seccomp': json.loads((ROOT / 'config/seccomp.json').read_text()),
        }
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rootfs',type=Path,required=True)
    p.add_argument('--home',type=Path,required=True)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--android-inet',action='store_true',help='Add Android kernel inet GID 3003')
    p.add_argument('--legacy-cgroup-v1',action='store_true',help='Omit unavailable pids controller on old kernels')
    p.add_argument('--no-terminal',action='store_true')
    p.add_argument('--memory',type=int,default=192,help='MiB (default: 192)')
    p.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args()
    rootfs,home,workspace,bundle=[p.resolve() for p in [args.rootfs,args.home,args.workspace,args.bundle]]
    if not (rootfs/'usr/local/bin/pi').is_file():p.error('Expected an unpacked Pi rootfs')
    if bundle.exists():p.error('Bundle already exists; use a new path for each upgrade')
    for writable in [home,workspace]:
        if writable==Path('/') or writable==rootfs or writable in rootfs.parents or rootfs in writable.parents:
            p.error('Home/workspace must be separate from the runtime and must not contain it')
        if not writable.is_dir():p.error('Create dedicated home/workspace directories first')
        if writable.stat().st_uid!=1000:p.error('Writable directories must be owned by UID 1000; ownership is never changed automatically')
    command=args.command
    if command[:1]==['--']:command=command[1:]
    bundle.mkdir(parents=True)
    config=specification(rootfs,home,workspace,terminal=not args.no_terminal,inet=args.android_inet,memory=args.memory,command=command or None)
    if args.legacy_cgroup_v1:config['linux']['resources'].pop('pids')
    (bundle/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    # Root-owned bundle, no eval, no Docker daemon, no startup registration.
    launcher='''#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo "Run with sudo/root (Pi itself runs as UID 1000)." >&2; exit 1; }
cd BUNDLE
mkdir .running 2>/dev/null || { echo "Bundle already running, or stale .running lock; inspect before removing it." >&2; exit 1; }
trap 'rmdir .running 2>/dev/null || true' EXIT
runc --root /run/pi-oci run --bundle "$PWD" "pi-oci-$$"
'''.replace('BUNDLE',shlex.quote(str(bundle)))
    (bundle/'pi-runc').write_text(launcher)
    (bundle/'pi-runc').chmod(0o755)
    print('Created',bundle/'pi-runc')


if __name__=='__main__':main()
