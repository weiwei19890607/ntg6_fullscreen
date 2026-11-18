#!/usr/bin/env python3
"""Refuse protected-mode cp2cl startup if the disk-backed mounts are writable."""
import json
from pathlib import Path
import subprocess
import sys

def mount(path):
    return json.loads(subprocess.check_output(
        ['findmnt', '--json', '-o', 'FSTYPE,OPTIONS,SOURCE', '-T', path], text=True))['filesystems'][0]

def main():
    tokens = Path('/proc/cmdline').read_text().split()
    protected = any(t.startswith('overlayroot=tmpfs') for t in tokens)
    if not protected:
        print('cp2cl storage: maintenance mode; disk writes allowed')
        return
    root, lower, upper, boot, logs = [mount(p) for p in
        ['/', '/media/root-ro', '/media/root-rw', '/boot/firmware', '/var/log']]
    assert root['fstype'] == 'overlay', 'root is not overlay'
    assert lower['fstype'] == 'ext4' and 'ro' in lower['options'].split(','), 'lower root is writable'
    assert upper['fstype'] == 'tmpfs', 'overlay writes are not in RAM'
    assert boot['fstype'] == 'vfat' and 'ro' in boot['options'].split(','), 'boot partition is writable'
    assert logs['fstype'] == 'tmpfs', 'logs are not in RAM'
    backing = Path('/sys/block/zram0/backing_dev')
    assert not backing.exists() or backing.read_text().strip() == 'none', 'zram has disk writeback'
    print('cp2cl storage: protected; root/boot read-only, writes/logs in RAM, no zram disk backing')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('cp2cl storage protection FAILED: ' + str(e), file=sys.stderr)
        sys.exit(1)
