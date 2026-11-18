#!/usr/bin/env bash
# Temporary AP test with an independent systemd timer restoring the Wi-Fi STA.
set -Eeuo pipefail
[[ $EUID == 0 ]] || exit 1
state=/run/cp2cl-window
logs=/var/log/cp2cl-window
install -d -m 700 "$state" "$logs"
case ${1:-} in
arm)
 [[ ! -e /etc/NetworkManager/conf.d/90-cp2cl-unmanaged.conf ]] || { echo '窗口模式需要保持 NM 的永久配置不变'; exit 1; }
 uuid=$(nmcli -t -f UUID,DEVICE connection show --active | awk -F: '$2=="wlan0" {print $1}')
 [[ $uuid =~ ^[0-9a-f-]{36}$ ]] || { echo '没有可恢复的 wlan0 STA 连接'; exit 1; }
 printf '%s\n' "$uuid" > "$state/sta-uuid"
 systemctl stop cp2cl-ap-rollback.timer cp2cl-ap-rollback.service 2>/dev/null || true
 systemctl reset-failed cp2cl-ap-rollback.service cp2cl-ap-probe.service 2>/dev/null || true
 systemd-run --unit=cp2cl-ap-rollback --on-active=150 --timer-property=AccuracySec=1 /usr/local/libexec/cp2cl-window rollback
 systemctl is-active --quiet cp2cl-ap-rollback.timer
 systemd-run --unit=cp2cl-ap-probe --property=TimeoutStartSec=140 /usr/local/libexec/cp2cl-window probe
 echo '150s 恢复 STA 已独立排程，AP 检查已启动。'
 ;;
probe)
 exec > "$logs/probe.log" 2>&1
 date --iso-8601=seconds
 nmcli device set wlan0 managed no
 if ! systemctl start cp2cl.service; then
  echo 'Bridge failed; enabling a temporary USB Ethernet recovery path.'
  systemctl stop cp2cl.service || true
  modprobe g_ether || true
  if [[ -e /sys/class/net/usb0 ]]; then
   ip addr replace 192.168.7.2/30 dev usb0
   ip link set usb0 up
  fi
 fi
 systemctl status cp2cl.service cp2cl-ap.service cp2cl-dhcp.service cp2cl-usb.service --no-pager || true
 iw dev; iw reg get
 hostapd_cli -i wlan0 status || true
 curl -fsS --max-time 3 http://192.168.4.1/api/status > "$logs/status.json" || true
 ls -l /sys/class/udc
 for f in /sys/class/udc/*/state /sys/class/udc/*/current_speed; do printf '%s: ' "$f"; cat "$f"; done
 journalctl -b -u cp2cl.service -u cp2cl-ap.service -u cp2cl-dhcp.service --no-pager -n 120
 for i in {1..4}; do
  sleep 15
  curl -fsS --max-time 3 http://192.168.4.1/api/status > "$logs/status-late-$i.json" || true
  bluetoothctl show || true
  vcgencmd get_throttled || true
 done
 journalctl -b -u cp2cl.service --no-pager -n 100
 echo 'AP probe finished. Independent rollback timer remains armed.'
 ;;
rollback)
 exec > "$logs/rollback.log" 2>&1
 date --iso-8601=seconds
 systemctl stop cp2cl.service cp2cl-dhcp.service cp2cl-ap.service || true
 systemctl stop hostapd.service || true
 nmcli device set wlan0 managed no
 ip addr flush dev wlan0 || true
 ip link set wlan0 down || true
 iw dev wlan0 set type managed || true
 nmcli device set wlan0 managed yes
 restored=no
 for i in {1..5}; do
  if nmcli --wait 15 connection up uuid "$(cat "$state/sta-uuid")"; then restored=yes; break; fi
  sleep 2
 done
 [[ $restored == yes ]]
 echo 'STA restored'
 ;;
*) echo '用法：cp2cl-window arm|probe|rollback'; exit 2;;
esac
