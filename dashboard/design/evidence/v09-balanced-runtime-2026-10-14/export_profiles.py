"""Production artifacts read-only, for isolated qualification only."""
from pathlib import Path
import hashlib,json,sqlite3
root=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game')
with sqlite3.connect('file:'+str(root/'game.sqlite')+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    rows=[]
    for record in db.execute('SELECT * FROM drivers ORDER BY number'):
        row=dict(record);profile=json.loads(row['profile'])
        if profile['algorithm']=='pure_pursuit':continue
        key=row['checkpoint']
        if profile['algorithm']=='evolution':
            local=db.execute("SELECT state FROM objective_paths WHERE driver=? AND objective='impara_infinito' ORDER BY track LIMIT 1",(row['id'],)).fetchone()
            if local:key=json.loads(local[0]).get('checkpoint') or key
        checkpoint=json.loads((root/'policies'/(key+'.json')).read_text()) if key else None
        rows.append(dict(name=row['name'],id=row['id'],profile=profile,checkpoint=checkpoint,sourceHash=key))
    sessions=[dict(r) for r in db.execute('SELECT id,mode,status,created FROM sessions ORDER BY created DESC LIMIT 2')]
print(json.dumps(dict(scope='Read-only original artifacts, copies only',profiles=rows,sessions=sessions)))
