"""Personal, versioned driving knowledge; no imports of a learner while browsing."""
from copy import deepcopy
import math
import json
from functools import lru_cache
from game_catalog import ACADEMY_OBSERVATION_VERSION, configuration, observation_size, TRACKS, scope_hash

PROTOCOL='driving-memory-1'
REWARD='valid-progress-recovery-1'
PHASES=('launch','control','recovery','pace','follow','overtake','corner','defend','duel','grid','race4')
LABELS={'recovery':'Rientro'}
REPLAY_EVERY=5
PPO_DEFAULTS={'gaeLambda':.99,'batchSize':64,'clip':.2,'entropy':.001,'targetKL':.03}


def _canonical(value):
    from game_store import canonical
    return canonical(value)


def _digest(value):
    from game_curriculum import digest
    return digest(value)


def task(track,phase):
    if phase=='straight':
        return dict(version='evo-progressive-1',phase=phase,label='Rettilineo · 40 m',distance=40.,laps=1,
                    limitSeconds=25.,opponents=0,teacher='traffic-pursuit-2',rewardVersion='balanced-driving-2')
    if phase=='bend':
        return dict(version='corner-control-1',phase=phase,label='Ingresso curva · 140 m',distance=140.,laps=1,
                    limitSeconds=45.,opponents=0,stall=dict(grace=2.,creditMeters=1.,slowSeconds=4.,maxNoProgressSeconds=15.),
                    teacher='traffic-pursuit-2',rewardVersion='balanced-driving-1')
    from game_protocol import academy_task
    if phase!='recovery':return {**academy_task(track,phase),'version':PROTOCOL,'rewardVersion':REWARD}
    return dict(version=PROTOCOL,phase=phase,label='Rientro',distance=40.,laps=1,
                limitSeconds=25.,opponents=0,stall=dict(grace=2.,creditMeters=1.,slowSeconds=4.,maxNoProgressSeconds=15.),
                teacher='traffic-pursuit-2',rewardVersion=REWARD)


def physical_context(config):
    """Small immutable descriptor; the versioned track geometry stays in the catalog."""
    from game_catalog import configuration_hash
    track=config['track']
    return dict(track={k:track[k] for k in ('id','revision','geometryHash') if k in track},
                vehicle=deepcopy(config['vehicle']),surface=deepcopy(config['surface']),
                condition=deepcopy(config['condition']),tire=deepcopy(config['tire']),physics=config['physics'],
                observation=config['observation'],contextHash=configuration_hash(config))


def current_context(track,observation=ACADEMY_OBSERVATION_VERSION):
    import game_catalog as catalog
    content=catalog.track_data(track)
    return _cached_context(track,observation,catalog.RACE_VEHICLE,catalog.SURFACE,catalog.CONDITION,catalog.TIRE,
                           content.get('geometryHash'),content.get('revision'))


@lru_cache(maxsize=32)
def _cached_context(track,observation,vehicle,surface,condition,tire,geometry,revision):
    return physical_context(configuration(track,observation))


def base_status(coverage):
    skills={c['phase'] for c in coverage}
    return 'consolidated' if {'launch','control'}<=skills else 'provisional'


def summary(data):
    if not data or not data.get('base'):return dict(status='empty',label='Da costruire',revision=0,skills=[],source='',policy='',contexts=[])
    base=data['base']
    return dict(status=base['status'],label='Consolidata' if base['status']=='consolidated' else 'In formazione',
                revision=base['revision'],skills=sorted({c['phase'] for c in base.get('coverage',[])}),
                source=base['source'],policy=base['policyHash'],contexts=sorted({c['track'] for c in base.get('coverage',[])}) )


def sources(store,identity):
    """Known paths only; never another pilot's models or synthetic successes."""
    rows=[]
    for track in ('oval-1',*[t['id'] for t in TRACKS if t['id']!='oval-1']):
        d=store.driver(identity,track)
        if not d:continue
        state=d.get('curriculum') or {}
        for field in ('candidate','policy'):
            if not d.get(field):continue
            p=store.load(d[field]);profile=d['profile'] if field=='candidate' else d.get('policy_profile') or d['profile']
            if p.get('kind') not in ('dense','neat'):continue
            checkpoint=store.load(d['checkpoint']) if d.get('checkpoint') else None
            if checkpoint and checkpoint.get('sourceCheckpoint') and profile['algorithm']=='neat':
                checkpoint=store.load(checkpoint['sourceCheckpoint'])
            evidence=d.get('policy_curriculum') or state if field=='policy' else state
            proof=(evidence.get('champion') or {}).get('proof') or {}
            valid=proof.get('candidateHash')==d[field]
            skills=proof.get('candidate',{}).get('skills',{}) if valid else {}
            coverage=[dict(track=track,phase=k,result=v) for k,v in skills.items() if v.get('valid',0)>=math.ceil(.9*v.get('total',20))]
            if valid and not skills and proof.get('candidate',{}).get('valid',0)>=math.ceil(.9*proof.get('candidate',{}).get('total',10)):
                coverage=[dict(track=track,phase=proof.get('phase','control'),result=proof['candidate'])]
            from game_observation_contract import bind,contract,legacy_cue
            p=bind(p,contract(legacy_cue(evidence.get('phase','launch')),'legacy-source:'+evidence.get('phase','launch')))
            rows.append(dict(track=track,policy=p,policyHash=d[field],profile=profile,checkpoint=checkpoint,
                             coverage=coverage,phase=state.get('phase','launch'),rank=(len(coverage),int(valid),int(field=='candidate'))))
    return rows


def seed_learner(profile,policy,donor=None):
    """New task optimizer/fitness; exact inherited actor or intact NEAT genotype."""
    import numpy as np
    from game_hybrid import ClonePPO
    from game_learning import Evolution,PPO,PPOSmooth,Imitation,Policy
    Policy(policy)
    from game_academy import expand_weights
    if policy['algorithm']!=profile['algorithm']:raise ValueError('Memoria di un altro paradigma')
    cls={'evolution':Evolution,'ppo':PPO,'ppo_smooth':PPOSmooth,'imitation':Imitation,'clone_ppo':ClonePPO}.get(profile['algorithm'])
    if cls:
        if policy['kind']!='dense' or policy['hidden']!=profile['hidden']:raise ValueError('Dimensione della memoria incompatibile')
        old=observation_size(policy['observation']);new=observation_size(profile['observation'])
        if old>new:raise ValueError('Schema memoria non riducibile')
        weights=np.asarray(policy['weights']) if old==new else expand_weights(policy['weights'],old,new,profile['hidden'])
        obj=cls(profile)
        obj.input_contract=deepcopy(policy.get('inputContract'))
        if isinstance(obj,ClonePPO):
            phase=(policy.get('recipe') or {}).get('phase','imitation')
            obj.phase=phase;obj.hybrid['phase']=phase
            obj.hybrid['sourceHash']=_digest(policy)
            obj.hybrid['inheritedPhase']=phase
            obj.actor=weights.copy()
            if obj.uses_teacher:
                obj.teacher.weights=obj.actor;obj.teacher.best=obj.actor.copy()
        elif isinstance(obj,PPO):obj.actor=weights.copy()
        elif isinstance(obj,Evolution):
            obj.best=weights.copy();obj.population[0]=weights
            n=max(2,len(obj.population)//2)
            obj.population[1:n]=weights+obj.rng.normal(0,profile['mutation']*.25,(n-1,len(weights)))
        else:
            obj.weights=weights.copy();obj.best=weights.copy()
            # Only explicitly labelled compatible teacher data, never rewards.
            if donor and donor.get('algorithm')=='imitation':
                for x,y in donor.get('examples',[]):
                    if len(x)<=obj.inputs:obj.samples.append((np.pad(np.asarray(x),(0,obj.inputs-len(x))),np.asarray(y)))
        return obj.checkpoint()
    from game_neat import NEAT,genome_from,snapshot
    if policy['kind']!='neat':raise ValueError('Genoma NEAT mancante')
    obj=NEAT(profile)
    obj.input_contract=deepcopy(policy.get('inputContract'))
    # Exported policies carry the full genotype, not only executable node_evals.
    genes=policy.get('genome')
    if not genes and donor:
        from game_curriculum import digest
        candidates=[donor.get('best'),*donor.get('population',[])]
        for row in candidates:
            if row and digest(snapshot(genome_from(row),obj.config,include_genome=False)['nodes'])==digest(policy['nodes']):genes=row;break
    if not genes:raise ValueError('Topologia storica NEAT non ricostruibile: modello conservato')
    pop=obj.population
    rng=obj_rng(obj)
    for i,key in enumerate(list(pop.population)):
        genome=genome_from(deepcopy(genes));genome.key=key;genome.fitness=None
        if i:
            for connection in genome.connections.values():connection.weight+=obj.profile['mutation']*.25*float(rng.normal())
        pop.population[key]=genome
    max_node=max([1,*[g['key']+1 for g in genes['nodes']]])
    from itertools import count
    obj.config.genome_config.node_indexer=count(max_node)
    pop.reproduction.innovation_tracker.global_counter=max([0,*[g['innovation'] for g in genes['connections']]])
    pop.reproduction.innovation_tracker.reset_generation()
    pop.species.species={};pop.species.genome_to_species={};pop.species.speciate(obj.config,pop.population,0)
    obj.prepare()
    return obj.checkpoint()


def obj_rng(obj):
    import numpy as np
    if not hasattr(obj,'_memory_rng'):obj._memory_rng=np.random.default_rng(obj.profile['seed']+319)
    return obj._memory_rng


def normalized_policy(profile,policy,donor=None):
    """Expand a source without changing its learned old-channel behavior."""
    from game_hybrid import ClonePPO
    from game_learning import Evolution,PPO,PPOSmooth,Imitation
    backend=seed_learner(profile,policy,donor)
    cls={'evolution':Evolution,'ppo':PPO,'ppo_smooth':PPOSmooth,'imitation':Imitation,'clone_ppo':ClonePPO}.get(profile['algorithm'])
    if cls:return cls(profile,backend).policy()
    from game_neat import NEAT
    obj=NEAT(profile,backend)
    from game_neat import snapshot
    from game_observation_contract import bind
    return bind(snapshot(obj.population.population[obj.keys[0]],obj.config),obj.input_contract)


def select_base(store,identity,profile):
    data=store.memory_record(identity)
    if data and data.get('base'):
        base=data['base'];policy=store.load(base['policyHash'])
        if policy.get('observation')==ACADEMY_OBSERVATION_VERSION and not policy.get('inputContract'):
            from game_observation_contract import bind,contract,legacy_cue
            phases={c['phase'] for c in base.get('coverage',[])}
            phase=next((x for x in reversed(PHASES) if x in phases),'launch')
            policy=bind(policy,contract(legacy_cue(phase),'legacy-memory-coverage:'+phase))
            previous=deepcopy(base);base['policyHash']=store.artifact(policy)
            base['sourcePolicy']=previous['policyHash'];base['inputContract']=deepcopy(policy['inputContract'])
            data['history']=(data.get('history',[])+[previous])[-20:]
            store.write_memory(identity,data)
        # Check structural compatibility rather than silently discarding memory.
        seed_learner(profile,policy,store.load(base['seedHash']) if base.get('seedHash') else None)
        return data
    if data and data.get('reset'):return data
    candidates=[r for r in sources(store,identity) if r['profile']['algorithm']==profile['algorithm']]
    candidates.sort(key=lambda r:r['rank'],reverse=True)
    errors=[]
    for source in candidates:
        try:policy=normalized_policy(profile,source['policy'],(source['checkpoint'] or {}).get('learner'))
        except ValueError as error:errors.append(str(error));continue
        key=store.artifact(policy);donor=(source['checkpoint'] or {}).get('learner')
        data=dict(version=1,base=dict(revision=1,policyHash=key,seedHash=store.artifact(donor) if donor else None,
                source=source['track'],sourcePolicy=source['policyHash'],status='provisional',coverage=[],
                observedCoverage=source['coverage']),history=[],reviews=[],reset=False)
        store.write_memory(identity,data);return data
    if candidates:raise ValueError('Memoria esistente incompatibile: '+errors[0])
    return dict(version=1,base=None,history=[],reviews=[],reset=False)


def prepare_path(store,identity):
    """Called exclusively by Start, after the legacy Academy expansion."""
    from game_academy import academy_profile,upgrade_learner
    row=store.driver(identity)
    if row['profile']['algorithm']=='pure_pursuit':return row
    profile=academy_profile(row['profile'])
    old=store.load(row['checkpoint']) if row['checkpoint'] else None
    config=configuration(store.track_id,profile['observation'])
    if old and old.get('protocol')==PROTOCOL:
        if old['configuration']==config:return row
        # The context changes when vehicle, grip or physical content changes.
        # Preserve and resume each specialist independently of the shared base.
        from game_catalog import configuration_hash
        from game_store import canonical
        select_base(store,identity,profile)
        with store.connect() as db:
            where,args=store.where(identity)
            raw=dict(db.execute('SELECT * FROM '+store.table+' WHERE '+where,args).fetchone())
            db.execute('INSERT OR REPLACE INTO driving_contexts VALUES(?,?,?,?)',(identity,configuration_hash(old['configuration']),canonical(old['configuration']).decode(),canonical(raw).decode()))
            target=db.execute('SELECT state FROM driving_contexts WHERE id=? AND context_hash=?',(identity,configuration_hash(config))).fetchone()
            restored=json.loads(target[0]) if target else dict(profile=canonical(profile).decode(),policy=None,policy_profile=None,candidate=None,curriculum=None,checkpoint=None,steps=0,seconds=0)
            keys=('profile','policy','policy_profile','candidate','curriculum','checkpoint','steps','seconds')
            db.execute('UPDATE '+store.table+' SET '+','.join(k+'=?' for k in keys)+' WHERE '+where,(*[restored[k] for k in keys],*args))
        row=store.driver(identity);old=store.load(row['checkpoint']) if row['checkpoint'] else None
        if old:return row
    data=select_base(store,identity,profile)
    base=data.get('base');provenance=None
    if old and old.get('learner'):
        # Existing local experience has priority over a newer personal base.
        backend=upgrade_learner(old,profile)
        if backend.get('algorithm')=='neat' and old['learner'].get('best'):
            backend['best']=deepcopy(old['learner']['best']);backend['best']['fitness']=None
        state=deepcopy(old.get('curriculum'))
        if state:
            state.update(rewardVersion=REWARD,pending=None,reliableWindows=0,protocol=PROTOCOL)
            state['qualifications']={};state['champion']=None
        provenance=old.get('memory')
        steps=old.get('steps',row['steps']);seconds=old.get('seconds',row['seconds'])
        fresh=not state and steps==0
    else:
        explicit=store.initializer(identity)
        if explicit:
            backend=seed_learner(profile,explicit);policy=normalized_policy(profile,explicit)
            provenance=dict(baseHash=store.artifact(policy),source='manual',revision=0,status='provisional')
        elif base:
            backend=seed_learner(profile,store.load(base['policyHash']),store.load(base['seedHash']) if base.get('seedHash') else None)
            provenance=dict(baseHash=base['policyHash'],source=base['source'],revision=base['revision'],status=base['status'])
        else:backend=None
        state=None;steps=seconds=0;fresh=bool(backend)
    memory={**(provenance or {}),'coverage':deepcopy((base.get('coverage') or base.get('observedCoverage',[])) if base else []),
            'baseline':store.load(base['policyHash']) if base else None,
            'reviewRevision':base['revision'] if base else 0,'fresh':fresh}
    warm=dict(schema=3,academyVersion='academy-1',protocol=PROTOCOL,configuration=configuration(store.track_id,profile['observation']),
        learner=backend,curriculum=state,episodes=None,steps=steps,seconds=seconds,memory=memory,
        sourceCheckpoint=row['checkpoint'],sourcePolicy=memory.get('baseHash'),tuning=PPO_DEFAULTS,contextHash=scope_hash(store.track_id,profile['observation']))
    key=store.artifact(warm)
    with store.connect() as db:
        where,args=store.where(identity)
        existing=dict(db.execute('SELECT * FROM '+store.table+' WHERE '+where,args).fetchone())
        if existing['checkpoint']!=row['checkpoint']:raise ValueError('Percorso aggiornato durante l’inizializzazione')
        db.execute('INSERT OR IGNORE INTO driving_archives VALUES(?,?,?,?)',(identity,store.track_id,row['checkpoint'] or key,_canonical(existing).decode()))
        db.execute('UPDATE '+store.table+' SET profile=?,checkpoint=?,candidate=NULL,curriculum=? WHERE '+where,
                   (_canonical(profile).decode(),key,_canonical(state).decode() if state else None,*args))
        db.execute('DELETE FROM path_initializers WHERE id=? AND track_id=?',(identity,store.track_id))
        store._event(db,identity,'memory',dict(source=memory.get('source','local'),policy=memory.get('baseHash'),protocol=PROTOCOL,sourceCheckpoint=row['checkpoint'],continued=bool(old)))
    return store.driver(identity)


class Review:
    """Fresh paired scenarios, one physics transition per call, durable pause."""
    def __init__(self,candidate,baseline,contexts,revision,kind='consolidation',saved=None):
        from game_learning import Policy
        from game_academy import Episode
        self.candidate=deepcopy(candidate);self.baseline=deepcopy(baseline);self.contexts=deepcopy(contexts)
        self.revision=revision;self.kind=kind;self.cursor=0;self.cancelled=False
        self.policies=[Policy(candidate)]+([Policy(baseline)] if baseline else [])
        self.episodes=[]
        for _ in self.policies:
            for c in contexts:
                for i in range(20):
                    try:e=Episode(c['track'],c['phase'],2_000_001+revision*100+i,protocol=PROTOCOL,context=c.get('configuration'))
                    except ValueError:
                        e=Episode(c['track'],c['phase'],2_000_001+revision*100+i,protocol=PROTOCOL);e.reason='not_run';e.truncated=True
                    self.episodes.append(e)
        if saved:
            self.cursor=saved['cursor'];self.cancelled=saved['cancelled']
            for e,s in zip(self.episodes,saved['episodes'],strict=True):e.restore(s)

    def tick(self):
        n=20
        for k in range(len(self.contexts)):
            rows=self.episodes[k*n:(k+1)*n]
            if sum(bool(e.reason) and e.reason!='success' for e in rows)>2:
                self.cancelled=True
                for e in self.episodes:
                    if not e.reason:e.reason='not_run';e.truncated=True
                return True
        for _ in range(len(self.episodes)):
            i=self.cursor%len(self.episodes);self.cursor+=1;e=self.episodes[i]
            if e.reason:continue
            p=self.policies[i//(len(self.contexts)*20)]
            e.step(p.act(e.observations(),world=e.world,index=0));return all(e.reason for e in self.episodes)
        return True

    def result(self):
        from game_curriculum import summary as stats
        groups=[]
        for p in range(len(self.policies)):
            out=[]
            for k,c in enumerate(self.contexts):
                start=(p*len(self.contexts)+k)*20
                result=stats([e.result() for e in self.episodes[start:start+20]])
                out.append({**c,'contextHash':self.episodes[start].context_config['contextHash'],
                            'configuration':deepcopy(self.episodes[start].context_config),'result':result})
            groups.append(out)
        passed=all(c['result']['valid']>=18 for c in groups[0])
        if passed and len(groups)>1:
            for new,old in zip(*groups):
                a,b=new['result'],old['result']
                if b['valid']>=18 and (a['valid']<b['valid'] or (b['median'] and a['median']>b['median']*1.05)):passed=False
        return dict(kind=self.kind,passed=passed,cancelled=self.cancelled,coverage=groups[0],baseline=groups[1] if len(groups)>1 else None,
                    policy=self.candidate,revision=self.revision)

    def snapshot(self):
        return dict(candidate=self.candidate,baseline=self.baseline,contexts=self.contexts,revision=self.revision,kind=self.kind,
                    cursor=self.cursor,cancelled=self.cancelled,episodes=[e.snapshot() for e in self.episodes])


def save_base(store,db,identity,checkpoint,policy,policy_hash):
    """Persist provisional knowledge and paired, validated promotions in one tx."""
    if checkpoint.get('backend')=='sb3-skill-1':
        from game_store import canonical
        row=db.execute('SELECT data FROM driver_memory WHERE id=?',(identity,)).fetchone()
        data=json.loads(row[0]) if row else dict(version=1,base=None,history=[],reviews=[],reset=False)
        old=data.get('reference') or {}
        data['reference']=dict(backend='sb3-skill-1',policyHash=policy_hash,algorithm=policy['algorithm'],hidden=policy['hidden'],
            track=store.track_id,objective=getattr(store,'objective','impara'),revision=old.get('revision',0)+int(old.get('policyHash')!=policy_hash),
            status='candidate')
        db.execute('INSERT OR REPLACE INTO driver_memory VALUES(?,?)',(identity,canonical(data).decode()))
        return
    if checkpoint.get('protocol')!=PROTOCOL:return
    from game_store import canonical
    row=db.execute('SELECT data FROM driver_memory WHERE id=?',(identity,)).fetchone()
    data=json.loads(row[0]) if row else dict(version=1,base=None,history=[],reviews=[],reset=False)
    if not data.get('base'):
        data['base']=dict(revision=0,policyHash=policy_hash,seedHash=store.artifact(checkpoint['learner']),source=store.track_id,
                          sourcePolicy=policy_hash,status='provisional',coverage=[])
        data['reset']=False
    for review in checkpoint.get('memoryReviews',[]):
        key=_digest({k:v for k,v in review.items() if k!='policy'})
        if any(r['id']==key for r in data['reviews']):continue
        data['reviews']=(data['reviews']+[dict(id=key,passed=review['passed'],revision=review['revision'],track=store.track_id)])[-40:]
        if review['passed'] and review['revision']==data['base']['revision']:
            from game_learning import Policy
            Policy(review['policy'])
            if review['policy']['kind'] not in ('dense','neat'):raise ValueError('La memoria personale richiede una rete appresa')
            if not all(c['result']['valid']>=18 for c in review['coverage']):raise ValueError('Prova di memoria incompleta')
            old=deepcopy(data['base']);key_policy=store.artifact(review['policy'])
            data['history']=(data['history']+[old])[-20:]
            data['base']=dict(revision=old['revision']+1,policyHash=key_policy,seedHash=store.artifact(checkpoint['learner']),
                source=store.track_id,sourcePolicy=key_policy,status=base_status(review['coverage']),coverage=review['coverage'])
            store._event(db,identity,'consolidation',dict(revision=data['base']['revision'],policy=key_policy,
                             coverage=review['coverage'],previous=old['policyHash']))
    db.execute('INSERT OR REPLACE INTO driver_memory VALUES(?,?)',(identity,canonical(data).decode()))
