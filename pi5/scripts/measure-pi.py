#!/usr/bin/env python3
"""Sample idle/runtime resources; never labels these as real CarPlay load."""
import json,os,pathlib,subprocess,sys,time
seconds=int(sys.argv[1]) if len(sys.argv)>1 else 20
assert 1<=seconds<=60
pid=int(subprocess.check_output(['systemctl','show','cp2cl','-p','MainPID','--value'],text=True))
assert pid>0
proc=pathlib.Path('/proc')/str(pid)
def sample():
 p=(proc/'stat').read_text().rsplit(') ',1)[1].split()
 disk=[int(x) for x in pathlib.Path('/sys/block/nvme0n1/stat').read_text().split()]
 status=(proc/'status').read_text().splitlines()
 rss=next(int(l.split()[1]) for l in status if l.startswith('VmRSS:'))
 return {'monotonic':time.monotonic(),'cpu_ticks':int(p[11])+int(p[12]),'start_ticks':int(p[19]),'rss_kib':rss,'disk_read_sectors':disk[2],'disk_written_sectors':disk[6],'temp_millic':int(pathlib.Path('/sys/class/thermal/thermal_zone0/temp').read_text())}
a=sample();time.sleep(seconds);b=sample()
assert a['start_ticks']==b['start_ticks']
elapsed=b['monotonic']-a['monotonic']
r={'mode':'runtime_sample_without_real_carplay','pid':pid,'elapsed_seconds':elapsed,'cpu_percent_one_core':100*(b['cpu_ticks']-a['cpu_ticks'])/os.sysconf('SC_CLK_TCK')/elapsed,'rss_kib':b['rss_kib'],'whole_nvme_read_bytes':512*(b['disk_read_sectors']-a['disk_read_sectors']),'whole_nvme_written_bytes':512*(b['disk_written_sectors']-a['disk_written_sectors']),'temperature_c':b['temp_millic']/1000,'throttled':subprocess.check_output(['vcgencmd','get_throttled'],text=True).strip(),'start':a,'end':b}
print(json.dumps(r,indent=2))
