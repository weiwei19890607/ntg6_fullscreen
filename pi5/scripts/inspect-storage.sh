#!/usr/bin/env bash
set -Eeuo pipefail
lsusb
lsblk -e 7 -o NAME,PATH,MODEL,SERIAL,SIZE,TRAN,TYPE,MOUNTPOINTS
findmnt /
ls -l /dev/disk/by-id/usb-* 2>/dev/null || true
echo '仅查询；尚未执行刷写。记录新出现的 USB 盘的型号、容量、序列号及 by-id 路径后，交由用户明确确认。'
