#!/usr/bin/env python3
"""Download and verify an official Lite image. Never opens a block device."""
import hashlib,json,lzma,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
os=json.loads((root/'configs/pi5/os-image.json').read_text())
p=root/'artifacts'/os['url'].split('/')[-1];p.parent.mkdir(exist_ok=True)
if not p.exists():
 partial=p.with_suffix(p.suffix+'.partial')
 urllib.request.urlretrieve(os['url'],partial);partial.rename(p)
h=hashlib.sha256();total=0
with lzma.open(p) as f:
 while data:=f.read(4*1024*1024):h.update(data);total+=len(data)
if total!=os['extract_size'] or h.hexdigest()!=os['extract_sha256']:
 raise SystemExit('镜像校验失败；不准刷写，请移走损坏文件后重试')
report=f'{p}\nExtracted bytes: {total}\nSHA256: {h.hexdigest()}\nMATCH official Imager metadata\n'
(root/'logs').mkdir(exist_ok=True);(root/'logs/os-image-verified.txt').write_text(report);print(report)
