"""Transactional driver registry, immutable policies, runs and race provenance."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from game_catalog import configuration, scope_hash, OBSERVATION_VERSION, LEGACY_OBSERVATION_VERSION, TRACKS


def stamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def default_profile(seed=1, algorithm='evolution'):
    from game_profiles import preset
    return preset(seed,algorithm)


def path_profile(profile,track_id):
    result=dict(profile)
    if track_id in ('mallory-oval-1','varano-short-1'):
        result['observation']=OBSERVATION_VERSION
    return result


def validate_profile(profile):
    allowed = set(default_profile())
    if not isinstance(profile, dict) or set(profile)!=allowed:
        raise ValueError('Profilo incompleto o sconosciuto')
    if profile['algorithm'] not in ('evolution', 'ppo', 'neat', 'pure_pursuit', 'imitation', 'ppo_smooth') or profile['observation'] not in (OBSERVATION_VERSION,LEGACY_OBSERVATION_VERSION):
        raise ValueError('Metodo o sensori incompatibili')
    for key, lo, hi in (('version',1,1), ('seed',0,2**31-1), ('population',8,256),
                        ('hidden',8,64), ('episodeSeconds',10,180), ('rollout',64,2048), ('epochs',1,8)):
        if type(profile[key]) is not int or not lo<=profile[key]<=hi:
            raise ValueError('Parametro non valido: '+key)
    for key, lo, hi in (('mutation',0.01,1.0), ('learningRate',1e-5,0.01), ('gamma',0.9,0.9999)):
        if type(profile[key]) not in (int,float) or not lo<=profile[key]<=hi:
            raise ValueError('Parametro non valido: '+key)
    if type(profile['traffic']) is not bool:
        raise ValueError('Curriculum non valido')
    return dict(profile)


class GameStore:
    def __init__(self, root, track_id='oval-1'):
        if track_id not in {t['id'] for t in TRACKS}:raise ValueError('Circuito sconosciuto')
        self.track_id=track_id
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.policies = self.root/'policies'
        self.policies.mkdir(exist_ok=True)
        with self.connect() as db:
            archive_version=db.execute('PRAGMA user_version').fetchone()[0]
            if archive_version>2:
                raise ValueError('Versione archivio gioco non supportata')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS drivers(id TEXT PRIMARY KEY,name TEXT NOT NULL,number INTEGER NOT NULL,
                    profile TEXT NOT NULL,policy TEXT,checkpoint TEXT,steps INTEGER NOT NULL DEFAULT 0,
                    seconds REAL NOT NULL DEFAULT 0,created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,driver TEXT NOT NULL,
                    kind TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,mode TEXT NOT NULL,status TEXT NOT NULL,
                    created TEXT NOT NULL,updated TEXT NOT NULL,payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS history_driver_kind ON history(driver,kind,id);
                CREATE TABLE IF NOT EXISTS driver_paths(id TEXT NOT NULL REFERENCES drivers(id),track_id TEXT NOT NULL,
                    profile TEXT NOT NULL,policy TEXT,checkpoint TEXT,steps INTEGER NOT NULL DEFAULT 0,
                    seconds REAL NOT NULL DEFAULT 0,policy_profile TEXT,candidate TEXT,curriculum TEXT,
                    PRIMARY KEY(id,track_id));
                CREATE TABLE IF NOT EXISTS path_initializers(id TEXT NOT NULL,track_id TEXT NOT NULL,
                    policy TEXT NOT NULL,source TEXT NOT NULL,PRIMARY KEY(id,track_id));
                CREATE TABLE IF NOT EXISTS profile_paths(id TEXT NOT NULL,track_id TEXT NOT NULL,
                    path_key TEXT NOT NULL,state TEXT NOT NULL,PRIMARY KEY(id,track_id,path_key));
            ''')
            if 'track_id' not in {row[1] for row in db.execute('PRAGMA table_info(history)')}:
                db.execute("ALTER TABLE history ADD COLUMN track_id TEXT NOT NULL DEFAULT 'oval-1'")
            if 'policy_profile' not in {row[1] for row in db.execute('PRAGMA table_info(drivers)')}:
                db.execute('ALTER TABLE drivers ADD COLUMN policy_profile TEXT')
                db.execute('UPDATE drivers SET policy_profile=profile WHERE policy IS NOT NULL')
            columns={row[1] for row in db.execute('PRAGMA table_info(drivers)')}
            for column in ('candidate','curriculum'):
                if column not in columns:db.execute('ALTER TABLE drivers ADD COLUMN '+column+' TEXT')
            if db.execute('SELECT count(*) FROM drivers').fetchone()[0]==0:
                self._seed_default_drivers(db)
            # A killed worker cannot silently promote an unfinished session.
            db.execute("UPDATE sessions SET status='interrupted' WHERE status IN ('running','paused')")
            self._ensure_paths(db)
            # Setting even the current version dirties SQLite's header and
            # forces a durable commit on every kiosk start or track change.
            if archive_version!=2:db.execute('PRAGMA user_version=2')

    @property
    def table(self):return 'drivers' if self.track_id=='oval-1' else 'driver_paths'

    def where(self,identity):
        return ('id=?',(identity,)) if self.track_id=='oval-1' else ('id=? AND track_id=?',(identity,self.track_id))

    def _seed_default_drivers(self, db):
        from game_catalog import ACTION_VERSION
        for name, num, algo in (('Evo', 1, 'evolution'), ('Neat', 2, 'neat'), ('PPO', 3, 'ppo'),
                                ('Pursuit', 4, 'pure_pursuit'), ('Clone', 5, 'imitation'), ('PPO-Smooth', 6, 'ppo_smooth')):
            prof = default_profile(num, algo)
            policy_hash = None
            if algo == 'pure_pursuit':
                from game_profiles import reference_policy
                policy_artifact=reference_policy('oval-1')
                policy_hash = self.artifact(policy_artifact)
            self._insert_driver(db, name, num, prof, policy_hash)

    def reset_roster(self):
        with self.connect() as db:
            db.execute('DELETE FROM history')
            db.execute('DELETE FROM sessions')
            db.execute('DELETE FROM profile_paths')
            db.execute('DELETE FROM path_initializers')
            db.execute('DELETE FROM driver_paths')
            db.execute('DELETE FROM drivers')
            self._seed_default_drivers(db)
            self._ensure_paths(db)

    def _ensure_paths(self,db):
        if self.track_id=='oval-1':return
        for row in db.execute('SELECT id,number,profile FROM drivers').fetchall():
            prof = path_profile(json.loads(row['profile']),self.track_id)
            from game_profiles import reference_policy
            policy=self.artifact(reference_policy(self.track_id)) if prof['algorithm']=='pure_pursuit' else None
            db.execute('INSERT OR IGNORE INTO driver_paths(id,track_id,profile,policy,policy_profile) VALUES(?,?,?,?,?)',
                       (row['id'],self.track_id,canonical(prof).decode(),policy,canonical(prof).decode() if policy else None))

    def select_track(self,identity):
        if identity not in {t['id'] for t in TRACKS}:raise ValueError('Circuito sconosciuto')
        self.track_id=identity
        with self.connect() as db:self._ensure_paths(db)

    def total_seconds(self,identity):
        with self.connect() as db:
            active=db.execute('SELECT seconds FROM drivers WHERE id=?',(identity,)).fetchone()[0]
            active+=db.execute('SELECT coalesce(sum(seconds),0) FROM driver_paths WHERE id=?',(identity,)).fetchone()[0]
            resets=[json.loads(r[0])['previous']['seconds'] for r in db.execute("SELECT payload FROM history WHERE driver=? AND kind='reset'",(identity,))]
            archived=sum(json.loads(r[0])['seconds'] for r in db.execute('SELECT state FROM profile_paths WHERE id=?',(identity,)))
        return active+archived+sum(resets)

    def initialize_from(self,identity,source):
        if source==self.track_id:raise ValueError('Il circuito di origine è già selezionato')
        with self.connect() as db:
            row=db.execute('SELECT policy,policy_profile FROM drivers WHERE id=?',(identity,)).fetchone() if source=='oval-1' else db.execute('SELECT policy,policy_profile FROM driver_paths WHERE id=? AND track_id=?',(identity,source)).fetchone()
            current=self.driver(identity)
            if not row or not row['policy']:raise ValueError('Nessun modello nel circuito di origine')
            policy=self.load(row['policy'])
            if policy['kind']!='dense' or policy.get('hidden')!=current['profile']['hidden'] or policy.get('algorithm')!=current['profile']['algorithm'] or policy.get('observation')!=current['profile']['observation']:
                raise ValueError('Trasferimento richiede lo stesso metodo e la stessa rete densa')
            if current['checkpoint'] or current['policy'] or current['steps']:raise ValueError('Il percorso contiene già apprendimento')
            db.execute('INSERT OR REPLACE INTO path_initializers VALUES(?,?,?,?)',(identity,self.track_id,row['policy'],source))
            self._event(db,identity,'transfer',{'source':source,'policy':row['policy']})

    def initializer(self,identity):
        with self.connect() as db:row=db.execute('SELECT policy FROM path_initializers WHERE id=? AND track_id=?',(identity,self.track_id)).fetchone()
        return self.load(row[0]) if row else None

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root/'game.sqlite', timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _insert_driver(self, db, name, number, profile=None, policy=None):
        identity = uuid.uuid4().hex
        prof = profile or default_profile(number)
        prof_json = canonical(prof).decode()
        db.execute('INSERT INTO drivers(id,name,number,profile,policy,policy_profile,created) VALUES(?,?,?,?,?,?,?)',
                   (identity, name, number, prof_json, policy, prof_json if policy else None, stamp()))
        return identity

    def create_driver(self, name='', algorithm='evolution'):
        with self.connect() as db:
            number = db.execute('SELECT coalesce(max(number),0)+1 FROM drivers').fetchone()[0]
            prof=default_profile(number,algorithm)
            from game_profiles import reference_policy
            policy=self.artifact(reference_policy('oval-1')) if algorithm=='pure_pursuit' else None
            identity=self._insert_driver(db, (name.strip() or f'Pilota {number}')[:40], number,prof,policy)
            self._ensure_paths(db)
            return identity

    def drivers(self,track_id=None):
        track_id=track_id or self.track_id
        with self.connect() as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM drivers ORDER BY number')]
            if track_id!='oval-1':
                paths={r['id']:dict(r) for r in db.execute('SELECT * FROM driver_paths WHERE track_id=?',(track_id,))}
                rows=[{**r,**{k:v for k,v in paths.get(r['id'],{'profile':canonical(path_profile(json.loads(r['profile']),track_id)).decode(),
                      'policy':None,'checkpoint':None,'steps':0,'seconds':0,'policy_profile':None,'candidate':None,'curriculum':None}).items() if k!='track_id'}} for r in rows]
        for row in rows:
            row['profile'] = json.loads(row['profile'])
            row['policy_profile'] = json.loads(row['policy_profile']) if row['policy_profile'] else None
            row['trained'] = bool(row['policy'])
            row['curriculum'] = json.loads(row['curriculum']) if row['curriculum'] else None
        return rows

    def driver(self, identity,track_id=None):
        return next((x for x in self.drivers(track_id) if x['id']==identity), None)

    def path_key(self,profile):
        return hashlib.sha256(canonical({k:profile[k] for k in ('algorithm','hidden','observation','population','traffic','seed')})).hexdigest()

    def set_profile(self, identity, profile, *, allow_reconfigure=False):
        validate_profile(profile)
        with self.connect() as db:
            where,args=self.where(identity)
            previous = db.execute('SELECT profile FROM '+self.table+' WHERE '+where,args).fetchone()
            if previous is None:
                raise ValueError('Pilota sconosciuto')
            old = json.loads(previous[0])
            if old!=profile and not allow_reconfigure:
                raise ValueError('Profilo fisso: crea un nuovo pilota per scegliere altri parametri')
            incompatible = any(old[k]!=profile[k] for k in ('algorithm','hidden','observation','population','traffic','seed'))
            if old==profile:return
            if incompatible:
                state=dict(db.execute('SELECT * FROM '+self.table+' WHERE '+where,args).fetchone())
                saved={k:state[k] for k in ('profile','policy','checkpoint','candidate','curriculum','policy_profile','steps','seconds')}
                db.execute('INSERT OR REPLACE INTO profile_paths VALUES(?,?,?,?)',
                           (identity,self.track_id,self.path_key(old),canonical(saved).decode()))
                resumed=db.execute('SELECT state FROM profile_paths WHERE id=? AND track_id=? AND path_key=?',
                                   (identity,self.track_id,self.path_key(profile))).fetchone()
                restored=json.loads(resumed[0]) if resumed else {**saved,'checkpoint':None,'candidate':None,'curriculum':None,'steps':0,'seconds':0}
                fields=('policy','checkpoint','candidate','curriculum','policy_profile','steps','seconds')
                db.execute('UPDATE '+self.table+' SET '+','.join(k+'=?' for k in fields)+' WHERE '+where,
                           (*[restored[k] for k in fields],*args))
                db.execute('DELETE FROM profile_paths WHERE id=? AND track_id=? AND path_key=?',
                           (identity,self.track_id,self.path_key(profile)))
            db.execute('UPDATE '+self.table+' SET profile=?,checkpoint=CASE WHEN ? THEN NULL ELSE checkpoint END WHERE '+where,
                       (canonical(profile).decode(),False,*args))
            if incompatible:
                db.execute('DELETE FROM path_initializers WHERE id=? AND track_id=?',(identity,self.track_id))
            self._event(db, identity, 'profile', {'previous':old, 'next':profile, 'newPath':incompatible})

    def _event(self, db, driver, kind, payload):
        db.execute('INSERT INTO history(driver,kind,created,payload,track_id) VALUES(?,?,?,?,?)',
                   (driver,kind,stamp(),canonical(payload).decode(),self.track_id))

    def artifact(self, value):
        data = canonical(value)
        if len(data)>512*1024*1024:
            raise ValueError('Checkpoint oltre il limite di persistenza di 512 MiB')
        digest = hashlib.sha256(data).hexdigest()
        target = self.policies/(digest+'.json')
        if not target.exists():
            temporary = target.with_suffix('.tmp-'+uuid.uuid4().hex)
            try:
                with temporary.open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
                directory = os.open(self.policies, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                temporary.unlink(missing_ok=True)
        return digest

    def load(self, digest):
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Hash non valido')
        target = self.policies/(digest+'.json')
        if target.stat().st_size>512*1024*1024:
            raise ValueError('Artefatto troppo grande')
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:
            raise ValueError('Artefatto danneggiato')
        return json.loads(data)

    def save_training(self, identity, checkpoint, policy, steps, seconds, metric=None, curriculum=None,
                      session=None, session_stats=None):
        checkpoint_hash, policy_hash = self.artifact(checkpoint), self.artifact(policy)
        champion_hash=self.artifact(curriculum['champion']['policy']) if curriculum and curriculum['champion'] else None
        with self.connect() as db:
            if db.execute('SELECT id FROM drivers WHERE id=?',(identity,)).fetchone() is None:
                raise ValueError('Pilota sconosciuto')
            where,args=self.where(identity)
            if curriculum is None:
                # Compatibility for old callers/imported training fixtures.
                db.execute('UPDATE '+self.table+' SET policy=?,checkpoint=?,steps=?,seconds=?,policy_profile=profile WHERE '+where,
                           (policy_hash,checkpoint_hash,steps,seconds,*args))
            else:
                public_state={**curriculum,'pending':None}
                db.execute('UPDATE '+self.table+' SET candidate=?,checkpoint=?,steps=?,seconds=?,curriculum=? WHERE '+where,
                           (policy_hash,checkpoint_hash,steps,seconds,canonical(public_state).decode(),*args))
                if champion_hash:
                    champion_profile=curriculum['champion'].get('profile')
                    if champion_profile:
                        db.execute('UPDATE '+self.table+' SET policy=?,policy_profile=? WHERE '+where,(champion_hash,canonical(champion_profile).decode(),*args))
                    else:db.execute('UPDATE '+self.table+' SET policy=?,policy_profile=profile WHERE '+where,(champion_hash,*args))
            self._event(db,identity,'checkpoint',{'policy':policy_hash,'checkpoint':checkpoint_hash,
                                                'steps':steps,'seconds':seconds,'metric':metric})
            if session:
                row=db.execute('SELECT payload,mode FROM sessions WHERE id=?',(session,)).fetchone()
                if row is None or row['mode']!='impara' or json.loads(row['payload']).get('driver')!=identity:
                    raise ValueError('Sessione di un altro pilota')
                data={**json.loads(row[0]),'training':session_stats}
                if checkpoint.get('task'):data['task']=checkpoint['task']
                db.execute('UPDATE sessions SET payload=?,updated=? WHERE id=?',
                           (canonical(data).decode(),stamp(),session))
            if curriculum and curriculum['evaluations']:
                proof=curriculum['evaluations'][-1]
                last=db.execute("SELECT payload FROM history WHERE driver=? AND track_id=? AND kind='evaluation' ORDER BY id DESC LIMIT 1",(identity,self.track_id)).fetchone()
                if not last or json.loads(last[0])!=proof:self._event(db,identity,'evaluation',proof)
        return policy_hash

    def reset_driver(self, identity):
        """Clear the active learner atomically; preserve identity and provenance."""
        with self.connect() as db:
            where,args=self.where(identity)
            row=db.execute('SELECT * FROM '+self.table+' WHERE '+where,args).fetchone()
            if row is None:raise ValueError('Pilota sconosciuto')
            self._event(db,identity,'reset',{'previous':dict(row)})
            db.execute('UPDATE '+self.table+' SET policy=NULL,policy_profile=NULL,checkpoint=NULL,candidate=NULL,'
                       'curriculum=NULL,steps=0,seconds=0 WHERE '+where,args)
            db.execute('DELETE FROM path_initializers WHERE id=? AND track_id=?',(identity,self.track_id))
            prof=json.loads(row['profile'])
            if prof['algorithm']=='pure_pursuit':
                from game_profiles import reference_policy
                policy=self.artifact(reference_policy(self.track_id))
                db.execute('UPDATE '+self.table+' SET policy=?,policy_profile=? WHERE '+where,(policy,row['profile'],*args))

    def driver_events(self, identity, all_tracks=False):
        with self.connect() as db:
            return [{**dict(row),'payload':json.loads(row['payload'])} for row in db.execute(
                "SELECT * FROM history WHERE driver=? AND (? OR track_id=?) AND kind IN ('profile','reset','evaluation','transfer') ORDER BY id DESC",(identity,all_tracks,self.track_id))]

    def begin_session(self, mode, payload):
        identity = uuid.uuid4().hex
        observation=payload.get('profile',{}).get('observation')
        if observation is None:
            from game_catalog import OBSERVATION_VERSION
            observation=OBSERVATION_VERSION
        payload = {**payload,'configuration':configuration(self.track_id,observation),'scope':scope_hash(self.track_id,observation)}
        now = stamp()
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',
                       (identity,mode,'running',now,now,canonical(payload).decode()))
        return identity, payload

    def finish_session(self, identity, status, payload):
        if status not in ('running','paused','complete','interrupted','failed'):
            raise ValueError('Stato non valido')
        with self.connect() as db:
            db.execute('UPDATE sessions SET status=?,updated=?,payload=? WHERE id=?',
                       (status,stamp(),canonical(payload).decode(),identity))

    def sessions(self, mode=None, complete=True):
        with self.connect() as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM sessions ORDER BY created DESC')]
        for row in rows:
            row['payload'] = json.loads(row['payload'])
        return [row for row in rows if (not mode or row['mode']==mode) and (not complete or row['status']=='complete')]

    def history(self, identity):
        with self.connect() as db:
            return [{**dict(row),'payload':json.loads(row['payload'])} for row in
                    db.execute('SELECT * FROM history WHERE driver=? AND track_id=? ORDER BY id DESC LIMIT 100',(identity,self.track_id))]
