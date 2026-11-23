"""Effective, weight-free learning descriptor shared by persistence and UI."""
from game_profiles import METHODS,variant


def effective(profile,learner,reward):
    method=profile['algorithm'];recipe=variant(profile)
    result=dict(version='effective-training-1',method=method,
        methodLabel=METHODS[method][1],variant=profile.get('variant'),
        variantLabel=recipe.get('name','Standard'),recipeVersion=profile.get('recipeVersion'),seed=profile['seed'],
        population=profile['population'],observation=profile['observation'],
        reward=reward,physicsHz=60,backend=type(learner).__name__,
        meaning='Candidates per generation' if method in ('evolution','neat') else 'Environment copies')
    if method=='neat':
        g=learner.config.genome_config
        result['network']=dict(kind='feed-forward NEAT',activation='tanh(2.5*z)',
            initialConnections=g.initial_connection,numInputs=g.num_inputs,
            weightSigma=learner.tuning['weightInit'],biasSigma=learner.tuning['biasInit'],
            mutationSigma=learner.tuning['mutationPower'],responseInit=learner.tuning['responseInit'],
            nodeAdd=g.node_add_prob,connectionAdd=g.conn_add_prob)
    else:result['network']=dict(kind='dense',hidden=profile['hidden'])
    if method in ('ppo','ppo_smooth','clone_ppo'):
        result['ppo']=dict(gamma=profile['gamma'],**learner.tuning,
            learningRate=profile['learningRate'],rollout=profile['rollout'],
            transitionsPerUpdate=profile['rollout']*profile['population'],epochs=profile['epochs'])
    if method in ('imitation','clone_ppo'):
        teacher=getattr(learner,'teacher',learner)
        result['teacher']=dict(controller='traffic-pursuit-2',replay=8192,batch=128,
            labels=getattr(teacher,'teacher_spec',None),actions='learner only')
    if method=='clone_ppo':result['recipe']=dict(version=learner.hybrid['version'],phase=learner.phase)
    if method=='ppo_smooth' or profile.get('variant')=='regular':
        result['smooth']='squared command versus current physical steering; not lap-time variance'
    return result
