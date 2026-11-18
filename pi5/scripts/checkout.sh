#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
cd "$ROOT"
git submodule update --init
git -C upstream/cp2cl submodule update --init --recursive
apply_patch_file() {
 local dir=$1 patch=$2
 if git -C "$dir" apply --reverse --check "$patch" 2>/dev/null; then
  echo "已应用：${patch##*/}"
 elif git -C "$dir" apply --check "$patch"; then
  git -C "$dir" apply "$patch"
 else echo "补丁冲突：$patch" >&2; exit 1; fi
}
apply_patch_file "$ROOT/upstream/cp2cl/vendor/LIVI" "$ROOT/patches/0001-livi-compatibility.patch"
apply_patch_file "$ROOT/upstream/cp2cl" "$ROOT/patches/0002-cp2cl-offline-diagnostics.patch"
apply_patch_file "$ROOT/upstream/cp2cl" "$ROOT/patches/0003-airplay-auth-capability.patch"
apply_patch_file "$ROOT/upstream/cp2cl" "$ROOT/patches/0004-pi5-direct-accessory.patch"
apply_patch_file "$ROOT/upstream/cp2cl" "$ROOT/patches/0005-ntg6-paused-keepalive.patch"
apply_patch_file "$ROOT/upstream/cp2cl" "$ROOT/patches/0006-early-phone-connection.patch"
