#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
remote=${1:?用法：deploy.sh user@pi [ARM64 binary]}
[[ $remote =~ ^[a-zA-Z0-9_.@:-]+$ && $remote != -* ]] || exit 2
binary=${2:-$ROOT/artifacts/cp2cl-aarch64-unknown-linux-musl}
readelf -h "$binary" | grep -q 'Machine:.*AArch64' || { echo '拒绝部署非 AArch64 ELF'; exit 1; }
[[ $("${SSH[@]}" "$remote" uname -m) == aarch64 ]] || { echo '目标不是 ARM64'; exit 1; }
if [[ $("${SSH[@]}" "$remote" findmnt -n -o FSTYPE /) == overlay ]]; then
 echo "目标为保护模式；请先 sudo cp2cl-mode maintenance 并重启，再部署。" >&2; exit 1
fi
"${SSH[@]}" "$remote" 'sudo -n true' || { echo '目标需要 sudo 权限；请先配置此 SSH 用户的部署权限'; exit 1; }
release=$(sha256sum "$binary" | cut -c1-16)
stage=$(mktemp -d); trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/bundle"
cp "$binary" "$stage/bundle/cp2cl"
cp -r "$ROOT/scripts" "$ROOT/configs" "$stage/bundle/"
(cd "$stage/bundle"; sha256sum cp2cl > SHA256SUMS; tar czf "$stage/release.tar.gz" .)
remote_stage=$("${SSH[@]}" "$remote" 'mktemp -d /tmp/cp2cl-deploy.XXXXXXXX')
[[ $remote_stage =~ ^/tmp/cp2cl-deploy\.[a-zA-Z0-9]+$ ]] || exit 1
"${SCP[@]}" "$stage/release.tar.gz" "$remote:$remote_stage/release.tar.gz"
log_run deploy "${SSH[@]}" "$remote" "tar xzf '$remote_stage/release.tar.gz' -C '$remote_stage' && sudo -n env CP2CL_STAGE_ONLY=${CP2CL_STAGE_ONLY:-0} bash '$remote_stage/scripts/install-release.sh' '$remote_stage' '$release'"
"${SSH[@]}" "$remote" "rm -rf '$remote_stage'"
