"""Actual lap crossings, replay, clean records and isolated configuration scopes."""
import copy,json,tempfile,unittest
import numpy as np
from game_simulation import World,DT
from game_catalog import configuration,RACE_PHYSICS_VERSION,ACADEMY_OBSERVATION_VERSION
from game_control import racing_actions
from game_store import GameStore


class RecordChecks(unittest.TestCase):
 def test_actual_two_lap_crossings_and_snapshot_resume(self):
  w=World(laps=2,physics=RACE_PHYSICS_VERSION,telemetry=True)
  w.reset()
  clone=World(laps=2,physics=RACE_PHYSICS_VERSION,telemetry=True)
  for i in range(16000):
   w.step(racing_actions(w),return_observations=False)
   if i==200:
    clone.restore(json.loads(json.dumps(w.snapshot())))
    clone.step(racing_actions(clone),return_observations=False)
   if i==201:self.assertEqual(w.snapshot(),clone.snapshot())
   if not w.active.any():break
  row=w.rows()[0];self.assertEqual(row['status'],'arrivato');self.assertEqual(len(row['lapTimes']),2)
  self.assertTrue(all(x['clean'] for x in row['lapTimes']))
  self.assertAlmostEqual(sum(x['time'] for x in row['lapTimes']),row['finishTime'],places=8)
  self.assertTrue(row['lapTimes'][0]['standingStart']);self.assertFalse(row['lapTimes'][1]['standingStart'])
  self.assertEqual(row['bestLap'],min(x['time'] for x in row['lapTimes']))
  self.assertGreater(row['maxSpeed'],0)
  self.assertLessEqual(row['finishTime'],w.time);self.assertLess(w.time-row['finishTime'],DT)
  self.assertNotIn('telemetry',World().snapshot())

 def test_contacts_and_limits_invalidate_lap_and_time_uses_gate_fraction(self):
  for track in ('oval-1','technical-1','mallory-oval-1','varano-short-1'):
   for dirty in ('none','contact','limit'):
    with self.subTest(track=track,dirty=dirty):
     w=World(laps=2,track_id=track,physics=RACE_PHYSICS_VERSION,telemetry=True)
     length=w.track.length;phase=length-.03;w.state[0,:3]=w.track.pose(phase)
     w.state[0,3]=5;w.coordinates();w.previous_phase=w.coordinates()[2];w.progress[:]=phase;w.checkpoint[:]=3
     if dirty=='contact':w.lap_contacted[:]=True
     if dirty=='limit':w.track_limits[:]=1
     w.step(np.zeros((1,2)),return_observations=False)
     lap=w.rows()[0]['lapTimes'][0]
     self.assertEqual(lap['clean'],dirty=='none');self.assertGreater(lap['time'],0);self.assertLess(lap['time'],DT)
     self.assertEqual(w.rows()[0]['bestLap'],lap['time'] if dirty=='none' else None)
     self.assertGreater(w.rows()[0]['maxSpeed'],4)

 def test_persistent_records_no_old_estimates_separate_scopes_and_modes(self):
  with tempfile.TemporaryDirectory() as root:
   store=GameStore(root);d=store.drivers()[0];person=dict(id=d['id'],name=d['name'],policy='hash',profile=d['profile'])
   run,payload=store.begin_session('gara',{'participants':[person]})
   row=dict(id=d['id'],finishTime=180,telemetryVersion=1,maxSpeed=20.,lapTimes=[dict(lap=1,time=60.,clean=False,standingStart=True),dict(lap=2,time=59.,clean=True,standingStart=False)])
   payload['results']=[row];store.finish_session(run,'complete',payload)
   summary=store.record_summary(payload['configuration'],'gara');self.assertEqual(summary['bestLap']['value'],59);self.assertEqual(summary['maxSpeed']['value'],20)
   self.assertEqual(len(GameStore(root).records(identity=d['id'])),1)
   self.assertFalse(store.record_summary(configuration('technical-1'),'gara')['bestLap'])
   changed=copy.deepcopy(payload['configuration']);changed['condition']['grip_factor']=.8
   self.assertFalse(store.record_summary(changed,'gara')['maxSpeed'])
   # Older trials have no lap telemetry: don't invent a lap record by dividing total time.
   trial,p=store.begin_session('prova',{'participants':[person]});p['results']=[dict(driver=d['id'],time=180)]
   store.finish_session(trial,'complete',p);self.assertFalse(store.record_summary(p['configuration'],'prova')['bestLap'])
   # Equal or worse repeated completions preserve original provenance.
   payload['results'][0]['maxSpeed']=10;payload['results'][0]['lapTimes'][1]['time']=70
   store.finish_session(run,'complete',payload);self.assertEqual(store.record_summary(payload['configuration'],'gara'),summary)
   # f2 category differs from f1; observation-only changes do not alter physical category.
   f2=configuration('oval-1',ACADEMY_OBSERVATION_VERSION);self.assertFalse(store.record_summary(f2,'gara')['bestLap'])
   f1=copy.deepcopy(payload['configuration']);f1['observation']='test-sensors';self.assertEqual(store.record_summary(f1,'gara'),summary)
   store.reset_driver(d['id']);self.assertEqual(store.record_summary(payload['configuration'],'gara'),summary)


if __name__=='__main__':unittest.main()
