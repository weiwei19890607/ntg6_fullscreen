#!/usr/bin/env bash
# Run ONLY after the human approves the recorded WD SN740 identity.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo '需要 sudo'; exit 1; }
[[ ${1:-} == --confirmed-wd-sn740-23222S404027 ]] || { echo '需要人工明确批准此序列号，默认拒绝'; exit 2; }
ROOT=$(cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
disk=/dev/disk/by-id/usb-nvme0n1_Raspberry_Pi_multi-function_USB_device_ab045208eb860d1e-0:0
[[ -b $disk ]] || { echo '目标 USB by-id 消失'; exit 1; }
[[ $(lsblk -bdno SIZE "$disk") == 512110190592 ]]
[[ $(lsblk -dno TRAN "$disk") == usb ]]
udevadm info -q property -n "$disk" | grep -qx 'ID_SERIAL_SHORT=ab045208eb860d1e'
[[ $(readlink -f "$disk") != /dev/nvme* ]]
# Check no mounted target partition; never unmount an unidentified device.
if lsblk -nr -o MOUNTPOINTS "$disk" | grep -q '[^[:space:]]'; then
 echo '目标仍有挂载，拒绝刷写；先审查并卸载目标分区'; exit 1
fi
env -u PI5_GADGET_COMMAND python3 scripts/read-gadget-console.py > logs/pre-flash-pi-identity.log
tr -d '\000\r' < logs/pre-flash-pi-identity.log > logs/pre-flash-pi-identity.txt
grep -q 'WD PC SN740 SDDPTQD-512G-1102' logs/pre-flash-pi-identity.txt
grep -q '23222S404027' logs/pre-flash-pi-identity.txt
expected=b8a393dc1c3701450b5fffbfe74368a98fb6eab7415ce456cc0cead886ea8780
printf '%s  %s\n' "$expected" '.tools/raspios-lite.img' | sha256sum -c -
lsblk -bd -o NAME,MODEL,SERIAL,SIZE,TRAN "$disk"
QT_QPA_PLATFORM=offscreen rpi-imager --cli .tools/raspios-lite.img "$(readlink -f "$disk")"
# Imager ejects the LUN after successful verification. Reinsert the same NVMe.
if ! blockdev --getsize64 "$disk" >/dev/null 2>&1; then
 PI5_GADGET_COMMAND='echo /dev/nvme0n1 > /sys/kernel/config/usb_gadget/rpimsg/functions/mass_storage.usb0/lun.0/file' python3 scripts/read-gadget-console.py > logs/gadget-reinsert.log
fi
udevadm settle
for i in {1..10}; do [[ -b $disk-part1 ]] && break; sleep 1; done
bash scripts/provision-boot.sh
bash scripts/provision-ssh-trust.sh
echo '镜像写入、校验及首次启动配置完成；尚未启动验证。'
