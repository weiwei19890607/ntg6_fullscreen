#!/usr/bin/env python3
"""Install the display name without changing controller addresses or pairings."""
import os
from pathlib import Path
import subprocess

if os.geteuid() != 0:
    raise SystemExit('需要 sudo')
if subprocess.check_output(['findmnt','-n','-o','FSTYPE','/'],text=True).strip() == 'overlay':
    raise SystemExit('请先进入维护模式并重启')
root=Path(__file__).resolve().parents[1]
name=(root/'configs/pi5/bluetooth-name').read_text().strip()
if not name or len(name.encode())>248 or any(ord(c)<32 or ord(c)==127 for c in name):
    raise SystemExit('无效的蓝牙名称')
path=Path('/etc/cp2cl/bluetooth-name')
path.write_text(name+'\n');path.chmod(0o644)
path=Path('/etc/bluetooth/main.conf')
lines=path.read_text().splitlines();out=[];general=False;found=False
for line in lines:
    if line.strip().startswith('['):
        general=line.strip()=='[General]'
        out.append(line)
        if general:
            out.append('Name = '+name);found=True
        continue
    if general and line.strip().startswith('Name') and line.partition('=')[0].strip()=='Name':
        continue
    out.append(line)
if not found:
    out=['[General]','Name = '+name]+out
path.write_text('\n'.join(out)+'\n')
print('蓝牙显示名称已保存；蓝牙服务重启后生效。配对记录及地址未修改。')
