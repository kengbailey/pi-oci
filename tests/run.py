#!/usr/bin/env python3
"""Run the real ARMv7 payload, including a PTY/TUI smoke. No live LLM."""
import argparse
import errno
import os
from pathlib import Path
import pty
import select
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('flavor', choices=['standard', 'minimal'])
    parser.add_argument('--tui-only', action='store_true')
    args = parser.parse_args()
    image = 'pi-oci:' + args.flavor + '-test'
    common = ['docker', 'run', '--rm', '--platform', 'linux/arm/v7', '--network', 'none',
              '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
              '--memory=512m', '--memory-swap=512m', '--cpus=2', '--pids-limit=64',
              '--tmpfs', '/tmp:rw,nosuid,nodev,size=32m',
              '--tmpfs', '/home/pi:rw,uid=1000,gid=1000,size=32m',
              '--tmpfs', '/workspace:rw,uid=1000,gid=1000,size=32m']
    if not args.tui_only:
        subprocess.run(common + ['-e', 'PI_TEST_FLAVOR=' + args.flavor, '-v', str(ROOT / 'tests') + ':/tests:ro',
                             '--entrypoint', 'node', image, '/tests/runtime.mjs'], check=True, timeout=900)
    master, slave = pty.openpty()
    import fcntl
    import struct
    import termios
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 28, 100, 0, 0))
    command = common + ['-it', image, '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-themes']
    child = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = b''
    try:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if select.select([master], [], [], .2)[0]:
                try:
                    output += os.read(master, 65536)
                except OSError as e:
                    if e.errno == errno.EIO:
                        break
                    raise
                # Respond to terminal capability query; not a keyboard event.
                if b'\x1b[6n' in output[-2048:]:
                    os.write(master, b'\x1b[1;1R')
                if b'/model' in output or b'ctrl+' in output.lower():
                    break
        assert b'\x1b[' in output and (b'/model' in output or b'ctrl+' in output.lower()), output[-4000:]
        # Continue draining the PTY: waiting without reading can deadlock a redraw.
        end = time.monotonic() + 45
        next_exit = time.monotonic() + 2
        while child.poll() is None and time.monotonic() < end:
            if select.select([master], [], [], .2)[0]:
                try:
                    output += os.read(master, 65536)
                except OSError as e:
                    if e.errno != errno.EIO:
                        raise
                    break
            if time.monotonic() >= next_exit:
                os.write(master, b'\x04')
                next_exit = time.monotonic() + 3
        child.wait(timeout=5)
        assert child.returncode == 0, output[-4000:]
        print('TUI_RENDER_EXIT_OK')
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        (ROOT / '.build' / (args.flavor + '-tui.raw')).write_bytes(output)
        os.close(master)


if __name__ == '__main__':
    main()
