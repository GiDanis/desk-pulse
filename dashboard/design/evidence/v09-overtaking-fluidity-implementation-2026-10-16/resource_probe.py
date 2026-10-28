"""Read-only CPU/RAM/thermal samples; no inferred GPU/NPU utilization."""
from pathlib import Path
import time,os,json,argparse
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=int,default=7200);a=p.parse_args()
start=time.monotonic();previous={};hz=os.sysconf('SC_CLK_TCK')
with a.output.open('w') as stream:
 while time.monotonic()-start<a.seconds:
  now=time.monotonic();processes=[]
  for path in Path('/proc').glob('[0-9]*'):
   try:
    cmd=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
    if 'game-runtime/bin/python' not in cmd:continue
    fields=(path/'stat').read_text().split();cpu=(int(fields[13])+int(fields[14]))/hz
    rss=int(fields[23])*os.sysconf('SC_PAGE_SIZE')
    old=previous.get(path.name);previous[path.name]=(now,cpu)
    processes.append(dict(pid=int(path.name),role='worker' if 'spawn_main' in cmd else 'gui' if 'check_game_' in cmd or 'main.py' in cmd else 'helper',cpuPercent=100*(cpu-old[1])/(now-old[0]) if old else None,rssMiB=rss/1024**2))
   except (OSError,ValueError,IndexError):pass
  memory={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
  thermal={}
  for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
   try:thermal[(zone/'type').read_text().strip()]=int((zone/'temp').read_text())/1000
   except (OSError,ValueError):pass
  stream.write(json.dumps(dict(monotonic=now,processes=processes,availableMiB=memory['MemAvailable']/1024,thermal=thermal))+'\n');stream.flush();time.sleep(2)
