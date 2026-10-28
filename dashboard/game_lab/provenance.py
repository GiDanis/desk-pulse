"""Bind experiments to physics, dependency versions and complete datasets."""
from pathlib import Path
import hashlib,json


def source_hashes():
    root=Path(__file__).resolve().parents[1]
    paths=[*root.glob('game*.py'),*root.glob('game*.json'),*root.joinpath('game_lab').glob('*.py'),
        *root.joinpath('game-tracks').rglob('*.json')]
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def contract(*,method,recipe,seed,history,dataset_hash,base_hash,environment):
    import numpy,torch,gymnasium,stable_baselines3
    from game_catalog import configuration
    return dict(version='reference-training-contract-1',method=method,recipe=recipe,seed=seed,history=history,
        datasetHash=dataset_hash,baseHash=base_hash,environment=environment,
        configuration=configuration('oval-1','race-68-v3'),sourceHashes=source_hashes(),
        dependencies=dict(numpy=numpy.__version__,torch=torch.__version__,gymnasium=gymnasium.__version__,sb3=stable_baselines3.__version__))


def verify(value):
    expected=contract(method=value['method'],recipe=value['recipe'],seed=value['seed'],history=value['history'],
        dataset_hash=value['datasetHash'],base_hash=value['baseHash'],environment=value['environment'])
    if value!=expected:raise ValueError('Training source, physics or dependency contract changed')
