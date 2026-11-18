#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
key_file=${CP2CL_CARLIFE_KEY_FILE:-$ROOT/certificate/carlife-private.pem}
if [[ -f $key_file ]]; then
 python3 "$ROOT/scripts/carlife-key.py" check "$key_file"
 export CARLIFE_PRIVATE_KEY="$(cat -- "$key_file")"
fi
for f in "$ROOT"/scripts/*.sh; do bash -n "$f"; done
if [[ -f "$ROOT/.tools/root/usr/include/openssl/ssl.h" ]]; then
 export OPENSSL_INCLUDE_DIR="$ROOT/.tools/root/usr/include"
 export OPENSSL_LIB_DIR="$ROOT/.tools/root/usr/lib/x86_64-linux-gnu"
fi
log_run cargo-test cargo test --manifest-path "$ROOT/upstream/cp2cl/Cargo.toml" --workspace --locked
log_run integration python3 "$ROOT/tests/test_offline.py"

log_run readonly-boot-config python3 "$ROOT/tests/test_readonly.py"
log_run carlife-key-checks python3 "$ROOT/tests/test_carlife_key.py"

node_bin=${CP2CL_NODE_BINARY:-$(command -v node || true)}
if [[ -n $node_bin ]]; then
 log_run web-reconnect-js "$node_bin" --test "$ROOT/tests/test_web_reconnect.cjs"
else
 echo '网页断线恢复测试需 Node.js；可用 CP2CL_NODE_BINARY 指定路径单独启用。'
fi

log_run startup-replug python3 "$ROOT/tests/test_startup_replug.py"
