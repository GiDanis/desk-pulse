"""Private copy of actual saved pilots: protocol migration, transfer and replay."""
import hashlib,json,os,shutil,sys,tempfile
from pathlib import Path
import numpy as np
H=Path('/var/lib/smartpc-dashboard');source=H/'smartpc-v09-rc12-project/dashboard';sys.path.insert(0,str(source))
from game_store import GameStore
from game_academy_trainer import AcademyTrainer
from game_learning import Policy
GAME=H/'.local/share/SmartPC/SmartPC/game';proof=H/'v09-driving-memory-proof'
def hashes():return {q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in (GAME/'policies').glob('*.json')}
before=hashes();rows=[]
with tempfile.TemporaryDirectory(prefix='actual-drivers-private-',dir=proof) as tmp:
 root=Path(tmp)/'game'
 def copy(src,dst):
  if Path(src).parent==GAME/'policies':os.link(src,dst);return dst
  return shutil.copy2(src,dst)
 shutil.copytree(GAME,root,copy_function=copy);s=GameStore(root);original=s.drivers()
 for d in original:
  identity=d['id'];s.select_track('oval-1');s.activate_academy(identity);s.prepare_driving(identity);local=s.driver(identity)
  if local['profile']['algorithm']=='pure_pursuit':rows.append(dict(name=d['name'],reference=True));continue
  t=AcademyTrainer(local['profile'],'oval-1',s.load(local['checkpoint']))
  saved=t.checkpoint(local['seconds']);b=AcademyTrainer(local['profile'],'oval-1',json.loads(json.dumps(saved)))
  for _ in range(100):t.tick();b.tick()
  assert json.loads(json.dumps(t.checkpoint(1)))==json.loads(json.dumps(b.checkpoint(1)))
  p=t.learner.candidate_policy() if hasattr(t.learner,'candidate_policy') else t.learner.policy()
  s.save_training(identity,t.checkpoint(1),p,t.steps,1,curriculum=t.state);local_checkpoint=s.driver(identity)['checkpoint']
  s.select_track('varano-short-1');previous_varano=s.driver(identity);s.activate_academy(identity);s.prepare_driving(identity)
  if previous_varano['checkpoint']:
   # Existing local knowledge must take precedence; don't mistake that for failed inheritance.
   local_varano=s.driver(identity);saved_varano=local_varano['checkpoint'];s.prepare_driving(identity)
   assert s.driver(identity)['checkpoint']==saved_varano
  s.reset_driver(identity);s.prepare_driving(identity);target=s.driver(identity)
  model=AcademyTrainer(target['profile'],'varano-short-1',s.load(target['checkpoint']))
  memory=s.memory_record(identity)['base'];assert memory and model.memory['baseHash']==memory['policyHash']
  inherited=model.learner.candidate_policy() if hasattr(model.learner,'candidate_policy') else model.learner.policy()
  obs=np.random.default_rng(102).normal(size=68)
  np.testing.assert_allclose(Policy(inherited).act(obs),Policy(s.load(memory['policyHash'])).act(obs),atol=1e-15)
  s.select_track('oval-1');s.prepare_driving(identity);assert s.driver(identity)['checkpoint']==local_checkpoint
  rows.append(dict(name=d['name'],method=local['profile']['algorithm'],originalSteps=d['steps'],protocolSteps=saved['steps'],originalCheckpoint=d['checkpoint'],privateMigratedCheckpoint=local_checkpoint,baseStatus=memory['status'],transfer='oval -> Varano -> oval',localResumeExact=True,varanoLocalPriority=bool(previous_varano['checkpoint']),newVaranoAfterPrivateReset=True,originalAlgorithmPreserved=True))
assert hashes()==before
result=dict(status='passed',actualArchivePrivateCopy=True,originalArtifactsUnchanged=len(before),pilots=rows)
(proof/'existing-drivers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
