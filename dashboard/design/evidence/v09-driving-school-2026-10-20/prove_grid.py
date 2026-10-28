from pathlib import Path
import json
from game_school_lessons import make_check
from game_direct_bootstrap import direct_profile,initial_policy
P=Path('/var/lib/smartpc-dashboard/v09-school-proof');bad=json.loads((P/'known-fast-regression.json').read_text());base=initial_policy(direct_profile(4,'residual_td3'))
check=make_check(bad,base,'oval-1');ticks=0
while not check.tick():ticks+=1
result=check.result();assert not result['accepted'] and result['decision']=='grid_regression',result
assert result['candidate']['valid']==3 and all(x['candidate']['demonstrated'] for x in result['school'])
assert any(x['candidate']['reason']!='success' or x['candidate']['limits']>x['champion']['limits'] for x in result['gridRetention'])
(P/'arm-frozen-retention.json').write_text(json.dumps(dict(status='passed',case='Real frozen fast Linea passes solo and lessons, rejected for five-car retention',ticks=ticks,evaluation=result),indent=2)+'\n')
print('Frozen unsafe improvement correctly rejected',flush=True)
