#!/usr/bin/env bash
# First-install host keys, read back locally before the target joins the network.
set -Eeuo pipefail
[[ $EUID == 0 ]] || exit 1
ROOT=$(cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
disk=/dev/disk/by-id/usb-nvme0n1_Raspberry_Pi_multi-function_USB_device_ab045208eb860d1e-0:0
[[ -b $disk && $(lsblk -bdno SIZE "$disk") == 512110190592 && $(lsblk -dno TRAN "$disk") == usb ]]
rootdir=$(mktemp -d)
trap 'mountpoint -q "$rootdir" && umount "$rootdir"; rmdir "$rootdir"' EXIT
mount "$disk-part2" "$rootdir"
[[ -f $rootdir/etc/rpi-issue && -d $rootdir/etc/ssh ]]
ssh-keygen -A -f "$rootdir"
install -m 644 "$rootdir/etc/ssh/ssh_host_ed25519_key.pub" .tools/ssh/pi5-host-ed25519.pub
ssh-keygen -lf .tools/ssh/pi5-host-ed25519.pub
sync
umount "$rootdir"
echo 'SSH host key provisioned; verify against this public key on first connection.'
