"""Full reference learner snapshots at completed update boundaries.

PPO pauses at a completed rollout/update, never discarding a partial rollout.
The separate process may keep serving UI acknowledgements while it reaches
that boundary. This module is not imported by the production GUI.
"""
from pathlib import Path
import gzip,io,hashlib,json,os,pickle,random,shutil,tempfile
import numpy as np
import torch
from game_lab.artifacts import digest

VERSION='reference-learner-checkpoint-1'


def save(model,destination,*,method,contract):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():raise ValueError('Checkpoint is immutable')
    private=Path(tempfile.mkdtemp(prefix='checkpoint-',dir=destination.parent))
    try:
        vec=model.get_env();env=vec.envs[0].unwrapped
        if len(vec.envs)!=1:raise ValueError('Single-learner checkpoint contract')
        rng=dict(python=random.getstate(),numpy=np.random.get_state(),torch=torch.get_rng_state(),
            actionSpace=env.action_space.np_random.bit_generator.state)
        # A skill includes its immutable, large preparation. SB3's generic
        # pretty-printed JSON repeats that base at every pause. Store it once
        # as an exact trusted-local binary object, covered by the manifest.
        # Existing checkpoint files without this optional file still load.
        skill=getattr(model,'_skill',None)
        model.save(private/'model',exclude=['_skill'] if skill else None)
        if skill:
            with (private/'skill.pkl').open('wb') as stream:pickle.dump(skill,stream,protocol=5)
        if method!='ppo':
            with gzip.open(private/'replay.pkl.gz','wb',compresslevel=1) as compressed,io.BufferedWriter(compressed) as stream:model.save_replay_buffer(stream)
        with (private/'state.pkl').open('wb') as stream:
            pickle.dump(dict(environment=env.snapshot(),rng=rng,
                vector={k:getattr(vec,k) for k in ('buf_obs','buf_dones','buf_rews','buf_infos','reset_infos')},
                monitor={k:getattr(vec.envs[0],k) for k in ('rewards','needs_reset','total_steps') if hasattr(vec.envs[0],k)}),stream,protocol=5)
        manifest=dict(version=VERSION,method=method,contract=contract,decisions=model.num_timesteps,
            files={p.name:digest(p) for p in sorted(private.iterdir())})
        (private/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        # The durable pointer is published only after all files are durable.
        for p in private.iterdir():
            with p.open('rb') as stream:os.fsync(stream.fileno())
        fd=os.open(private,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        os.replace(private,destination)
        fd=os.open(destination.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        return manifest
    finally:
        if private.exists():shutil.rmtree(private)


def load(path,environment,*,contract):
    """Load only a trusted local checkpoint with exact contract and hashes."""
    from stable_baselines3 import PPO,SAC,TD3
    from game_lab.reference_learning import CalibratedPPO,CalibratedSAC,CalibratedTD3,install_training_prior
    path=Path(path);manifest=json.loads((path/'manifest.json').read_text())
    if manifest['version']!=VERSION or manifest['contract']!=contract:raise ValueError('Reference checkpoint contract changed')
    for name,sha in manifest['files'].items():
        if Path(name).name!=name or digest(path/name)!=sha:raise ValueError('Reference checkpoint damaged')
    # The saved data records whether the actor has a training-only prior.
    from stable_baselines3.common.save_util import load_from_zip_file
    data,_,_=load_from_zip_file(path/'model.zip',device='cpu')
    calibrated=bool(data.get('_smartpc_prior'))
    method=manifest['method']
    cls=({'ppo':CalibratedPPO,'sac':CalibratedSAC,'td3':CalibratedTD3} if calibrated else {'ppo':PPO,'sac':SAC,'td3':TD3})[method]
    model=cls.load(path/'model.zip',env=environment,device='cpu',force_reset=False)
    if (path/'skill.pkl').is_file():
        if 'skill.pkl' not in manifest['files']:raise ValueError('Unverified skill snapshot')
        with (path/'skill.pkl').open('rb') as stream:model._skill=pickle.load(stream)
    if method!='ppo':
        if (path/'replay.pkl.gz').exists():
            with gzip.open(path/'replay.pkl.gz','rb') as compressed,io.BufferedReader(compressed) as stream:model.load_replay_buffer(stream,truncate_last_traj=False)
        else:model.load_replay_buffer(path/'replay.pkl',truncate_last_traj=False)
    if getattr(model,'_skill',None):
        from game_lab.skills import install_prior
        install_prior(model)
    if calibrated:install_training_prior(model,method,warmup=model._smartpc_prior['warmup'])
    with (path/'state.pkl').open('rb') as stream:state=pickle.load(stream)
    environment.restore(state['environment']);vec=model.get_env()
    for k,v in state['vector'].items():setattr(vec,k,v)
    for k,v in state['monitor'].items():setattr(vec.envs[0],k,v)
    environment.action_space.np_random.bit_generator.state=state['rng']['actionSpace']
    random.setstate(state['rng']['python']);np.random.set_state(state['rng']['numpy']);torch.set_rng_state(state['rng']['torch'])
    return model,manifest
