"""Read-only roster metadata. Does not construct GameStore or run learners.

Usage on the board: python3 - /path/to/game < audit_roster.py
Output contains descriptors and counters, never neural weights or replay rows.
"""
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

root = Path(sys.argv[1]).resolve()
db = sqlite3.connect((root / 'game.sqlite').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
db.execute('PRAGMA query_only=ON')
db.execute('BEGIN')


def artifact(digest):
    if not digest:
        return None
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid artifact hash')
    raw = (root / 'policies' / (digest + '.json')).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Artifact checksum mismatch')
    return json.loads(raw)


def describe_policy(digest):
    p = artifact(digest)
    if p is None:
        return None
    return {'hash': digest, **{k: p[k] for k in (
        'kind', 'algorithm', 'hidden', 'observation', 'action', 'controller',
        'inputContract') if k in p}}


def describe_checkpoint(digest):
    c = artifact(digest)
    if c is None:
        return None
    curriculum = c.get('curriculum') or {}
    suite = curriculum.get('evoTraining') or {}
    learner = c.get('learner') or {}
    champion = curriculum.get('champion') or {}
    return dict(hash=digest, steps=c.get('steps'), seconds=c.get('seconds'),
        rewardSpec=c.get('rewardSpec'), inputContract=c.get('inputContract'),
        rewardMigration=c.get('rewardMigration'), tuning=c.get('tuning'),
        learnerTuning=learner.get('tuning'), sourceCheckpoint=c.get('sourceCheckpoint'),
        phase=curriculum.get('phase'), updates=curriculum.get('updates'),
        pacePressure=curriculum.get('pacePressure'),
        epoch={k: (curriculum.get('epochStats') or {})[k] for k in (
            'version', 'startedSteps', 'episodes', 'byTask')
            if k in (curriculum.get('epochStats') or {})},
        stage={k: suite[k] for k in ('version', 'level', 'generations',
            'stageGenerations', 'reliable') if k in suite},
        bestVerified=bool(champion),
        population=len(learner.get('population', [])),
        species=len(learner.get('species', [])),
        recentSuite=suite.get('recent', [])[-8:],
        metric=c.get('metric'),
        totalEpisodes=(curriculum.get('stats') or {}).get('episodes'))


drivers = []
for d in db.execute('SELECT * FROM drivers ORDER BY number').fetchall():
    paths = []
    for p in db.execute('SELECT * FROM driver_paths WHERE id=? ORDER BY track_id', (d['id'],)).fetchall():
        paths.append(dict(track=p['track_id'], profile=json.loads(p['profile']),
            steps=p['steps'], seconds=p['seconds'],
            policy=describe_policy(p['policy']),
            candidate=describe_policy(p['candidate']),
            checkpoint=describe_checkpoint(p['checkpoint'])))
    objectives = []
    for row in db.execute('SELECT track,objective,state FROM objective_paths WHERE driver=? ORDER BY track,objective', (d['id'],)).fetchall():
        state = json.loads(row['state'])
        objectives.append(dict(track=row['track'], objective=row['objective'],
            steps=state.get('steps'), seconds=state.get('seconds'),
            checkpoint=describe_checkpoint(state.get('checkpoint'))))
    drivers.append(dict(id=d['id'], name=d['name'], number=d['number'],
        profile=json.loads(d['profile']), steps=d['steps'], seconds=d['seconds'],
        policy=describe_policy(d['policy']),
        checkpoint=describe_checkpoint(d['checkpoint']), paths=paths,
        objectives=objectives))

sessions = [dict(row) for row in db.execute(
    'SELECT id,mode,status,created,updated FROM sessions ORDER BY updated DESC LIMIT 5')]
db.rollback()
db.close()
print(json.dumps(dict(capturedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    access='sqlite mode=ro, query_only, single read transaction; immutable artifacts verified',
    scope='metadata only; no training, no frozen driving tests, no service restart',
    drivers=drivers, sessions=sessions), indent=2))
