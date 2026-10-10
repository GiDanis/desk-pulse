"""Brief passive health sample of the installed GUI; no input or provider writes."""
from pathlib import Path
import json,os,subprocess,time
P=Path('/var/lib/smartpc-dashboard/v087-opening-proof');health=json.loads((P/'reboot-health.json').read_text());pid=health['guiHeartbeat']['pid'];ticks=os.sysconf('SC_CLK_TCK')
def read():
 text=Path(f'/proc/{pid}/stat').read_text();fields=text[text.rfind(')')+2:].split();cpu=(int(fields[11])+int(fields[12]))/ticks
 memory=next(line.split(':',1)[1].strip() for line in Path(f'/proc/{pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
 temps=[int(f.read_text())/1000 for f in Path('/sys/class/thermal').glob('thermal_zone*/temp')]
 return time.monotonic(),cpu,memory,temps
rows=[];previous=read()
for _ in range(20):
 time.sleep(1);current=read();rows.append({'time':time.time(),'cpuOneCorePercent':100*(current[1]-previous[1])/(current[0]-previous[0]),'rss':current[2],'temperaturesC':current[3]});previous=current
service=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=ActiveState,SubState,NRestarts'],text=True).splitlines());assert service=={'ActiveState':'active','SubState':'running','NRestarts':'0'},service
(P/'installed-passive-sample.json').write_text(json.dumps({'status':'passed','pid':pid,'scope':'20 seconds passive; activity not controlled; no pre/post idle CPU comparison','service':service,'meanCpuOneCorePercent':sum(r['cpuOneCorePercent'] for r in rows)/len(rows),'samples':rows},indent=2)+'\n')
