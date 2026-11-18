#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
[[ $(uname -m) == x86_64 ]] || { echo '此脚本固定主机为 x86_64'; exit 1; }
rustup target add aarch64-unknown-linux-musl
python3 - "$ROOT" <<'PY'
import pathlib,json,sys,urllib.request,hashlib,tarfile
root=pathlib.Path(sys.argv[1]);meta=json.loads((root/'configs/pi5/zig-toolchain.json').read_text())
tools=root/'.tools';tools.mkdir(exist_ok=True)
name=meta['tarball'].split('/')[-1];archive=tools/name
if not archive.exists():urllib.request.urlretrieve(meta['tarball'],archive)
if hashlib.sha256(archive.read_bytes()).hexdigest()!=meta['shasum']:raise SystemExit('Zig SHA256 mismatch')
with tarfile.open(archive) as t:t.extractall(tools,filter='data')
print('Verified Zig toolchain ready')
PY
