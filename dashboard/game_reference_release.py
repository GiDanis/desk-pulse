"""Atomic activation of scientifically and technically qualified pilots.

Called by the release installer with the Dashboard stopped, never at boot or
while opening the Game view. Old model/profile paths remain recoverable.
"""
from copy import deepcopy
import json
from game_residual import key

METHODS=('residual_ppo','residual_sac','residual_td3','residual_tactic')
VERSION='pilot-reference-release-1'


def validate(proposal,arm):
    from game_lab.qualification import VERSION as GATE
    from game_lab.provenance import source_hashes
    from game_catalog import configuration
    from game_temporal import TemporalPolicy
    if proposal.get('version')!=VERSION or set(proposal.get('methods',{}))!=set(METHODS):
        raise ValueError('Servono tutti e quattro i metodi qualificati')
    hashes={}
    for method,pack in proposal['methods'].items():
        policy=pack['policy'];qualification=pack.get('qualification',{});runs=qualification.get('runs',[])
        TemporalPolicy(policy)
        if (pack.get('policyHash')!=key(policy) or policy.get('algorithm')!=method
            or policy.get('hidden')!=128 or policy.get('features')!='direct-physical-90-road-v2'
            or (policy.get('origin') or {}).get('backend')!='sb3-skill-1'):
            raise ValueError('Modello della consegna incompatibile')
        if (qualification.get('version')!=GATE or qualification.get('qualified') is not True
            or qualification.get('failures') or len(runs)!=5 or len({r.get('seed') for r in runs})!=5
            or len({r.get('datasetHash') for r in runs})!=5 or qualification.get('improvedSeeds',0)<4
            or any(not r.get('passed') or r.get('issues') for r in runs)
            or not any(r.get('seed')==pack.get('selectedSeed') and r.get('candidateHash')==key(policy) for r in runs)
            or pack.get('context')!=configuration('oval-1','race-68-v3')):
            raise ValueError('Qualifica scientifica incompleta')
        hashes[method]=key(policy)
    if (arm.get('version')!=VERSION or arm.get('qualified') is not True
        or arm.get('policies')!=hashes or arm.get('runtimeSourceHashes')!=source_hashes()
        or not all(arm.get('checks',{}).get(k) is True for k in
            ('learning','exactResume','allModes','race2','race5','eglfsBase','eglfsFunctional','eglfsApple','health'))):
        raise ValueError('Qualifica ARM e della Dashboard incompleta')
    return hashes


def install(store,proposal,arm):
    """Publish the release authority and all four profile pointers in one tx."""
    from game_store import canonical,validate_profile
    hashes=validate(proposal,arm);people=store.drivers()
    proposal_hash=key(proposal)
    if store.reference_release().get('proposalHash')==proposal_hash:
        return dict(version=VERSION,installed=False,alreadyInstalled=True,policies=hashes)
    targets={method:[d for d in people if d['profile']['algorithm']==method] for method in METHODS}
    if store.track_id!='oval-1' or any(len(v)!=1 for v in targets.values()):raise ValueError('Rosa da migrare non univoca')
    # Immutable objects are durable before SQLite can point to them.
    for method,pack in proposal['methods'].items():
        if store.artifact(pack['policy'])!=hashes[method]:raise ValueError('Policy persistita incoerente')
    receipt=dict(version=VERSION,qualified=True,policies=list(hashes.values()),basesByMethod=hashes,
        proposalHash=store.artifact(proposal),arm=deepcopy(arm))
    with store.connect() as db:
        for method,rows in targets.items():
            driver=rows[0];old=driver['profile'];new=validate_profile({**old,'hidden':128,'learningBackend':'sb3-skill-1'})
            fields=('profile','policy','checkpoint','candidate','curriculum','policy_profile','steps','seconds')
            raw=dict(db.execute('SELECT * FROM drivers WHERE id=?',(driver['id'],)).fetchone())
            previous={k:raw.get(k) for k in fields}
            db.execute('INSERT OR REPLACE INTO profile_paths VALUES(?,?,?,?)',
                (driver['id'],store.track_id,store.path_key(old),canonical(previous).decode()))
            db.execute('UPDATE drivers SET profile=?,policy=?,policy_profile=?,candidate=?,checkpoint=NULL,curriculum=NULL,steps=0,seconds=0 WHERE id=?',
                (canonical(new).decode(),hashes[method],canonical(new).decode(),hashes[method],driver['id']))
            # Archive alternate objectives before publishing their replacement.
            # Otherwise the first new save could overwrite a legacy checkpoint
            # with the same track configuration and lose its recovery pointer.
            objectives=[dict(r) for r in db.execute('SELECT * FROM objective_paths WHERE driver=?',(driver['id'],))]
            objective_archives=[dict(r) for r in db.execute('SELECT * FROM objective_archives WHERE driver=?',(driver['id'],))]
            paths=[dict(r) for r in db.execute('SELECT * FROM driver_paths WHERE id=?',(driver['id'],))]
            memory=db.execute('SELECT data FROM driver_memory WHERE id=?',(driver['id'],)).fetchone()
            previous_memory=json.loads(memory['data']) if memory else None
            certificates=[dict(r) for r in db.execute('SELECT * FROM timed_qualifications WHERE driver=?',(driver['id'],))]
            store._event(db,driver['id'],'reference_archive',dict(release=VERSION,objectives=objectives,
                objectiveArchives=objective_archives,paths=paths,memory=previous_memory,qualifications=certificates))
            db.execute('DELETE FROM objective_paths WHERE driver=?',(driver['id'],))
            db.execute('DELETE FROM objective_archives WHERE driver=?',(driver['id'],))
            if previous_memory and 'reference' in previous_memory:
                # A later release can keep the same backend and dimensions.
                # Its first Start must still use the newly qualified factory,
                # rather than resurrecting the old personal candidate.
                previous_memory.pop('reference')
                db.execute('UPDATE driver_memory SET data=? WHERE id=?',(canonical(previous_memory).decode(),driver['id']))
            if old.get('learningBackend')=='sb3-skill-1':
                for certificate in certificates:
                    data=json.loads(certificate['data']);data['releaseArchived']=proposal_hash
                    db.execute('UPDATE timed_qualifications SET data=? WHERE driver=? AND scope=? AND policy=?',
                        (canonical(data).decode(),driver['id'],certificate['scope'],certificate['policy']))
            from game_store import path_profile
            for path in paths:
                saved={k:path.get(k) for k in fields};old_profile=json.loads(path['profile'])
                db.execute('INSERT OR REPLACE INTO profile_paths VALUES(?,?,?,?)',
                    (driver['id'],path['track_id'],store.path_key(old_profile),canonical(saved).decode()))
                profile=path_profile(new,path['track_id'])
                db.execute('UPDATE driver_paths SET profile=?,policy=?,policy_profile=?,candidate=?,checkpoint=NULL,curriculum=NULL,steps=0,seconds=0 WHERE id=? AND track_id=?',
                    (canonical(profile).decode(),hashes[method],canonical(profile).decode(),hashes[method],driver['id'],path['track_id']))
            store._event(db,driver['id'],'profile',dict(previous=old,next=new,newPath=True,
                release=VERSION,sourceCheckpoint=driver.get('checkpoint'),archivedPolicy=driver.get('policy')))
        db.execute("INSERT OR REPLACE INTO reference_releases VALUES('current',?)",(canonical(receipt).decode(),))
    return dict(version=VERSION,installed=True,policies=hashes,drivers={m:rows[0]['id'] for m,rows in targets.items()})
