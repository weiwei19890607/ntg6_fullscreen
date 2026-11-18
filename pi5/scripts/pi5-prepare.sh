#!/usr/bin/env bash
set -Eeuo pipefail
case ${1:-} in
usb)
 modprobe dwc2
 modprobe libcomposite
 mountpoint -q /sys/kernel/config || mount -t configfs configfs /sys/kernel/config
 for i in {1..30}; do compgen -G '/sys/class/udc/*' >/dev/null && break; sleep 1; done
 compgen -G '/sys/class/udc/*' >/dev/null || { echo '没有 UDC；检查 dwc2 和重启状态'; exit 1; }
 for g in /sys/kernel/config/usb_gadget/*; do
  [[ -e $g/UDC ]] || continue
  [[ ${g##*/} == cp2cl || -z $(cat "$g/UDC") ]] || { echo "UDC 已被 $g 占用"; exit 1; }
 done
 if lsmod | grep -Eq '^g_(ether|mass_storage|multi) '; then
  echo '检测到竞争 gadget 模块'; exit 1
 fi
 ;;
ap)
 for i in {1..5}; do
  if /usr/sbin/hostapd -B -P /run/hostapd.pid /etc/hostapd/hostapd.conf; then exit 0; fi
  sleep 2
 done
 echo 'hostapd failed after five attempts'; exit 1
 ;;
network)
 for i in {1..30}; do [[ -e /sys/class/net/wlan0 ]] && break; sleep 1; done
 [[ -e /sys/class/net/wlan0 ]]
 rfkill unblock wifi
 ip link set wlan0 up
 iw dev wlan0 set power_save off
 ip addr replace 192.168.4.1/24 dev wlan0
 ;;
*) echo '用法：cp2cl-prepare usb|network|ap'; exit 2;;
esac
