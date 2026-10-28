"""Shared pilot presets and capabilities; creating a pilot fixes its method."""
from game_catalog import OBSERVATION_VERSION

METHODS = {
    'evolution': ('Evo', 'Evoluzione', 'Evoluzione', 'Rete densa · selezione e mutazione dei pesi.'),
    'neat': ('Neat', 'NEAT', 'Evoluzione', 'Evolve nodi e connessioni, con specie distinte.'),
    'ppo': ('PPO', 'PPO', 'Rinforzo', 'Actor e critic · esplorazione gaussiana.'),
    'pure_pursuit': ('Pursuit', 'Pure Pursuit', 'Controllo', 'Punto di mira anticipato · nessun apprendimento.'),
    'imitation': ('Clone', 'Imitazione', 'Imitazione', 'Esempi del maestro negli stati visitati · buffer aggregato.'),
    'ppo_smooth': ('PPO-Smooth', 'PPO-Smooth', 'Rinforzo', 'PPO gaussiano · costo dei comandi bruschi sullo sterzo.'),
}
PRESET_VERSION = 2


def preset(seed=1, algorithm='evolution'):
    if algorithm not in METHODS: raise ValueError('Metodo sconosciuto')
    return {'version':1, 'algorithm':algorithm, 'seed':seed, 'population':32,
            'hidden':16, 'mutation':0.15, 'episodeSeconds':60, 'traffic':False,
            'learningRate':0.0003, 'rollout':256, 'epochs':4, 'gamma':0.995,
            'observation':OBSERVATION_VERSION}


def reference_policy(track_id):
    from game_catalog import ACTION_VERSION
    return {'schema':1, 'kind':'geometric', 'algorithm':'pure_pursuit',
            'controller':'pure-pursuit-1', 'track':track_id,
            'observation':OBSERVATION_VERSION, 'action':ACTION_VERSION}
