"""Versioned recipe fields shared by production, validation and migration."""
METHODS=('residual_ppo','residual_sac','residual_td3','residual_tactic')
RACING_FIELDS={
    'learningBackend':((str,),('sb3-skill-1',)),
    'trafficLearning':((str,),('attack-1',)),
    'relativeAdvantage':((int,float),(0.,.25,.5)),
    'racingObjective':((str,),('legacy','valid-time-1')),
    'racingCurriculum':((str,),('graduated-1',)),
    'expertLearning':((str,),('routed-1',)),
    'racingAnchor':((str,),('steering-retained-1',)),
    'episodeExploration':((str,),('coherent-pedal-1',)),
    'racingBackup':((int,),(1,2,3,5)),
    'racingHorizon':((int,float),(4.,8.)),
    'raceValidationEvery':((int,),(1,2,3,4)),
}
PROFILE_KEYS=tuple(RACING_FIELDS)
RACING_DEFAULTS=dict(racingObjective='valid-time-1',racingCurriculum='graduated-1',
    expertLearning='routed-1',racingAnchor='steering-retained-1',raceValidationEvery=4)


def validate_recipe_fields(profile):
    present=set(profile)&set(PROFILE_KEYS)
    if not present:return
    if profile.get('controlMode')!='direct' or profile.get('algorithm') not in METHODS:
        raise ValueError('Ricetta di apprendimento incompatibile con il metodo di guida')
    for name in PROFILE_KEYS:
        if name not in present:continue
        types,values=RACING_FIELDS[name];value=profile[name]
        if type(value) not in types or value not in values:
            raise ValueError('Parametro ricetta non supportato: '+name)
    if profile.get('racingCurriculum')=='graduated-1' and profile.get('racingObjective')!='valid-time-1':
        raise ValueError('Curriculum incompatibile con racingObjective')
    if 'racingHorizon' in present and profile['algorithm']!='residual_ppo':
        raise ValueError('racingHorizon richiede PPO')
    if 'racingBackup' in present and profile['algorithm']=='residual_ppo':
        raise ValueError('racingBackup richiede SAC o TD3')
    if 'relativeAdvantage' in present and profile.get('trafficLearning')!='attack-1':
        raise ValueError('relativeAdvantage richiede trafficLearning')
    if 'trafficLearning' in present and (profile.get('racingCurriculum')!='graduated-1' or profile.get('racingObjective')!='valid-time-1'):
        raise ValueError('trafficLearning richiede obiettivo sul tempo e scuola graduata')


def production_profile(profile):
    result=dict(profile)
    if 'racingObjective' in result or not result.get('algorithm','').startswith('residual_'):
        return result
    result.update(RACING_DEFAULTS)
    if result['algorithm']=='residual_ppo':result['episodeExploration']='coherent-pedal-1'
    return result
