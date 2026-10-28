from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent;b=p/'board';r=json.loads((b/'final-receipt.json').read_text());assert r['status']=='passed'
rows=[]
for name in ('base','functional','apple'):
 d=json.loads((b/name/'report.json').read_text());assert d['status']=='passed' and d['fiveCarsVisible'] and not d['qmlWarnings']
 assert all(x['control']=='direct' and x['policyKind']=='direct' and x['decisions']>512 for x in d['learners'])
 row=dict(theme=name,window=d['window'],learners=d['learners'],fiveCarsVisible=d['fiveCarsVisible'],completedRace=d['completedRace'],frameTiming=d['frameTiming'],qmlWarnings=d['qmlWarnings'])
 if name=='apple':
  assert d['completedRace'] and d['actualGuiQualification'] and all(x['status']=='arrivato' and x['lap']==3 for x in d['raceResults'])
  row['finishTimes']=[dict(id=x['id'],seconds=x['finishTime'],lap=x['lap'],status=x['status']) for x in d['raceResults']]
 rows.append(row)
source=json.loads((b/'source-checks.json').read_text());assert source['status']=='passed'
rep=json.loads((p/'final-source-reproduction.json').read_text());assert all(source['sourceHashes'][n]==h for n,h in rep['sourceHashes'].items())
assert r['files']==632 and not r['manifestMismatches'] and r['preferencesPreserved'] and r['liveGuiPidVerified']
assert all(x['steps']==0 and x['seconds']==0 and x['checkpoint'] is None for x in r['newGame']['drivers'])
proof=dict(status='passed',version=r['version'],runtimeFiles=r['files'],native=rows,learning='final-summary.json',sourceReproduction='final-source-reproduction.json',install='board/final-receipt.json',pcTests=45,armTests=16,resetVerified=True,preferencesPreserved=True,frameTimingScope='Qt frameSwapped, short races, not optical FPS or sustained thermals',sourceDelta='source-delta.json')
(p/'delivery-summary.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(status=proof['status'],version=proof['version'],files=proof['runtimeFiles'],native=[dict(theme=x['theme'],completedRace=x['completedRace'],frameTiming=x['frameTiming']) for x in rows]),indent=2))
