#!/usr/bin/env bash
set -euo pipefail
args=()
skip=no
for arg in "$@"; do
 if [[ $skip == yes ]]; then skip=no; continue; fi
 case $arg in
 -target|--target) skip=yes;;
 --target=*|-target=*) ;;
 *) args+=("$arg");;
 esac
done
exec zig cc -target aarch64-linux-musl "${args[@]}"
