#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
. /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 26.04 ]] || echo "提示：当前验证基线为 Ubuntu 26.04"
packages=(build-essential git wget ca-certificates pkg-config libssl-dev libusb-1.0-0-dev openssh-client xz-utils file binutils python3 qemu-user)
missing=()
for p in "${packages[@]}"; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || missing+=("$p"); done
if ((${#missing[@]})); then
  sudo apt-get update
  sudo apt-get install -y "${missing[@]}"
fi
if ! command -v cargo >/dev/null; then
  wget -q https://sh.rustup.rs -O "$ROOT/.rustup-init.sh"
  sh "$ROOT/.rustup-init.sh" -y --profile minimal --no-modify-path
  rm "$ROOT/.rustup-init.sh"
fi
rustc --version
cargo --version
