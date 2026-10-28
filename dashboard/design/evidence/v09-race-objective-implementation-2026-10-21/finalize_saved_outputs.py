"""Keep continuations of personal models private; publish metrics and hashes."""
from pathlib import Path
import json,shutil,hashlib

P=Path(__file__).parent
PRIVATE=Path('/tmp/smartpc-racing-implementation-private-20261021/snapshot/continued')
PRIVATE.mkdir(exist_ok=True);PRIVATE.chmod(0o700)


def public(value):
    if isinstance(value,list):return [public(x) for x in value]
    if not isinstance(value,dict):return value
    return {k:public(v) for k,v in value.items() if k not in
        ('weights','actor','critic','q1','q2','target1','target2','target_actor','replay','replayBinary','actorAdam','criticAdam','q1Adam','q2Adam','stdAdam')}


def finalize():
    rows=[]
    for name in ('Crono','Memoria','Linea','Tattico'):
        src=P/'saved-continuations'/(name+'.json');private=PRIVATE/src.name
        if not private.exists():
            if not src.exists():continue
            raw=json.loads(src.read_text())
            if raw.get('modelsPrivate'):continue
            shutil.move(src,private)
        raw=json.loads(private.read_text());clean=public(raw);clean['modelsPrivate']=True
        def key(model):return hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        clean['modelHashes']=dict(champion=key(raw['champion']),candidate=key(raw['candidate']),raceChampion=key(raw['state']['raceChampion']['policy']))
        temporary=src.with_suffix('.public.tmp');temporary.write_text(json.dumps(clean,indent=2)+'\n');temporary.replace(src)
        rows.append(name)
    return rows


if __name__=='__main__':print('Personal models private; public metrics:',finalize())
