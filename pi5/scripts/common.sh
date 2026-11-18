#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export PATH="$HOME/.cargo/bin:$PATH"
mkdir -p "$ROOT/logs" "$ROOT/artifacts"
log_run() { local name=$1; shift; "$@" 2>&1 | tee "$ROOT/logs/$name-$(date +%Y%m%dT%H%M%S).log"; }

SSH=(ssh)
SCP=(scp)
if [[ -n ${CP2CL_SSH_CONFIG:-} ]]; then
 SSH+=(-F "$CP2CL_SSH_CONFIG")
 SCP+=(-F "$CP2CL_SSH_CONFIG")
fi
