"""Headless ARM qualification in an isolated home, while dashboard stays up."""
from pathlib import Path
import json,unittest,time
P=Path('/var/lib/smartpc-dashboard/v09-attack-proof');start=time.monotonic()
names=['check_game_attack','check_game_overtaking','check_game_racing_objective','check_game_direct','check_game_menu','check_game_sessions']
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
with (P/'arm-tests.txt').open('w') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
report=dict(status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,seconds=time.monotonic()-start,failures=result.failures,errors=result.errors,productionChanges=False)
(P/'arm-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
raise SystemExit(not result.wasSuccessful())
