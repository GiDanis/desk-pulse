"""Persist the meaning of policy inputs independently of the selected task.

Historical actors retain their trained constant cue. No weights, topology,
optimizer moments or random streams are changed by this adapter.
"""
from copy import deepcopy
import math
import numpy as np

VERSION='driving-inputs-1'
PHASES=('launch','control','pace','follow','overtake','corner','defend','duel','grid','race4')


def legacy_cue(phase):
    return PHASES.index('control' if phase in ('recovery','bend','straight') else phase)/9


def contract(cue=0.,source='new-policy'):
    cue=float(cue)
    if not math.isfinite(cue) or not 0<=cue<=1:raise ValueError('Contesto sensori non valido')
    return dict(version=VERSION,constantCue=cue,source=source,temporal='safe-frontier-1')


def bind(policy,context):
    if not policy or not context:return deepcopy(policy)
    result=deepcopy(policy)
    if result.get('kind') in ('dense','neat') and result.get('observation')=='race-68-v3':
        if not result.get('inputContract'):result['inputContract']=deepcopy(context)
    return result


def adapt(observation,context):
    if not context:return observation
    if context.get('version')!=VERSION:raise ValueError('Contratto sensori sconosciuto')
    result=np.asarray(observation).copy()
    if result.shape[-1]>=68:result[...,67]=contract(context['constantCue'])['constantCue']
    return result


def migrate(checkpoint):
    """Immutable checkpoint input; declare the old actor's main training cue.

    A new collection boundary clears pending old-context observations. Actor,
    critic, examples, optimizer and RNG remain intact. Evaluation proofs stay
    historical and must not certify the new exported policy hash.
    """
    c=deepcopy(checkpoint or {})
    if c.get('inputContract'):return c
    state=c.get('curriculum') or {};phase=state.get('phase','launch')
    context=deepcopy((c.get('learner') or {}).get('inputContract')) or (contract(legacy_cue(phase),'legacy-main-phase:'+phase) if c.get('learner') else contract())
    c['inputContract']=context
    def visit(value,phase):
        if isinstance(value,list):return [visit(x,phase) for x in value]
        if not isinstance(value,dict):return value
        phase=value.get('phase',phase)
        if value.get('kind') in ('dense','neat') and value.get('schema')==1:
            return bind(value,contract(legacy_cue(phase),'legacy-archive:'+phase))
        return {k:visit(v,k.rsplit(':',1)[-1] if isinstance(k,str) and k.rsplit(':',1)[-1] in PHASES else phase) for k,v in value.items()}
    if state:
        c['curriculum']=visit(state,phase)
        c['curriculum'].update(pending=None,reliableWindows=0)
        # Old hash based certificates remain historical; the new actor needs a new check.
        c['curriculum']['champion']=None
        c['curriculum']['qualifications']={}
    memory=c.get('memory') or {}
    c['memory']=memory
    if memory.get('baseline'):
        coverage=memory.get('coverage',[])
        phases={x['phase'] for x in coverage}
        source=next((x for x in reversed(PHASES) if x in phases),'launch')
        memory['baseline']=bind(memory['baseline'],contract(legacy_cue(source),'legacy-memory:'+source))
    c.update(episodes=None,visibleEpisodes=None,fitness=None,inflight=None,observationRows=[],
             collectorResults=None,physicsResults=None,memoryReview=None)
    c['inputMigration']=dict(version=VERSION,boundary='new-collection',kept='weights-topology-optimizer-rng-history')
    if c.get('learner'):
        c['learner']['inputContract']=deepcopy(context)
        # PPO rollout contains observations with varying old task cues.
        c['learner'].update(buffer=[],pending=None)
    return c
