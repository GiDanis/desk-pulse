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

from game_catalog import configuration, scope_hash, OBSERVATION_VERSION


def stamp():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def default_profile(seed=1):
    return {'version':1, 'algorithm':'evolution', 'seed':seed, 'population':32,
            'hidden':16, 'mutation':0.15, 'episodeSeconds':60, 'traffic':False,
            'learningRate':0.0003, 'rollout':256, 'epochs':4, 'gamma':0.995,
            'observation':OBSERVATION_VERSION}


def validate_profile(profile):
    allowed = set(default_profile())
    if not isinstance(profile, dict) or set(profile)!=allowed:
        raise ValueError('Profilo incompleto o sconosciuto')
    if profile['algorithm'] not in ('evolution', 'ppo', 'neat') or profile['observation']!=OBSERVATION_VERSION:
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
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.policies = self.root/'policies'
        self.policies.mkdir(exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS drivers(id TEXT PRIMARY KEY,name TEXT NOT NULL,number INTEGER NOT NULL,
                    profile TEXT NOT NULL,policy TEXT,checkpoint TEXT,steps INTEGER NOT NULL DEFAULT 0,
                    seconds REAL NOT NULL DEFAULT 0,created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,driver TEXT NOT NULL,
                    kind TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,mode TEXT NOT NULL,status TEXT NOT NULL,
                    created TEXT NOT NULL,updated TEXT NOT NULL,payload TEXT NOT NULL);
            ''')
            if 'policy_profile' not in {row[1] for row in db.execute('PRAGMA table_info(drivers)')}:
                db.execute('ALTER TABLE drivers ADD COLUMN policy_profile TEXT')
                db.execute('UPDATE drivers SET policy_profile=profile WHERE policy IS NOT NULL')
            columns={row[1] for row in db.execute('PRAGMA table_info(drivers)')}
            for column in ('candidate','curriculum'):
                if column not in columns:db.execute('ALTER TABLE drivers ADD COLUMN '+column+' TEXT')
            if db.execute('SELECT count(*) FROM drivers').fetchone()[0]==0:
                for i in range(4):
                    self._insert_driver(db, 'Pilota '+str(i+1), i+1)
            # A killed worker cannot silently promote an unfinished session.
            db.execute("UPDATE sessions SET status='interrupted' WHERE status IN ('running','paused')")

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

    def _insert_driver(self, db, name, number):
        identity = uuid.uuid4().hex
        db.execute('INSERT INTO drivers(id,name,number,profile,created) VALUES(?,?,?,?,?)',
                   (identity, name, number, canonical(default_profile(number)).decode(), stamp()))
        return identity

    def create_driver(self, name=''):
        with self.connect() as db:
            number = db.execute('SELECT coalesce(max(number),0)+1 FROM drivers').fetchone()[0]
            return self._insert_driver(db, (name.strip() or f'Pilota {number}')[:40], number)

    def drivers(self):
        with self.connect() as db:
            rows = [dict(row) for row in db.execute('SELECT * FROM drivers ORDER BY number')]
        for row in rows:
            row['profile'] = json.loads(row['profile'])
            row['policy_profile'] = json.loads(row['policy_profile']) if row['policy_profile'] else None
            row['trained'] = bool(row['policy'])
            row['curriculum'] = json.loads(row['curriculum']) if row['curriculum'] else None
        return rows

    def driver(self, identity):
        return next((x for x in self.drivers() if x['id']==identity), None)

    def set_profile(self, identity, profile):
        validate_profile(profile)
        with self.connect() as db:
            previous = db.execute('SELECT profile FROM drivers WHERE id=?', (identity,)).fetchone()
            if previous is None:
                raise ValueError('Pilota sconosciuto')
            old = json.loads(previous[0])
            incompatible = any(old[k]!=profile[k] for k in ('algorithm','hidden','observation','population','traffic','seed'))
            db.execute('UPDATE drivers SET profile=?,checkpoint=CASE WHEN ? THEN NULL ELSE checkpoint END WHERE id=?',
                       (canonical(profile).decode(), incompatible, identity))
            if incompatible:
                db.execute('UPDATE drivers SET curriculum=NULL,candidate=NULL WHERE id=?',(identity,))
            self._event(db, identity, 'profile', {'previous':old, 'next':profile, 'newPath':incompatible})

    def _event(self, db, driver, kind, payload):
        db.execute('INSERT INTO history(driver,kind,created,payload) VALUES(?,?,?,?)',
                   (driver,kind,stamp(),canonical(payload).decode()))

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

    def save_training(self, identity, checkpoint, policy, steps, seconds, metric=None, curriculum=None):
        checkpoint_hash, policy_hash = self.artifact(checkpoint), self.artifact(policy)
        champion_hash=self.artifact(curriculum['champion']['policy']) if curriculum and curriculum['champion'] else None
        with self.connect() as db:
            if db.execute('SELECT id FROM drivers WHERE id=?',(identity,)).fetchone() is None:
                raise ValueError('Pilota sconosciuto')
            if curriculum is None:
                # Compatibility for old callers/imported training fixtures.
                db.execute('UPDATE drivers SET policy=?,checkpoint=?,steps=?,seconds=?,policy_profile=profile WHERE id=?',
                           (policy_hash,checkpoint_hash,steps,seconds,identity))
            else:
                public_state={**curriculum,'pending':None}
                db.execute('UPDATE drivers SET candidate=?,checkpoint=?,steps=?,seconds=?,curriculum=? WHERE id=?',
                           (policy_hash,checkpoint_hash,steps,seconds,canonical(public_state).decode(),identity))
                if champion_hash:
                    champion_profile=curriculum['champion'].get('profile')
                    if champion_profile:
                        db.execute('UPDATE drivers SET policy=?,policy_profile=? WHERE id=?',(champion_hash,canonical(champion_profile).decode(),identity))
                    else:db.execute('UPDATE drivers SET policy=?,policy_profile=profile WHERE id=?',(champion_hash,identity))
            self._event(db,identity,'checkpoint',{'policy':policy_hash,'checkpoint':checkpoint_hash,
                                                'steps':steps,'seconds':seconds,'metric':metric})
            if curriculum and curriculum['evaluations']:
                proof=curriculum['evaluations'][-1]
                last=db.execute("SELECT payload FROM history WHERE driver=? AND kind='evaluation' ORDER BY id DESC LIMIT 1",(identity,)).fetchone()
                if not last or json.loads(last[0])!=proof:self._event(db,identity,'evaluation',proof)
        return policy_hash

    def begin_session(self, mode, payload):
        identity = uuid.uuid4().hex
        payload = {**payload,'configuration':configuration(),'scope':scope_hash()}
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
                    db.execute('SELECT * FROM history WHERE driver=? ORDER BY id DESC LIMIT 100',(identity,))]
