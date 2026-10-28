"""Resume each production checkpoint on a temporary copy; never train originals."""
import hashlib,json,multiprocessing as mp,os,shutil,sqlite3,sys,tempfile,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');PROJECT=H/'smartpc-v09-rc10-project';SOURCE=H/'.local/share/SmartPC/SmartPC/game';P=H/'v09-optimization-proof'
sys.path.insert(0,str(PROJECT/'dashboard'))
from game_store import GameStore
from game_worker import worker_main

def original_hashes():
 with sqlite3.connect('file:'+str(SOURCE/'game.sqlite')+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  rows=[dict(r) for r in db.execute('SELECT * FROM drivers ORDER BY number')]
 return {'drivers':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),
         'policies':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE/'policies').glob('*.json')}}

def wait_message(conn,kind,epoch,timeout=45):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if conn.poll(.1):
   msg=conn.recv()
   if msg.get('session')!=epoch:continue
   assert msg['type']!='error',msg
   if msg['type']==kind:return msg
 raise AssertionError('Timeout '+kind)

def main():
 before=original_hashes();reports=[]
 with tempfile.TemporaryDirectory(prefix='smartpc-rc9-checkpoints-') as root:
  shutil.copytree(SOURCE,Path(root)/'game');store=GameStore(Path(root)/'game')
  context=mp.get_context('spawn')
  for driver in store.drivers():
   epoch=driver['id'];parent,child=context.Pipe();frames=context.Queue(maxsize=2)
   proc=context.Process(target=worker_main,args=(child,frames,str(Path(root)/'game'),{'mode':'impara','driver':driver['id'],'epoch':epoch,'participants':[],'selected':0,'laps':3,'track':'oval-1'}))
   proc.start();child.close()
   try:
    wait_message(parent,'ready',epoch);time.sleep(3)
    tick=time.monotonic();parent.send({'type':'pause'});wait_message(parent,'paused',epoch)
    latency=time.monotonic()-tick
    if driver['profile']['algorithm']!='pure_pursuit':wait_message(parent,'saved',epoch)
    first=store.driver(driver['id'])
    assert first['profile']['version']==2
    for key in ('algorithm','seed','population','hidden'):
     assert first['profile'][key]==driver['profile'][key]
    with store.connect() as db:
     archives=[json.loads(r[0]) for r in db.execute('SELECT state FROM profile_paths WHERE id=?',(driver['id'],))]
    assert any(a['checkpoint']==driver['checkpoint'] and a['steps']==driver['steps'] and a['seconds']==driver['seconds'] for a in archives)
    assert store.total_seconds(driver['id'])>=driver['seconds']
    if driver['profile']['algorithm']=='pure_pursuit':
     assert first['steps']==0 and first['seconds']==0 and first['policy']
     assert store.load(first['policy'])['algorithm']=='pure_pursuit'
    else:
     assert first['steps']>0 and first['seconds']>0,first
     parent.send({'type':'resume'});wait_message(parent,'ready',epoch);time.sleep(1)
     parent.send({'type':'pause'});wait_message(parent,'paused',epoch);wait_message(parent,'saved',epoch)
     assert store.driver(driver['id'])['steps']>=first['steps']
     assert store.driver(driver['id'])['seconds']>first['seconds']
    reports.append({'name':driver['name'],'method':driver['profile']['algorithm'],'observation':driver['profile']['observation'],'hadCheckpoint':bool(driver['checkpoint']),'resumed':True,'stepsBefore':driver['steps'],'stepsAfter':store.driver(driver['id'])['steps'],'pauseAckSeconds':latency})
    print('Checkpoint passed: '+driver['name'],flush=True)
   finally:
    if proc.is_alive():parent.send({'type':'stop'});proc.join(5)
    if proc.is_alive():proc.terminate();proc.join(2)
    assert not proc.is_alive();proc.close();parent.close();frames.close()
 assert original_hashes()==before
 (P/'production-checkpoints-copy.json').write_text(json.dumps({'status':'passed','originalsUnchanged':True,'originalPathsArchived':True,'immutableParametersPreserved':True,'pilots':reports},indent=2)+'\n')
if __name__=='__main__':main()
