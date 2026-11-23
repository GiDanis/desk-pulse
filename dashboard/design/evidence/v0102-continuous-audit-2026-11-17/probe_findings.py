"""Isolated fault probes of the verified installed source copy; no board writes."""
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parent/'v0102-apple-calm-implementation-2026-10-30/runtime'
sys.path.insert(0,str(RUNTIME))
from aquarium_store import AquariumStore
from aquarium_catalog import load_3d_catalog

now=[1794945600.0]
catalog=load_3d_catalog()
db=AquariumStore(':memory:',catalog,clock=lambda:now[0])
db.reconcile()
changes=[]
for i in range(3):
    now[0]+=60
    before=db.db.total_changes
    db.reconcile()
    changes.append(db.db.total_changes-before)
result={'source':str(RUNTIME),'aquarium_idle_reconcile':{'refreshes':3,
        'rows_changed_per_refresh':changes,'active_fish':len(db.active()),
        'pending_count':db.db.execute('SELECT COUNT(*) FROM pending').fetchone()[0],
        'all_deadlines_null':all(f['due'] is None for f in db.active())}}
with db.db: db.reserve(0,'angel')
pending_snapshot=db.snapshot()
db.close()

from PySide6.QtCore import QCoreApplication
from aquarium_population import AquariumPopulation
app=QCoreApplication([])
class FailOnce:
    calls=0
    def prepared(self,_):
        self.calls+=1
        raise sqlite3.OperationalError('controlled database is locked')
    def close(self): pass
p=AquariumPopulation()
p.store=FailOnce()
p.catalog=catalog
p.state=pending_snapshot
accepted=p.submit('prepared',pending_snapshot['pending'][0]['operationId'])
until=time.monotonic()+2
while p.busy and time.monotonic()<until:
    app.processEvents();time.sleep(.001)
scene=p.scene('running','test-session')
# QML sets candidateSent to this enqueue acknowledgement and only retries while false.
result['aquarium_async_failure']={'enqueue_accepted':accepted,'worker_calls':p.store.calls,
    'worker_error':p.error,'candidate_still_pending':bool(p.state['pending']),
    'scene_status_after_failure':scene['status'],
    'qml_candidate_sent_after_enqueue':accepted}
p.close()
(HERE/'fault-probes.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
