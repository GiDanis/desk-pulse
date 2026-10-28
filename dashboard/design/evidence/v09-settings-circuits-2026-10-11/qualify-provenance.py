import hashlib,json,sys,tempfile,sqlite3
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from game_store import GameStore
from game_curriculum import Evaluation
from game_catalog import scope_hash
root=Path(sys.argv[2]);evidence=Path(sys.argv[3]);report={}
with tempfile.TemporaryDirectory() as temp:
 import shutil
 shutil.copytree(root,Path(temp)/'game');copy=Path(temp)/'game'
 db=sqlite3.connect(copy/'game.sqlite');db.row_factory=sqlite3.Row
 before=[dict(r) for r in db.execute('SELECT * FROM drivers ORDER BY number')];db.close()
 artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (copy/'policies').glob('*.json')}
 store=GameStore(copy);store.select_track('technical-1');store.select_track('oval-1')
 db=sqlite3.connect(copy/'game.sqlite');db.row_factory=sqlite3.Row
 after=[dict(r) for r in db.execute('SELECT * FROM drivers ORDER BY number')];db.close()
 assert before==after
 assert artifacts=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (copy/'policies').glob('*.json')}
 report['migration']={'allDriverColumnsPreserved':True,'allArtifactHashesPreserved':True,'drivers':len(before),'artifacts':len(artifacts)}
report['status']='passed';print(json.dumps(report,indent=2))
