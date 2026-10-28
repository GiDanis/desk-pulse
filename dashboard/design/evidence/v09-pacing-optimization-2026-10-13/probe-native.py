"""Real Main: resumed Evo capture, then identical scene replay with 32/8/30 Hz."""
import argparse,gzip,json,os,statistics,sys,time,faulthandler
faulthandler.enable(all_threads=True)
from pathlib import Path
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=('capture','replay32','replay8','smooth30'),required=True);p.add_argument('--seconds',type=float,default=30);p.add_argument('--label',default='');p.add_argument('--theme',default='base');p.add_argument('--fresh-population',action='store_true');a=p.parse_args()
 sys.path.insert(0,str(a.project/'dashboard'))
 from theme_fixture_support import isolate_process,LegacyHarness
 from PySide6.QtCore import QTimer,Qt
 import shiboken6
 private,base=isolate_process();h=LegacyHarness(base,dict(theme=a.theme,variant='day',motion='normal',game=True))
 a.output.mkdir(parents=True,exist_ok=True);frames=[];poses={};gaps={};last_moves={};callback_cost=[];scene_gaps=[];last_scene=0.;corpus=[];sampled=[];resource_times=[];main_pid=os.getpid();hz=os.sysconf('SC_CLK_TCK');started=None;source_meta={};last_cpu=None
 
 def distribution(rows):
  if not rows:return None
  v=sorted(rows);return dict(n=len(v),medianMs=statistics.median(v)*1000,p95Ms=v[int(.95*(len(v)-1))]*1000,p99Ms=v[int(.99*(len(v)-1))]*1000,maxMs=max(v)*1000,stallsOver100ms=sum(x>.1 for x in v))
 
 def objects(item):
  yield item
  for child in item.childItems():yield from objects(child)
 
 
 def receive_scene():
  global last_scene
  now=time.monotonic()
  if started is None:return
  epoch=(h.game.scene.get('meta',{}).get('generation'),h.game.scene.get('meta',{}).get('presentation'))
  if epoch!=receive_scene.epoch:
   last_moves.clear();poses.clear();receive_scene.epoch=epoch
  if last_scene:scene_gaps.append(now-last_scene)
  last_scene=now
  if a.mode=='capture':corpus.append((now-started,h.game.scene))
 
 
 receive_scene.epoch=None
 
 def rendered():
  if started is not None:frames.append(time.monotonic())
 
 
 def animated():
  if started is None:return
  tick=time.monotonic()
  if any(not shiboken6.isValid(car) for car in cars) or len(cars)!=len(h.game.scene.get('cars',[])):
   cars[:]=[x for x in objects(h.window.contentItem()) if x.objectName().startswith('gameCar')]
  rows=h.game.scene.get('cars',[])
  for i,car in enumerate(cars):
   if i>=len(rows) or rows[i].get('completed') or rows[i].get('speed',0)<.5:continue
   if not shiboken6.isValid(car) or not car.property('visible'):continue
   key=car.objectName();value=(car.x(),car.y(),car.rotation())
   if key in poses and any(abs(x-y)>1e-7 for x,y in zip(value,poses[key])):
    if key in last_moves:gaps.setdefault(key,[]).append(tick-last_moves[key])
    last_moves[key]=tick
   poses[key]=value
  callback_cost.append(time.monotonic()-tick)
 
 
 def resources():
  global last_cpu
  now=time.monotonic();pid=main_pid;cpu={}
  for q in Path(f'/proc/{pid}/task').glob('*'):
   try:
    v=(q/'stat').read_text().rsplit(')',1)[1].split();cpu[q.name]=(int(v[11])+int(v[12]),(q/'comm').read_text().strip())
   except OSError:pass
  row=dict(at=now-started,rssKB=next(int(x.split()[1]) for x in Path(f'/proc/{pid}/status').read_text().splitlines() if x.startswith('VmRSS:')))
  if last_cpu:
   dt=now-last_cpu[0];row['threads']=[dict(tid=k,name=v[1],cpuOneCore=100*(v[0]-last_cpu[1].get(k,v)[0])/hz/dt) for k,v in cpu.items()]
  last_cpu=(now,cpu);sampled.append(row)
 
 
 try:
  h.expression('familyId="game"');h.wait_ready()
  if a.mode=='capture':
   saved=json.loads((a.output/'evo-source.json').read_text());source_meta=saved['metadata'];checkpoint=saved['checkpoint'];s=h.game._store;identity=s.drivers()[0]['id']
   s.set_profile(identity,source_meta['profile'],allow_reconfigure=True)
   from game_academy_trainer import AcademyTrainer
   trainer=AcademyTrainer(source_meta['profile'],'oval-1',checkpoint)
   if a.fresh_population:
    trainer.inflight=None;trainer.collected=None;trainer.review=None;trainer.evaluation=None;trainer.iterator=None;trainer.fitness[:]=0;trainer.reset_episodes();checkpoint=trainer.checkpoint(checkpoint['seconds'])
   policy=trainer.learner.policy();s.save_training(identity,checkpoint,policy,checkpoint['steps'],checkpoint['seconds'],curriculum=checkpoint['curriculum'])
   h.game._refresh();assert h.game.selectDriver(identity);assert h.game.start()
   deadline=time.monotonic()+30
   while not h.game.scene.get('cars') and time.monotonic()<deadline:h.pump(10)
   assert len(h.game.scene['cars'])==32,h.game.scene
  else:
   with gzip.open(a.output/'capture-scenes.json.gz','rt') as stream:data=json.load(stream)
   corpus_input=data['scenes'];source_meta=data['source'];h.game._mode='impara';h.game._run_state='running';h.game.changed.emit()
   h.game._scene=corpus_input[0][1];h.game.sceneChanged.emit();h.pump(150)
  print('Source frame arrived; waiting renderer',flush=True)
  h.pump(300)
  deadline=time.monotonic()+20;cars=[]
  while len(cars)!=32 and time.monotonic()<deadline:
   h.pump(20);cars=[x for x in objects(h.window.contentItem()) if x.objectName().startswith('gameCar')]
  assert len(cars)==32,dict(cars=len(cars),content=h.value('activeContentId'),family=h.value('familyId'),messages=h.messages)

  print('Renderer ready '+str(len(cars)),flush=True)
  h.game.sceneChanged.connect(receive_scene);h.window.frameSwapped.connect(rendered);pose_timer=QTimer();pose_timer.setTimerType(Qt.TimerType.PreciseTimer);pose_timer.setInterval(16);pose_timer.timeout.connect(animated)
  worker_pid=h.game._process.pid if h.game._process else None
  started=time.monotonic();pose_timer.start();resource_timer=QTimer();resource_timer.setInterval(2000);resource_timer.timeout.connect(resources);resource_timer.start();resources()
  timer=None
  if a.mode!='capture':
   index=0;last_render=-1.
   def replay():
    global index,last_render
    now=time.monotonic();elapsed=now-started;changed=False
    while index<len(corpus_input) and corpus_input[index][0]<=elapsed:
     scene=corpus_input[index][1]
     if a.mode=='replay8':scene={**scene,'cars':scene['cars'][:8]}
     h.game._scene={**scene,'timestamp':started+corpus_input[index][0]}
     index+=1;changed=True
    if changed:h.game.sceneChanged.emit()
   timer=QTimer();timer.setTimerType(Qt.TimerType.PreciseTimer);timer.setInterval(33 if a.mode=='smooth30' else 4);timer.timeout.connect(replay);timer.start()
  while time.monotonic()-started<a.seconds:h.pump(1)
  elapsed=time.monotonic()-started
  print('Measurement complete '+str(len(frames)),flush=True)
  resource_timer.stop()
  if timer:timer.stop()
  h.window.frameSwapped.disconnect(rendered);pose_timer.stop();h.game.sceneChanged.disconnect(receive_scene)
  intervals=[b-a for a,b in zip(frames,frames[1:])]
  result=dict(status='passed',mode=a.mode,scope='Software submitted frames and item poses; not optical FPS or direct GPU time',seconds=elapsed,window=[h.window.width(),h.window.height()],
   frameTimes=[t-started for t in frames],frames=len(frames),frameHz=len(frames)/elapsed,frameGaps=distribution(intervals),sceneGaps=distribution(scene_gaps),
   motionGaps={k:distribution(v) for k,v in gaps.items()},probeCallbackCost=distribution(callback_cost),resources=sampled,source=source_meta,freshPopulation=a.fresh_population,qmlWarnings=h.messages)
  if a.mode=='capture':
   with gzip.open(a.output/'capture-scenes.json.gz','wt') as stream:json.dump(dict(source=source_meta,scenes=corpus),stream)
   result.update(sourcePackets=len(corpus),steps=h.game.scene['meta'].get('steps'),activeCounts=[sum(not car.get('completed') for car in scene['cars']) for _,scene in corpus])
   assert h.game.pause();deadline=time.monotonic()+30
   while h.game.captured and time.monotonic()<deadline:h.pump(10)
   assert not h.game.captured
  print('Saving screenshot outside timing',flush=True)
  # Screenshots are outside measured windows.
  assert h.window.grabWindow().save(str(a.output/((a.label or a.mode)+'.png')))
  (a.output/((a.label or a.mode)+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('status','mode','frameHz','frameGaps','sceneGaps','qmlWarnings')}))
  assert not h.messages,h.messages
 finally:h.close();private.cleanup()
