"""NEAT-Python 1.1 adapter with JSON checkpoints (no pickle execution)."""
from __future__ import annotations

from itertools import count
from pathlib import Path
import random

import neat
import numpy as np

from game_catalog import OBSERVATION_VERSION, LEGACY_OBSERVATION_VERSION, ACTION_VERSION, observation_size, observation_version


def tuples(value):
    return tuple(tuples(x) for x in value) if isinstance(value,list) else value


def counter_value(owner, name):
    indexer=getattr(owner,name)
    if indexer is None:return None
    value=next(indexer)
    setattr(owner,name,count(value))
    return value


def genome_data(genome):
    return {'key':genome.key,'fitness':genome.fitness,
            'nodes':[{k:getattr(g,k) for k in ('key','bias','response','activation','aggregation')}
                     for g in genome.nodes.values()],
            'connections':[{k:getattr(g,k) for k in ('key','weight','enabled','innovation')}
                           for g in genome.connections.values()]}


def genome_from(data):
    from neat.genes import DefaultNodeGene, DefaultConnectionGene
    genome=neat.DefaultGenome(data['key'])
    genome.fitness=data['fitness']
    for row in data['nodes']:
        gene=DefaultNodeGene(row['key'])
        for key,value in row.items():setattr(gene,key,value)
        genome.nodes[gene.key]=gene
    for row in data['connections']:
        gene=DefaultConnectionGene(tuple(row['key']),row['innovation'])
        gene.weight,gene.enabled=row['weight'],row['enabled']
        genome.connections[gene.key]=gene
    return genome


def snapshot(genome, config):
    network=neat.nn.FeedForwardNetwork.create(genome,config)
    return {'schema':1,'kind':'neat','algorithm':'neat','observation':observation_version(config.genome_config.num_inputs),
            'action':ACTION_VERSION,'nodes':[{'id':key,'bias':bias,'response':response,'links':links}
            for key,activation,aggregation,bias,response,links in network.node_evals]}


class NEAT:
    def __init__(self, profile, checkpoint=None):
        self.profile=profile
        config=neat.Config(neat.DefaultGenome,neat.DefaultReproduction,neat.DefaultSpeciesSet,
                           neat.DefaultStagnation,str(Path(__file__).with_name('game-neat-config.txt')))
        config.pop_size=profile['population']
        config.genome_config.num_inputs=observation_size(profile['observation'])
        config.genome_config.input_keys=[-i-1 for i in range(config.genome_config.num_inputs)]
        config.genome_config.weight_mutate_power=profile['mutation']
        config.genome_config.bias_mutate_power=profile['mutation']
        self.config=config
        self.population=neat.Population(config,seed=profile['seed'])
        self.best_score=None
        if checkpoint:
            from neat.species import Species
            pop=self.population
            pop.population={g['key']:genome_from(g) for g in checkpoint['population']}
            pop.generation=checkpoint['generation']
            pop.species.species={}
            for row in checkpoint['species']:
                species=Species(row['key'],row['created'])
                for key in ('last_improved','fitness','adjusted_fitness','fitness_history'):
                    setattr(species,key,row[key])
                species.representative=genome_from(row['representative'])
                species.members={key:pop.population[key] for key in row['members']}
                pop.species.species[species.key]=species
            pop.species.genome_to_species={g:key for key,sp in pop.species.species.items() for g in sp.members}
            pop.species.indexer=count(checkpoint['speciesIndexer'])
            pop.reproduction.genome_indexer=count(checkpoint['genomeIndexer'])
            pop.reproduction.ancestors={int(k):tuple(v) for k,v in checkpoint['ancestors'].items()}
            pop.reproduction.innovation_tracker.global_counter=checkpoint['innovationCounter']
            config.genome_config.node_indexer=count(checkpoint['nodeIndexer']) if checkpoint['nodeIndexer'] is not None else None
            config.genome_config.innovation_tracker=pop.reproduction.innovation_tracker
            best=checkpoint['best']
            pop.best_genome=(pop.population.get(best['key']) or genome_from(best)) if best else None
            self.best_score=pop.best_genome.fitness if pop.best_genome else None
            random.setstate(tuples(checkpoint['random']))
            if checkpoint.get('candidate'):self.candidate=checkpoint['candidate']
        self.prepare()

    @property
    def generation(self):
        return self.population.generation

    def prepare(self):
        self.keys=list(self.population.population)
        self.networks=[neat.nn.FeedForwardNetwork.create(self.population.population[k],self.config) for k in self.keys]

    def act(self, observations):
        return np.array([network.activate(row) for network,row in zip(self.networks,observations)])

    def update(self, scores):
        scores=dict(zip(self.keys,map(float,scores)))
        def evaluate(genomes, _config):
            for key,genome in genomes:genome.fitness=scores[key]
            self.candidate=snapshot(max((genome for _,genome in genomes),key=lambda g:g.fitness),self.config)
        best=self.population.run(evaluate,1)
        self.best_score=best.fitness
        self.prepare()
        return {'generation':self.generation,'fitness':max(scores.values()),'bestFitness':self.best_score,
                'species':len(self.population.species.species),'nodes':len(best.nodes),
                'connections':len(best.connections)}

    def policy(self):
        best=self.population.best_genome or self.population.population[self.keys[0]]
        return snapshot(best,self.config)

    def candidate_policy(self):
        best=max(self.population.population.values(),key=lambda g:float('-inf') if g.fitness is None else g.fitness)
        # Reproduction replaces the evaluated population, so use the snapshot
        # captured before it runs (see update).
        return getattr(self,'candidate',snapshot(best,self.config))

    def change_reward(self):
        self.population.best_genome=None
        self.best_score=None
        for species in self.population.species.species.values():
            species.fitness_history=[]
            species.last_improved=self.population.generation

    def checkpoint(self):
        pop=self.population
        return {'algorithm':'neat','library':'1.1.0','generation':pop.generation,
                'population':[genome_data(g) for g in pop.population.values()],
                'best':genome_data(pop.best_genome) if pop.best_genome else None,
                'candidate':getattr(self,'candidate',None),
                'species':[{'key':sp.key,'created':sp.created,'last_improved':sp.last_improved,
                            'fitness':sp.fitness,'adjusted_fitness':sp.adjusted_fitness,
                            'fitness_history':sp.fitness_history,'members':list(sp.members),
                            'representative':genome_data(sp.representative)} for sp in pop.species.species.values()],
                'random':random.getstate(),'speciesIndexer':counter_value(pop.species,'indexer'),
                'genomeIndexer':counter_value(pop.reproduction,'genome_indexer'),
                'ancestors':pop.reproduction.ancestors,
                'innovationCounter':pop.reproduction.innovation_tracker.global_counter,
                'nodeIndexer':counter_value(self.config.genome_config,'node_indexer')}
