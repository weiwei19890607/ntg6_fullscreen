#!/usr/bin/env python3
"""Collect evidence; a successful command is not a successful end-to-end test."""
import datetime,json,pathlib,subprocess,sys
checks={
 "identity":"cat /etc/os-release; uname -a; cat /proc/device-tree/model",
 "nvme":"findmnt -no SOURCE,FSTYPE /; lsblk -o NAME,MODEL,SERIAL,SIZE,TRAN,MOUNTPOINTS; lspci -nn; dmesg | tail -100",
 "usb":"ls -la /sys/class/udc; lsmod; findmnt -t configfs,functionfs; lsusb -t",
 "wifi":"iw dev; iw phy; iw reg get; ip addr show wlan0; hostapd_cli -i wlan0 status",
 "bluetooth":"bluetoothctl show; busctl --system list; systemctl status bluetooth --no-pager",
 "services":"systemctl status cp2cl cp2cl-ap cp2cl-dhcp cp2cl-usb --no-pager; journalctl -b -u cp2cl -n 150 --no-pager",
 "performance":"systemd-analyze; systemd-analyze critical-chain cp2cl.service; systemctl show cp2cl -p ExecMainStartTimestampMonotonic -p MemoryCurrent -p CPUUsageNSec -p IOReadBytes -p IOWriteBytes; vcgencmd measure_temp; vcgencmd get_throttled; cat /proc/diskstats",
}
report={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"tests":{},"end_to_end":"NOT_TESTED"}
for name,cmd in checks.items():
 try:
  p=subprocess.run(['bash','-o','pipefail','-c',cmd],text=True,capture_output=True,timeout=45)
  report['tests'][name]={"command":cmd,"returncode":p.returncode,"output":p.stdout,"stderr":p.stderr,"status":"EVIDENCE_ONLY_REVIEW_REQUIRED"}
 except subprocess.TimeoutExpired:report['tests'][name]={"command":cmd,"status":"TIMEOUT"}
p=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'hardware-report.json')
p.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(p)
