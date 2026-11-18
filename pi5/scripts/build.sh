#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
target=${1:-native}
# Production builds must answer the head unit's authentication challenge.
# Read the ignored local file without putting its contents in command arguments
# or build logs. Explicitly allow a keyless build only for offline diagnostics.
key_file=${CP2CL_CARLIFE_KEY_FILE:-$ROOT/certificate/carlife-private.pem}
if [[ -f $key_file ]]; then
  python3 "$ROOT/scripts/carlife-key.py" check "$key_file"
  export CARLIFE_PRIVATE_KEY="$(cat -- "$key_file")"
elif [[ $target == aarch64-unknown-linux-musl && ${CP2CL_ALLOW_NO_CARLIFE_KEY:-0} != 1 ]]; then
  echo '正式 ARM64 构建缺少 CarLife 密钥；请设置 CP2CL_CARLIFE_KEY_FILE。离线诊断可显式设置 CP2CL_ALLOW_NO_CARLIFE_KEY=1。' >&2
  exit 1
fi
cd "$ROOT/upstream/cp2cl"
args=(build --locked --bin cp2cl)
if [[ $target == native ]]; then
  # User-local Ubuntu headers are a fallback when sudo is unavailable.
  if [[ -f "$ROOT/.tools/root/usr/include/openssl/ssl.h" ]]; then
    export OPENSSL_INCLUDE_DIR="$ROOT/.tools/root/usr/include"
    export OPENSSL_LIB_DIR="$ROOT/.tools/root/usr/lib/x86_64-linux-gnu"
  fi
  output=target/debug/cp2cl
elif [[ $target == aarch64-unknown-linux-musl ]]; then
  rustup target add "$target"
  command -v zig >/dev/null || export PATH="$ROOT/.tools/zig-x86_64-linux-0.17.1:$PATH"
  command -v zig >/dev/null || { echo '需要 zig（本次验证版本 0.17.1）'; exit 1; }
  unset OPENSSL_DIR OPENSSL_LIB_DIR OPENSSL_INCLUDE_DIR
  export CC_aarch64_unknown_linux_musl="$ROOT/scripts/zig-cc.sh"
  export CFLAGS_aarch64_unknown_linux_musl="-fno-sanitize=undefined"
  export AR_aarch64_unknown_linux_musl="$ROOT/scripts/zig-ar.sh"
  export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER="$(rustc --print sysroot)/lib/rustlib/$(rustc -vV | sed -n 's/^host: //p')/bin/rust-lld"
  args+=(--release --target "$target")
  output=target/$target/release/cp2cl
else
  echo '用法：build.sh [native|aarch64-unknown-linux-musl]' >&2; exit 2
fi
log_run "build-$target" cargo "${args[@]}"
cp "$output" "$ROOT/artifacts/cp2cl-$target"
file "$ROOT/artifacts/cp2cl-$target"
sha256sum "$ROOT/artifacts/cp2cl-$target" > "$ROOT/artifacts/cp2cl-$target.sha256"
