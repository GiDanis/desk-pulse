"""Dedicated transactional fish archive. All production access belongs to one worker."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
import uuid
from aquarium_rotation import DAY, deadline, choose_species

CAPACITY = 6


class AquariumStore:
    def __init__(self,path,catalog,clock=time.time):
        self.catalog={s['id']:s for s in catalog['species']};self.clock=clock
        if str(path)!=':memory:':Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(path),timeout=3);self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fish(id TEXT PRIMARY KEY,species TEXT NOT NULL,variant TEXT NOT NULL,name TEXT NOT NULL,seed INTEGER NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS slots(id INTEGER PRIMARY KEY,days INTEGER NOT NULL DEFAULT 0,next_species TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS visits(id TEXT PRIMARY KEY,fish TEXT NOT NULL REFERENCES fish(id),slot INTEGER NOT NULL REFERENCES slots(id),started REAL NOT NULL,due REAL,ended REAL,shown REAL,reason TEXT NOT NULL,label TEXT NOT NULL,asset TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS active_slot ON visits(slot) WHERE ended IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS active_fish ON visits(fish) WHERE ended IS NULL;
        CREATE TABLE IF NOT EXISTS pending(id TEXT PRIMARY KEY,slot INTEGER UNIQUE NOT NULL REFERENCES slots(id),fish TEXT NOT NULL REFERENCES fish(id),expected TEXT NOT NULL,revision INTEGER NOT NULL,reason TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY);
        ''')
        with self.db:
            version=self.meta('schema',None)
            if version is not None and version!=1:raise ValueError('Archivio Acquario più recente del runtime')
            if version is None:
                self.set_meta('schema',1);self.set_meta('revision',1);self.set_meta('pool',list(self.catalog));self.set_meta('lastTime',0)
                initial=['teal','teal','gold','gold','angel','clown']
                available=list(self.catalog)
                for i,species in enumerate(initial):
                    self.db.execute('INSERT INTO slots(id) VALUES(?)',(i,))
                    s=species if species in self.catalog else available[i%len(available)]
                    fish=self.new_fish(s);self.enter(i,fish,'initial')
            self.db.execute('DELETE FROM requests WHERE rowid < (SELECT COALESCE(MAX(rowid),0)-512 FROM requests)')

    def meta(self,key,default=None):
        r=self.db.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone()
        return json.loads(r[0]) if r else default

    def set_meta(self,key,value):
        self.db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',(key,json.dumps(value,ensure_ascii=False,allow_nan=False)))

    def new_fish(self,species):
        if species not in self.catalog:raise ValueError('Tipo non disponibile')
        identity=uuid.uuid4().hex;row=self.catalog[species]
        self.db.execute('INSERT INTO fish VALUES(?,?,?,?,?,?)',(identity,species,row['variants'][0]['id'],row['name'],int(identity[:7],16),self.clock()))
        return identity

    def enter(self,slot,fish,reason):
        now=self.clock();days=self.db.execute('SELECT days FROM slots WHERE id=?',(slot,)).fetchone()[0]
        row=dict(self.db.execute('SELECT * FROM fish WHERE id=?',(fish,)).fetchone());s=self.catalog[row['species']]
        self.db.execute('INSERT INTO visits VALUES(?,?,?,?,?,?,NULL,?,?,?)',(uuid.uuid4().hex,fish,slot,now,deadline(now,days),None,reason,json.dumps({'name':row['name'],'speciesName':s['name'],'variant':row['variant'],'speciesProfile':s},ensure_ascii=False),s['assetUrl']))

    @contextmanager
    def transaction(self,request_id='',expected_revision=None):
        with self.db:
            if request_id:
                if self.db.execute('SELECT 1 FROM requests WHERE id=?',(request_id,)).fetchone():
                    yield False;return
                self.db.execute('INSERT INTO requests VALUES(?)',(request_id,))
            if expected_revision is not None and expected_revision!=self.meta('revision'):raise ValueError('Dati cambiati: riapri la scheda')
            yield True
            self.set_meta('revision',self.meta('revision')+1)

    def active(self):
        return [dict(r) for r in self.db.execute('SELECT v.id visitId,v.slot slotId,v.started,v.due,v.shown,v.label savedLabel,f.*,s.days,s.next_species FROM visits v JOIN fish f ON f.id=v.fish JOIN slots s ON s.id=v.slot WHERE v.ended IS NULL ORDER BY v.slot')]

    def reserve(self,slot,species='',fish_id='',reason='manual'):
        if self.db.execute('SELECT 1 FROM pending WHERE slot=?',(slot,)).fetchone():raise ValueError('Sostituzione già in preparazione')
        active={r['slotId']:r for r in self.active()}
        if slot not in active and len(active)>=CAPACITY:raise ValueError('Profilo pieno: sostituisci o rimuovi un pesce')
        if fish_id:
            r=self.db.execute('SELECT * FROM fish WHERE id=?',(fish_id,)).fetchone()
            if r is None or r['species'] not in self.catalog:raise ValueError('Pesce non disponibile')
            if any(a['id']==fish_id for a in active.values()):raise ValueError('Questo pesce è già presente')
        else:fish_id=self.new_fish(species)
        self.db.execute('INSERT INTO pending VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,slot,fish_id,active.get(slot,{}).get('visitId',''),self.meta('revision')+1,reason))

    def command(self,action,target,args,request_id='',revision=None):
        with self.transaction(request_id,revision) as apply:
            if not apply:return
            active={r['id']:r for r in self.active()}
            row=active.get(target)
            if action=='add':
                used={r['slotId'] for r in active.values()}|{r[0] for r in self.db.execute('SELECT slot FROM pending')}
                slot=next((i for i in range(CAPACITY) if i not in used),None)
                if slot is None:raise ValueError('Profilo pieno: sostituisci o rimuovi un pesce')
                self.reserve(slot,args['species'],args.get('fishId',''))
            elif action=='pool':
                pool=self.meta('pool');species=target
                if species not in self.catalog:raise ValueError('Tipo non disponibile')
                if species in pool:pool.remove(species)
                else:pool.append(species)
                self.set_meta('pool',pool)
                self.db.execute('DELETE FROM pending WHERE reason="calendar"')
            elif action in ('remove','replace','save'):
                if row is None:raise ValueError('Pesce non più presente')
                if action=='remove':
                    self.db.execute('DELETE FROM pending WHERE slot=?',(row['slotId'],));self.db.execute('UPDATE visits SET ended=?,reason=? WHERE id=?',(self.clock(),'removed',row['visitId']))
                elif action=='replace':self.reserve(row['slotId'],args.get('species',row['species']),args.get('fishId',''))
                else:
                    name=args['name'].strip();variant=args['variant'];days=args['days'];successor=args.get('nextSpecies','')
                    if not 1<=len(name)<=32 or any(ord(c)<32 for c in name):raise ValueError('Nome non valido')
                    if variant not in [v['id'] for v in (json.loads(row['savedLabel']).get('speciesProfile') or self.catalog.get(row['species'],{})).get('variants',[])]:raise ValueError('Variante non valida')
                    due=deadline(row['started'],days)
                    if successor and successor not in self.catalog:raise ValueError('Successore non disponibile')
                    self.db.execute('UPDATE fish SET name=?,variant=? WHERE id=?',(name,variant,target))
                    self.db.execute('UPDATE slots SET days=?,next_species=? WHERE id=?',(days,successor,row['slotId']))
                    self.db.execute('UPDATE visits SET due=? WHERE id=?',(due,row['visitId']))
                    self.db.execute('DELETE FROM pending WHERE slot=?',(row['slotId'],))
            else:raise ValueError('Comando Acquario non valido')

    def reconcile(self):
        now=self.clock();last=self.meta('lastTime',0)
        if now<1577836800 or now<last-120:return False
        with self.db:
            self.set_meta('lastTime',max(now,last));pool=self.meta('pool',[])
            current=self.active();counts={s:sum(r['species']==s for r in current) for s in self.catalog}
            for r in self.db.execute('SELECT f.species FROM pending p JOIN fish f ON f.id=p.fish'):counts[r[0]]=counts.get(r[0],0)+1
            for row in current:
                if row['due'] is None or row['due']>now or self.db.execute('SELECT 1 FROM pending WHERE slot=?',(row['slotId'],)).fetchone():continue
                recent=[r[0] for r in self.db.execute('SELECT f.species FROM visits v JOIN fish f ON f.id=v.fish WHERE v.slot=? AND v.ended>?',(row['slotId'],now-7*DAY))]
                species=choose_species(self.catalog,pool,counts,recent,row['seed']+self.meta('revision'),previous=row['species'],next_species=row['next_species'])
                if species:
                    self.reserve(row['slotId'],species,reason='calendar');counts[species]=counts.get(species,0)+1;self.set_meta('revision',self.meta('revision')+1)
        return True

    def prepared(self,operation):
        if self.clock()<max(1577836800,self.meta('lastTime',0)-120):return
        with self.db:
            p=self.db.execute('SELECT * FROM pending WHERE id=?',(operation,)).fetchone()
            if p is None:return
            current=self.db.execute('SELECT id FROM visits WHERE slot=? AND ended IS NULL',(p['slot'],)).fetchone()
            if (current[0] if current else '')!=p['expected']:
                self.db.execute('DELETE FROM pending WHERE id=?',(operation,));return
            if current:self.db.execute('UPDATE visits SET ended=?,reason=? WHERE id=?',(self.clock(),p['reason'],current[0]))
            self.enter(p['slot'],p['fish'],p['reason']);self.db.execute('DELETE FROM pending WHERE id=?',(operation,));self.set_meta('revision',self.meta('revision')+1)

    def shown(self,visit):
        with self.db:self.db.execute('UPDATE visits SET shown=COALESCE(shown,?) WHERE id=? AND ended IS NULL',(self.clock(),visit))

    def snapshot(self,history_offset=0):
        pending=[]
        for r in self.db.execute('SELECT p.id operationId,p.slot slotId,p.reason,f.* FROM pending p JOIN fish f ON f.id=p.fish ORDER BY p.rowid LIMIT 1'):pending.append(dict(r))
        history=[]
        for r in self.db.execute('SELECT * FROM visits ORDER BY started DESC,rowid DESC LIMIT 100 OFFSET ?',(history_offset,)):
            row=dict(r);row['label']=json.loads(row['label']);history.append(row)
        return dict(revision=self.meta('revision'),active=self.active(),pending=pending,pool=self.meta('pool'),history=history,historyOffset=history_offset,historyCount=self.db.execute('SELECT COUNT(*) FROM visits').fetchone()[0],clockHealthy=self.clock()>=max(1577836800,self.meta('lastTime')-120))

    def close(self):self.db.close()
