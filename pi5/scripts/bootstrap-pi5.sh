#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $(findmnt -n -o FSTYPE /) == overlay ]]; then
 echo "当前为内存覆盖保护模式；请先 sudo cp2cl-mode maintenance，再重启后进行持久修改。" >&2; exit 1
fi
prepare_only=${1:-}
[[ -z $prepare_only || $prepare_only == --prepare-only ]] || exit 2
[[ $EUID == 0 ]] || { echo '请在 Pi 上 sudo 运行'; exit 1; }
[[ $(uname -m) == aarch64 ]] && grep -aq 'Raspberry Pi 5' /proc/device-tree/model || { echo '仅支持 Raspberry Pi 5 ARM64'; exit 1; }
. /etc/os-release
[[ $ID == raspbian || $ID == debian ]] || { echo '目标必须是 Raspberry Pi OS Lite 64-bit'; exit 1; }
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# wlan0 will be taken from NetworkManager; do not sever an active SSH session.
if [[ -n ${SSH_CONNECTION:-} && $prepare_only != --prepare-only ]]; then
 client=${SSH_CONNECTION%% *}
 if ip route get "$client" | grep -q 'dev wlan0'; then
   echo '请改用以太网 SSH 后运行；此步骤会把 wlan0 交给 hostapd。'; exit 1
 fi
fi
packages=(dbus bluez hostapd dnsmasq-base iw kmod usbutils pciutils iproute2 rfkill curl ca-certificates)
missing=()
for p in "${packages[@]}"; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || missing+=("$p"); done
if ((${#missing[@]})); then apt-get update; apt-get install -y "${missing[@]}"; fi
install -d -m 700 /etc/cp2cl
install -d /etc/hostapd /opt/cp2cl/releases /usr/local/libexec /etc/systemd/journald.conf.d /etc/NetworkManager/conf.d
[[ -e /etc/cp2cl/config.json ]] || install -m 600 "$ROOT/configs/pi5/config.json" /etc/cp2cl/config.json
if [[ ! -e /etc/hostapd/hostapd.conf ]]; then
 password=$(od -An -N16 -tx1 /dev/urandom | tr -d ' 
')
 sed "s/@PASSPHRASE@/$password/" "$ROOT/configs/pi5/hostapd.conf.in" > /etc/hostapd/hostapd.conf
 chmod 600 /etc/hostapd/hostapd.conf
fi
if [[ $prepare_only != --prepare-only ]]; then
 install -m 644 "$ROOT/configs/pi5/90-cp2cl-unmanaged.conf" /etc/NetworkManager/conf.d/
fi
install -m 644 "$ROOT/configs/pi5/50-cp2cl-journal.conf" /etc/systemd/journald.conf.d/
install -m 644 "$ROOT/configs/systemd/"*.service /etc/systemd/system/
install -m 755 "$ROOT/scripts/pi5-prepare.sh" /usr/local/libexec/cp2cl-prepare
install -m 644 "$ROOT/configs/pi5/dnsmasq.conf" /etc/cp2cl/dnsmasq.conf
# Add under [all], otherwise an earlier board filter can silently disable this.
boot=/boot/firmware/config.txt
[[ -f $boot ]] || { echo '未发现 Raspberry Pi OS config.txt'; exit 1; }
if ! grep -q '^# BEGIN cp2cl Pi5$' "$boot"; then
 cp -an "$boot" "$boot.before-cp2cl"
 printf '
[all]
# BEGIN cp2cl Pi5
dtoverlay=dwc2,dr_mode=peripheral
# END cp2cl Pi5
' >> "$boot"
fi
# Refuse conflicting gadget overlays rather than editing unrelated config.
if grep -Eq 'modules-load=.*g_ether|modules-load=.*g_mass_storage' /boot/firmware/cmdline.txt; then
 echo 'cmdline 加载了竞争 gadget；先按 docs/03 手动移除该 gadget 模块'; exit 1
fi
python3 "$ROOT/scripts/configure-bluetooth-name.py"
systemctl unmask hostapd.service
systemctl disable --now hostapd.service
systemctl enable bluetooth.service
systemctl daemon-reload
# NM reload is deferred to reboot: keep provisioning connection alive.
echo '配置完成。请确认 AP 国家码 CN 符合所在地；重启后通过以太网部署。'
echo 'AP 密码仅保存在 /etc/hostapd/hostapd.conf；本脚本不显示凭据。'
