"""Diagnose rc.27 on a temporary store; never starts a worker or touches production."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib,json
from PySide6.QtCore import QCoreApplication
from game_store import GameStore,canonical,validate_profile
from game_racing_presets import PROFILE_KEYS
from game import GameService

P=Path(__file__).parent;source=Path(__import__('game_store').__file__).parent
snapshot=json.loads((P/'board-state.json').read_text());app=QCoreApplication([])
rows=[]
for driver in snapshot['drivers']:
    profile=driver['profile']
    try:validate_profile(profile);error=None
    except ValueError as exc:error=str(exc)
    legacy={k:v for k,v in profile.items() if k not in PROFILE_KEYS}
    validate_profile(legacy)
    rows.append(dict(name=driver['name'],method=profile['algorithm'],error=error,
        newRecipeKeys=sorted(set(profile)&set(PROFILE_KEYS)),legacySchemaControlPassed=True))

with TemporaryDirectory(prefix='smartpc-menu-study-') as root:
    store=GameStore(root)
    with store.connect() as db:
        for d in snapshot['drivers']:
            db.execute('UPDATE drivers SET profile=? WHERE name=?',(canonical(d['profile']).decode(),d['name']))
    service=GameService(root);settings=service._settings;drivers={d['name']:d['id'] for d in service._store.drivers()}
    paths=[]
    try:
        for name in ('Crono','Memoria','Linea','Tattico'):
            for change_mode in (False,True):
                service._selected=drivers['Crono'];service._mode='impara';service._refresh();settings.open(True)
                assert settings.action('driver') and settings.action('pick:'+drivers[name])
                if change_mode:settings.draft['mode']='impara_infinito'
                dirty=settings.dirty
                before=[d['profile'] for d in service._store.drivers()]
                applied=settings.apply('apply')
                after=[d['profile'] for d in service._store.drivers()]
                assert before==after
                paths.append(dict(name=name,changeMode=change_mode,dirty=dirty,applied=applied,
                    message=service._message,settingsMessage=settings.message,profilesUnchanged=True,
                    workerCreated=service._process is not None))
        assert paths[0]['applied'] and not paths[0]['dirty']
        assert all(not r['applied'] for r in paths[1:])
        assert all(not r['workerCreated'] for r in paths)
    finally:service.close()

hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in snapshot['sourceHashes']}
assert hashes==snapshot['sourceHashes'],'Source differs from installed rc.27'
out=dict(status='reproduced',scope='Real GameSettings -> GameService.applySetup, temporary store, no worker, no production writes',
    sourceHashes=hashes,profiles=rows,paths=paths,
    explanation='Unchanged selected Crono bypasses applySetup when dirty is false; selection or mode changes validate and reject new recipe fields.')
(P/'menu-reproduction.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
