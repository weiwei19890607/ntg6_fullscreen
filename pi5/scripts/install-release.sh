#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $(findmnt -n -o FSTYPE /) == overlay ]]; then
 echo "当前为内存覆盖保护模式；请先 sudo cp2cl-mode maintenance，再重启后进行持久修改。" >&2; exit 1
fi
[[ $EUID == 0 && $(uname -m) == aarch64 ]] || exit 1
stage=${1:?}; release=${2:?}
[[ $release =~ ^[0-9a-f]{16}$ ]] || exit 2
grep -aq 'Raspberry Pi 5' /proc/device-tree/model || exit 1
[[ -f /etc/systemd/system/cp2cl.service && -f /etc/cp2cl/config.json ]] || { echo '先运行 bootstrap-pi5.sh 并重启'; exit 1; }
(cd "$stage"; sha256sum -c SHA256SUMS)
new=/opt/cp2cl/releases/$release
install -d "$new"
install -m 755 "$stage/cp2cl" "$new/cp2cl"
"$new/cp2cl" --check
if [[ ${CP2CL_STAGE_ONLY:-0} == 1 ]]; then
 ln -sfn "$new" /opt/cp2cl/staged
 [[ -e /opt/cp2cl/current ]] || ln -s "$new" /opt/cp2cl/current
 echo "已暂存 $release；未启动或启用服务"
 exit 0
fi
old=$(readlink -f /opt/cp2cl/current || true)
rollback() {
 systemctl stop cp2cl.service || true
 if [[ -n $old && -x $old/cp2cl ]]; then
  ln -sfn "$old" /opt/cp2cl/current.next; mv -Tf /opt/cp2cl/current.next /opt/cp2cl/current
  systemctl start cp2cl.service || true
 else rm -f /opt/cp2cl/current; fi
}
trap rollback ERR
systemctl stop cp2cl.service || true
ln -sfn "$new" /opt/cp2cl/current.next
mv -Tf /opt/cp2cl/current.next /opt/cp2cl/current
bash "$stage/scripts/install-startup-replug.sh"
systemctl daemon-reload
systemctl start cp2cl.service
ready=no
for i in {1..20}; do
 if systemctl is-active --quiet cp2cl.service && curl -fsS --max-time 2 http://192.168.4.1/api/status >/dev/null; then ready=yes; break; fi
 sleep 1
done
[[ $ready == yes ]] || { journalctl -u cp2cl.service -n 60 --no-pager; false; }
if [[ -n $old && $old != "$new" ]]; then ln -sfn "$old" /opt/cp2cl/previous; fi
systemctl enable cp2cl.service
trap - ERR
echo "部署完成：$release；仅验证进程和 HTTP，尚不代表 CarPlay/NTG6 成功"
