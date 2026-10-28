"""Private extended learning comparison; no production registry or board access."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'


def run(job):
    source, label, method, seed, budget, extend, directory = job
    sys.path.insert(0, source)
    from game_academy import Episode, academy_profile
    from game_academy_trainer import AcademyTrainer
    from game_evo_plan import stage_scenario
    from game_learning import Policy
    from game_profiles import preset
    p = academy_profile(preset(seed, method))
    checkpoint_path = Path('/tmp/smartpc-pilot-improvement-checkpoints') / label / f'{method}-{seed}.json'
    saved = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
    t = AcademyTrainer(p, 'oval-1', saved, balanced=True, batched=True)
    prior_seconds = (saved or {}).get('seconds', 0.)
    start = time.monotonic()
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    private = Path('/tmp/smartpc-pilot-improvement-checkpoints') / label
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    results = []
    for target in (budget, extend):
        if not target or target <= t.steps:
            continue
        while t.steps < target:
            t.tick()
        policy = Policy(t.learner.candidate_policy() if hasattr(t.learner, 'candidate_policy') else t.learner.policy())
        held = []
        for level in (3, 5, 7, 10):
            for case in range(4):
                scenario_seed = 10400100 + case
                scenario = stage_scenario('oval-1', level, scenario_seed)
                e = Episode('oval-1', scenario['phase'], scenario_seed,
                    protocol='driving-memory-1', scenario=scenario, single_lap=True)
                e.world.native_sensors = True
                while not e.reason:
                    e.step(policy.act(e.observations(), world=e.world, index=0))
                held.append(dict(level=level, reason=e.reason, meters=e.valid_progress,
                    seconds=e.age, cleanLaps=int(e.world.clean_laps[0])))
        row = dict(label=label, method=method, seed=seed, profile=p,
            transitions=t.steps, wallSeconds=prior_seconds+time.monotonic()-start,
            stage=t.evo_plan.data['level'], updates=t.state['updates'],
            hybridPhase=getattr(t.learner,'phase',None),hybridProof=t.state.get('hybridProof'),
            hybridEvaluationSteps=t.state.get('hybridEvaluationSteps',0),
            evaluationSteps=t.evo_plan.data.get('evaluationSteps', 0),
            evaluationSeconds=t.state.get('evaluationSeconds', 0), held=held,
            extensionRule='extend from 1M to 3M iff stage >= 6 or at least one held lap succeeds',
            classification='private learning evidence; not a production qualification or board throughput')
        results.append(row)
        (output / f'{label}-{method}-{seed}-{target}.json').write_text(json.dumps(row, indent=2)+'\n')
        checkpoint = private / f'{method}-{seed}.json'
        checkpoint.write_text(json.dumps(t.checkpoint(prior_seconds+time.monotonic()-start)))
        checkpoint.chmod(0o600)
        print(json.dumps({k: row[k] for k in ('label','method','seed','transitions','stage','wallSeconds')}), flush=True)
        if target == budget and row['stage'] < 6 and not any(r['level']==10 and r['reason']=='success' for r in held):
            break
    t.close()
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--budget', type=int, default=1000000)
    parser.add_argument('--extend', type=int, default=3000000)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--methods', nargs='+', default=['evolution','neat','ppo','ppo_smooth','imitation'])
    parser.add_argument('--seeds', nargs='+', type=int, default=[1,2,3,4,5])
    args = parser.parse_args()
    jobs = [(str(Path(args.source).resolve()), args.label, method, seed, args.budget,
        args.extend, str(Path(__file__).parent)) for method in args.methods for seed in args.seeds]
    with concurrent.futures.ProcessPoolExecutor(args.workers) as pool:
        for result in pool.map(run, jobs):
            pass
