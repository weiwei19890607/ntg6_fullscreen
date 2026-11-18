#!/usr/bin/env python3
"""Find the provisioned Pi on the specified local /24 by its pinned host key."""
import concurrent.futures,ipaddress,pathlib,socket,subprocess,sys
network=ipaddress.ip_network(sys.argv[1]);assert network.version==4 and network.prefixlen>=24
root=pathlib.Path(__file__).resolve().parents[1]
key=(root/'.tools/ssh/pi5-host-ed25519.pub').read_text().split()[1]
def probe(address):
 try:
  with socket.create_connection((str(address),22),timeout=.4):pass
  p=subprocess.run(['ssh-keyscan','-T','2','-t','ed25519',str(address)],capture_output=True,text=True,timeout=4)
  if any(line.split()[2:3]==[key] for line in p.stdout.splitlines() if not line.startswith('#')):return str(address)
 except (OSError,subprocess.TimeoutExpired):pass
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
 matches=[r for r in pool.map(probe,network.hosts()) if r]
print('\n'.join(matches))
if len(matches)!=1:raise SystemExit(1)
