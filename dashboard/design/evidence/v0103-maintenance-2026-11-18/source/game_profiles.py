"""Shared pilot presets and capabilities; creating a pilot fixes its method."""
from game_catalog import OBSERVATION_VERSION

METHODS = {
    'race_master': ('Maestro','Maestro','Controllo','Bot verificato · guida pronta · nessun apprendimento.'),
    'residual_ppo': ('Crono','Crono · PPO','Rinforzo','PPO · ricerca del tempo sul giro con sterzo e pedali neurali.'),
    'residual_sac': ('Memoria','Memoria · SAC','Rinforzo','SAC · esperienze conservate e due critic per affinare la guida.'),
    'residual_td3': ('Linea','Linea · TD3','Rinforzo','TD3 · guida deterministica e aggiornamenti ritardati.'),
    'residual_tactic': ('Tattico','Tattico · TD3','Rinforzo','TD3 · guida, sorpasso e difesa con attuatori neurali.'),
    'evolution': ('Evo', 'Evoluzione', 'Evoluzione', 'Rete densa · selezione e mutazione dei pesi.'),
    'neat': ('Neat', 'NEAT', 'Evoluzione', 'Evolve nodi e connessioni, con specie distinte.'),
    'ppo': ('PPO', 'PPO', 'Rinforzo', 'Actor e critic · esplorazione gaussiana.'),
    'pure_pursuit': ('Pursuit', 'Pure Pursuit', 'Controllo', 'Punto di mira anticipato · nessun apprendimento.'),
    'imitation': ('Clone', 'Imitazione', 'Imitazione', 'Esempi del maestro negli stati visitati · buffer aggregato.'),
    'ppo_smooth': ('PPO-Smooth', 'PPO-Smooth', 'Rinforzo', 'PPO gaussiano · costo dei comandi bruschi sullo sterzo.'),
    'clone_ppo': ('Ibrido', 'Clone → PPO', 'Imitazione e rinforzo', 'Prima imita il maestro; passa a PPO dopo verifiche di guida e continuità.'),
}
PRESET_VERSION = 3

# Immutable recipes. Existing profiles deliberately acquire no new fields.
VARIANTS = {
    'neat64': dict(name='NEAT-64', algorithm='neat', population=64, description='64 candidati · stessa evoluzione NEAT · variante sperimentale.'),
    'neat_response': dict(name='NEAT-Risposta', algorithm='neat', responseInit=.4, description='Risposta iniziale più graduale · evoluzione pura · sperimentale.'),
    'evo32': dict(name='Evo-32N', algorithm='evolution', hidden=32, description='32 neuroni interni · più capacità da confrontare.'),
    'ppo_cautious': dict(name='PPO-Prudente', algorithm='ppo', learningRate=.0001, description='Aggiornamenti più piccoli · LR 0,0001 · sperimentale.'),
    'regular': dict(name='Regolare', algorithm='clone_ppo', description='Maestro → PPO · priorità a giri puliti e tempi ripetibili.'),
    'attacker': dict(name='Attaccante', algorithm='clone_ppo', description='Maestro → PPO · progressione nel traffico e sorpassi puliti.'),
    'versatile': dict(name='Polivalente', algorithm='clone_ppo', description='Maestro → PPO · esercizi su più piste e ripasso.'),
}


def variant(profile):
    return VARIANTS.get(profile.get('variant'), {})


def uses_teacher(learner):
    return getattr(learner, 'uses_teacher', learner.__class__.__name__ == 'Imitation')


def smooth_objective(profile):
    return profile['algorithm']=='ppo_smooth' or profile.get('variant')=='regular'


def preset(seed=1, algorithm='evolution'):
    recipe = VARIANTS.get(algorithm)
    identity = algorithm
    if recipe: algorithm = recipe['algorithm']
    if algorithm not in METHODS: raise ValueError('Metodo sconosciuto')
    result = {'version':1, 'algorithm':algorithm, 'seed':seed, 'population':32,
            'hidden':16, 'mutation':0.15, 'episodeSeconds':60, 'traffic':False,
            'learningRate':0.0003, 'rollout':256, 'epochs':4, 'gamma':0.995,
            'observation':OBSERVATION_VERSION}
    if algorithm=='clone_ppo' or recipe:result['recipeVersion']=1
    if recipe:
        result['variant']=identity
        for key in ('population','hidden','learningRate'):
            if key in recipe: result[key]=recipe[key]
    return result


def reference_policy(track_id,academy=False):
    from game_catalog import ACTION_VERSION, ACADEMY_OBSERVATION_VERSION
    return {'schema':1, 'kind':'geometric', 'algorithm':'pure_pursuit',
            'controller':'traffic-pursuit-2' if academy else 'pure-pursuit-1', 'track':track_id,
            'observation':ACADEMY_OBSERVATION_VERSION if academy else OBSERVATION_VERSION, 'action':ACTION_VERSION}
