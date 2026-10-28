from pathlib import Path
import json,time,os
out=Path('/var/lib/smartpc-dashboard/v09-timing-proof/resources.jsonl')
with out.open('w') as f:
 for _ in range(24):
  pids=[]
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
    if 'check_game_timing_ui.py --theme apple' not in cmd and 'spawn_main(tracker_fd=' not in cmd:continue
    if 'python' not in cmd:continue
    s=(p/'stat').read_text().split();pids.append(dict(pid=int(p.name),userTicks=int(s[13]),systemTicks=int(s[14]),rssBytes=int(s[23])*os.sysconf('SC_PAGE_SIZE')))
   except (OSError,ValueError,IndexError):continue
  temp={}
  for z in Path('/sys/class/thermal').glob('thermal_zone*'):
   try:temp[(z/'type').read_text().strip()]=int((z/'temp').read_text())/1000
   except (OSError,ValueError):pass
  mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))}
  f.write(json.dumps(dict(monotonic=time.monotonic(),ticksPerSecond=os.sysconf('SC_CLK_TCK'),processes=pids,temperaturesC=temp,**mem))+'\n');f.flush();time.sleep(10)
