#!/usr/bin/env python3
"""Query official gadget console; explicit maintenance via PI5_GADGET_COMMAND."""
import errno,os,select,sys,termios,time
fd=os.open('/dev/ttyACM0',os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
old=termios.tcgetattr(fd);attrs=termios.tcgetattr(fd)
attrs[0]=0;attrs[1]=0;attrs[3]=0;attrs[4]=termios.B115200;attrs[5]=termios.B115200
termios.tcsetattr(fd,termios.TCSANOW,attrs)
def exchange(data,seconds):
 os.write(fd,data.encode());out=b'';end=time.monotonic()+seconds
 while time.monotonic()<end:
  if select.select([fd],[],[],.2)[0]:
   try:out+=os.read(fd,65536)
   except BlockingIOError:pass
   except OSError as e:
    if e.errno in (errno.EIO,errno.ENODEV):break
    raise
 sys.stdout.write(out.decode(errors='replace'));sys.stdout.flush();return out
try:
 out=exchange('\n',1)
 if b'login:' in out:out=exchange('root\n',1)
 if b'Password:' in out:out=exchange('\n',1)
 command = os.environ.get("PI5_GADGET_COMMAND")
 if command is None: command = "echo PI5_STORAGE_ID; cat /proc/device-tree/model; echo; cat /sys/block/nvme0n1/device/model; cat /sys/block/nvme0n1/device/serial; cat /sys/block/nvme0n1/size; cat /proc/partitions; cat /sys/class/thermal/thermal_zone0/temp; dmesg | tail -25"
 exchange(command+"\n",2)
finally:os.close(fd)  # Keep host-side echo disabled to avoid an ACM echo loop.
