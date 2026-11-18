#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID == 0 ]] || exit 1
[[ $(findmnt -n -o FSTYPE /) != overlay ]] || { echo '需要维护模式才能持久安装'; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
command -v python3 >/dev/null
install -d -m 755 /usr/local/lib/cp2cl
install -m 755 "$root/scripts/startup-replug.py" /usr/local/lib/cp2cl/startup-replug.py
install -m 644 "$root/configs/systemd/cp2cl-startup-replug.service" /etc/systemd/system/
if [[ ! -f /etc/cp2cl/startup-replug.json ]]; then
 install -m 600 /dev/stdin /etc/cp2cl/startup-replug.json <<<'{"enabled":false}'
fi
systemctl daemon-reload
systemctl enable cp2cl-startup-replug.service
