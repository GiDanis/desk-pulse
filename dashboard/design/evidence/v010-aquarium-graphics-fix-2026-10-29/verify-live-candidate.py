"""Verify the installed service via its real keypad and GUI heartbeat, no test data."""
from pathlib import Path
import hashlib,json,os,pwd,sqlite3,struct,subprocess,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');DATA=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC');EVENT=struct.Struct('@llHHi')
def service():return dict(r.split('=',1) for r in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState,NRestarts,MainPID'],text=True).splitlines())
def beat():
 pid=service()['MainPID'];uid=pwd.getpwnam('smartpc').pw_uid
 return json.loads((Path('/proc')/pid/'root/tmp'/('smartpc-theme-health-'+str(uid))/(hashlib.sha256(os.fsencode(str(DATA))).hexdigest()+'.json')).read_text())
def wait_surface(surface,limit=20):
 end=time.monotonic()+limit
 while time.monotonic()<end:
  try:
   b=beat()
   if b['ready'] and time.time()-b['time']<5 and b.get('context',{}).get('surfaceId')==surface:return b
  except (FileNotFoundError,KeyError,ValueError):pass
  time.sleep(.25)
 raise AssertionError('Live surface did not become ready: '+surface)
keypad=None
for e in Path('/sys/class/input').glob('event*'):
 d=e/'device'
 try:
  if (d/'id/vendor').read_text().strip()=='413d' and (d/'id/product').read_text().strip()=='553a' and (d/'phys').read_text().strip().endswith('/input0'):keypad=Path('/dev/input')/e.name
 except OSError:pass
assert keypad is not None,'Dedicated keypad not connected'
fd=os.open(keypad,os.O_WRONLY|os.O_NONBLOCK)
def key(position):
 codes={1:19,2:31,3:111,4:30,5:44,6:21,7:46,8:47,9:45};mods=[] if position==3 else [29]+([42] if position==1 else [])
 def emit(kind,code,value):os.write(fd,EVENT.pack(0,0,kind,code,value));os.write(fd,EVENT.pack(0,0,0,0,0))
 try:
  for c in mods:emit(1,c,1)
  emit(1,codes[position],1);time.sleep(.04);emit(1,codes[position],0)
 finally:
  for c in reversed(mods):emit(1,c,0)
 time.sleep(.2)
def population():
 db=DATA/'aquarium/aquarium.sqlite';end=time.monotonic()+15
 while not db.exists() and time.monotonic()<end:time.sleep(.25)
 with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as con:
  assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not con.execute('PRAGMA foreign_key_check').fetchall()
  rows=con.execute('SELECT f.id,f.species,v.id FROM visits v JOIN fish f ON v.fish=f.id WHERE v.ended IS NULL ORDER BY v.slot').fetchall();assert len(rows)==6,rows
 return rows
try:
 key(1);wait_surface('home.now');key(4);first=wait_surface('aquarium.3d');time.sleep(3);rows=population()
 key(9)
 for _ in range(5):key(8)
 key(5);management=wait_surface('aquarium.manage');key(7);wait_surface('aquarium.3d');assert population()==rows
 (W/'live-before-restart.json').write_text(json.dumps({'rows':rows,'pid':first['pid']},indent=2)+'\n')
 for _ in range(10):
  key(1);wait_surface('home.now');key(4);wait_surface('aquarium.3d')
 assert population()==rows
 report={'status':'passed','installedVersion':'0.10.2-rc.3','keypadDevice':str(keypad),'guiPid':first['pid'],'aquariumSurface':first['context'],'managementSurface':management['context'],'activeFish':len(rows),'species':sorted({r[1] for r in rows}),'storeIntegrity':'passed','identitiesPreservedAcrossManagement':True,'service':service(),'scope':'Synthetic events through the real dedicated evdev keypad; real installed process and persistent store. Not physical-keypad or optical FPS proof.'}
 (W/'live-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
finally:os.close(fd)
