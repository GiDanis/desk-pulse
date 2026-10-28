"""ARM supplement for the final epoch fix; retain exact prior GUI evidence."""
from pathlib import Path
import hashlib,json,subprocess,shutil
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-racing-objective-proof'
S=H/'smartpc-racing-final-project/dashboard';old=H/'smartpc-racing-project/dashboard';PY=H/'game-runtime/bin/python'
m=json.loads((S/'release-manifest.json').read_text());prior=json.loads((old/'release-manifest.json').read_text())
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
changed=[n for n,h in m['sha256'].items() if prior['sha256'].get(n)!=h]
assert set(changed)=={'game_direct_trainer.py','game_residual_trainer.py','check_game_racing_objective.py'}
assert json.loads((P/'source-checks.json').read_text())['status']=='passed'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
    'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1',
    'QT_QPA_PLATFORM=offscreen','PYTHONPATH='+str(S)]
with (P/'final-epoch-tests.txt').open('w') as out:
    subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),'-m','unittest',
        'check_game_racing_objective.RacingObjectiveTests.test_tactical_curriculum_counts_new_epoch_not_lifetime',
        'check_game_racing_objective.RacingObjectiveTests.test_traffic_rehearsal_does_not_mask_race_practice',
        'check_game_racing_objective.RacingObjectiveTests.test_migration_preserves_actor_identity_and_exact_qualification',
        '-v'],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=120)
shutil.copy2(P/'source-checks.json',P/'source-checks-before-epoch.json')
receipt=dict(status='passed',sourceHashes=m['sha256'],nativeCases=['base','functional','apple'],
    guiSourceManifest='source-checks-before-epoch.json',finalDeltaFiles=changed,finalDeltaTests='final-epoch-tests.txt',
    scope='Three native GUI cases on preceding epoch counter; final ARM supplement covers migrated/fresh curriculum and persistence. GUI, inference, race and reward files unchanged.')
(P/'source-checks.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Final ARM epoch, rehearsal and migration tests passed; unchanged GUI evidence retained',flush=True)
