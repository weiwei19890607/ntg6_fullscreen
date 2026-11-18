#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $(findmnt -n -o FSTYPE /) == overlay ]]; then
 echo "当前为内存覆盖保护模式；请先 sudo cp2cl-mode maintenance，再重启后进行持久修改。" >&2; exit 1
fi
[[ $EUID == 0 ]] || exit 1
previous=$(readlink -f /opt/cp2cl/previous)
[[ $previous == /opt/cp2cl/releases/* && -x $previous/cp2cl ]]
current=$(readlink -f /opt/cp2cl/current)
systemctl stop cp2cl.service
ln -sfn "$previous" /opt/cp2cl/current.next
mv -Tf /opt/cp2cl/current.next /opt/cp2cl/current
ln -sfn "$current" /opt/cp2cl/previous
systemctl start cp2cl.service
