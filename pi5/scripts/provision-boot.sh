#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID == 0 ]] || exit 1
ROOT=$(cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
disk=/dev/disk/by-id/usb-nvme0n1_Raspberry_Pi_multi-function_USB_device_ab045208eb860d1e-0:0
[[ -b $disk && $(lsblk -bdno SIZE "$disk") == 512110190592 && $(lsblk -dno TRAN "$disk") == usb ]]
bootpart="$disk-part1"
[[ -b $bootpart ]]
# Desktop automount may reappear after Imager reinsertion.
while read -r target; do [[ -z $target ]] || umount "$target"; done < <(findmnt -rn -S "$(readlink -f "$bootpart")" -o TARGET)
mountdir=$(mktemp -d)
trap 'mountpoint -q "$mountdir" && umount "$mountdir"; rmdir "$mountdir"' EXIT
mount "$bootpart" "$mountdir"
[[ -f $mountdir/config.txt && -f $mountdir/kernel_2712.img ]]
install -m 644 .tools/pi5-user-data "$mountdir/user-data"
install -m 644 .tools/pi5-meta-data "$mountdir/meta-data"
install -m 600 .tools/pi5-network-config "$mountdir/network-config"
sync
cmp .tools/pi5-user-data "$mountdir/user-data"
cmp .tools/pi5-meta-data "$mountdir/meta-data"
cmp .tools/pi5-network-config "$mountdir/network-config"
umount "$mountdir"
echo 'Boot cloud-init files written and compared successfully.'
