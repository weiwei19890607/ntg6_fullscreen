#!/usr/bin/env bash
# Run in writable maintenance mode after preserving a private configuration backup.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo '需要 sudo'; exit 1; }
grep -aq 'Raspberry Pi 5' /proc/device-tree/model
[[ $(findmnt -n -o FSTYPE /) == ext4 ]] || { echo '先进入维护模式并重启'; exit 1; }
ROOT=$(cd -- "$(dirname "$0")/.." && pwd)
dpkg-query -W -f='${Status}' overlayroot | grep -q 'install ok installed'
[[ -f /usr/share/initramfs-tools/scripts/init-bottom/overlayroot ]]
install -m 755 "$ROOT/scripts/cp2cl-mode.py" /usr/local/sbin/cp2cl-mode
install -m 755 "$ROOT/scripts/pi5-storage-check.py" /usr/local/libexec/cp2cl-storage-check
install -m 644 "$ROOT/configs/systemd/cp2cl-maintenance-boot.service" /etc/systemd/system/cp2cl-maintenance-boot.service
systemctl enable cp2cl-maintenance-boot.service
install -d /etc/systemd/system/cp2cl.service.d /etc/rpi/swap.conf.d /etc/initramfs-tools/scripts/init-bottom
install -m 755 "$ROOT/configs/initramfs/zz-cp2cl-overlay-fstab" /etc/initramfs-tools/scripts/init-bottom/zz-cp2cl-overlay-fstab
cat > /etc/rpi/swap.conf.d/90-cp2cl-memory-only.conf <<'EOF'
[Main]
Mechanism=zram
EOF
cat > /etc/systemd/system/cp2cl.service.d/20-storage.conf <<'EOF'
[Unit]
RequiresMountsFor=/var/log /boot/firmware
[Service]
ExecStartPre=/usr/local/libexec/cp2cl-storage-check
EOF
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/fstab');lines=[]
for line in p.read_text().splitlines():
    fields=line.split()
    if fields and not line.lstrip().startswith('#'):
        if fields[1]=='/boot/firmware':
            opts=[x for x in fields[3].split(',') if x not in ('ro','rw')]+['ro']
            fields[3]=','.join(opts);line='\t'.join(fields)
        if fields[1]=='/var/log':
            continue
    lines.append(line)
lines.append('tmpfs /var/log tmpfs defaults,nosuid,nodev,noexec,size=64M,mode=0755 0 0')
p.write_text('\n'.join(lines)+'\n')
PY
# Disable unattended package/maintenance jobs which otherwise consume overlay RAM.
for unit in apt-daily.timer apt-daily-upgrade.timer dpkg-db-backup.timer man-db.timer logrotate.timer e2scrub_all.timer fstrim.timer rpi-zram-writeback.timer rpi-zram-writeback.service; do
 systemctl mask --now "$unit"
done
systemctl daemon-reload
# Include both the package overlay hook and the local remount compatibility hook.
update-initramfs -u -k "$(uname -r)"
lsinitramfs "/boot/initrd.img-$(uname -r)" | grep '^scripts/init-bottom/overlayroot$' >/dev/null
/usr/local/sbin/cp2cl-mode protect
sync
echo '只读保护已配置，需重启验证。配对及配置基线保持不变。'
