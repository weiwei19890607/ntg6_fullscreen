#!/usr/bin/env python3
"""Select next boot mode without copying volatile overlay changes to disk."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

BOOT = Path('/boot/firmware')
CMDLINE = BOOT / 'cmdline.txt'
PROTECTED = 'overlayroot=tmpfs:swap=0,recurse=1'

def run(*args):
    return subprocess.check_output(args, text=True).strip()

def status():
    root_type = run('findmnt', '-n', '-o', 'FSTYPE', '/')
    current = 'protected' if root_type == 'overlay' else 'maintenance'
    tokens = CMDLINE.read_text().split()
    next_mode = 'protected' if PROTECTED in tokens else 'maintenance'
    print(json.dumps({'current': current, 'next_boot': next_mode,
                      'root_type': root_type,
                      'boot_options': run('findmnt', '-n', '-o', 'OPTIONS', str(BOOT)),
                      'changes_persist': current == 'maintenance'}, ensure_ascii=False))

def select(mode):
    if os.geteuid() != 0:
        raise SystemExit('请使用 sudo')
    if not Path('/proc/device-tree/model').read_text().startswith('Raspberry Pi 5'):
        raise SystemExit('仅支持本项目 Pi 5')
    if mode == 'protect' and run('findmnt', '-n', '-o', 'FSTYPE', '/') == 'overlay':
        raise SystemExit('当前已经受保护；不会将内存修改复制到磁盘。永久修改请先进入 maintenance 并重启。')
    tokens = CMDLINE.read_text().split()
    tokens = [t for t in tokens if not t.startswith('overlayroot=')]
    tokens.append(PROTECTED if mode == 'protect' else 'overlayroot=disabled')
    new = ' '.join(tokens) + '\n'
    was_ro = 'ro' in run('findmnt', '-n', '-o', 'OPTIONS', str(BOOT)).split(',')
    if was_ro:
        subprocess.run(['mount', '-o', 'remount,rw', str(BOOT)], check=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=BOOT, prefix='.cp2cl-cmdline-', delete=False) as f:
            name = f.name
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, 0o644)
        os.replace(name, CMDLINE)
        name = None
        fd = os.open(BOOT, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        os.sync()
    finally:
        if name:
            Path(name).unlink(missing_ok=True)
        if was_ro:
            subprocess.run(['mount', '-o', 'remount,ro', str(BOOT)], check=True)
    print('下一次启动：' + ('日常保护模式' if mode == 'protect' else '可持久保存的维护模式'))
    print('请执行 sudo reboot。模式在重启后生效；当前内存中的修改不会自动保存。')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['status', 'maintenance', 'protect'])
    args = parser.parse_args()
    status() if args.mode == 'status' else select(args.mode)
