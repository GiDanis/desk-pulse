"""Private state-transfer diagnosis, without GameStore or production writes."""
from pathlib import Path
import sys,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'dashboard'))
from game_residual_trainer import ResidualTrainer
from game_residual import profile
from game_academy import Episode
from game_rewards import specification


def main():
    p=profile(77,'residual_sac');a=ResidualTrainer(p,'oval-1')
    while a.decisions<80:a.tick()
    c=a.checkpoint(0);b=ResidualTrainer(p,'oval-1',c,objective='impara_sorpasso')
    assert a.learner.count==b.learner.count==80;np.testing.assert_array_equal(a.learner.actor,b.learner.actor)
    e=Episode('oval-1','corner',95203,protocol='driving-memory-1',reward_spec=specification(p))
    drill=e.reward_spec['drillProgress']/e.spec['distance'];continuous=e.reward_spec['progressPerLap']/e.world.track.length
    result=dict(kind='private-mode-transfer-diagnosis',method='residual_sac',decisions=80,oldObjective=a.objective,newObjective=b.objective,replayRetained=b.learner.count,actorUnchanged=True,
        finiteProgressRewardPerMeter=drill,continuousProgressRewardPerMeter=continuous,scaleRatio=drill/continuous,finiteSuccessBonus=e.reward_spec['drillSuccess'],
        finiteFailurePenalty=-1.,continuousCollectionWindowHasFailurePenalty=False,observationIncludesGoalOrMode=False,productionWrites=0,notAConvergenceTest=True)
    Path(__file__).with_name('mode-transfer.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
