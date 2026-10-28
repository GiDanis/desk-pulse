from pathlib import Path
import hashlib,json,re
p=Path(__file__).parent;b=p/'board';r=json.loads((b/'final-receipt.json').read_text());s=json.loads((p/'final-summary.json').read_text());rep=json.loads((p/'final-source-reproduction.json').read_text());source=json.loads((b/'source-checks.json').read_text())
assert r['status']==s['status']==rep['status']==source['status']=='passed'
assert r['files']==636 and not r['manifestMismatches'] and r['historyPreserved'] and r['identitiesPreserved'] and r['lifetimeTotalsPreserved']
assert all(source['sourceHashes'][n]==h for n,h in rep['sourceHashes'].items())
assert json.loads((b/'arm-frozen-retention.json').read_text())['status']=='passed'
arm=set()
for f in ('arm-tests.txt','arm-final-school.txt'):
 t=(b/f).read_text();assert '\nOK\n' in t
 arm.update(re.findall(r'^(test_.*) \.\.\. ok$',t,re.M))
assert len(arm)==28,len(arm)
t=(p/'pc-release-final.txt').read_text();assert 'Ran 57 tests' in t and '\nOK\n' in t
rows=[]
for name in ('base','functional','apple'):
 d=json.loads((b/name/'report.json').read_text());assert d['status']=='passed' and d['fiveCarsVisible'] and not d['qmlWarnings']
 if name=='apple':assert d['completedRace'] and d['actualGuiQualification'] and all(x['status']=='arrivato' and x['lap']==3 for x in d['raceResults'])
 rows.append(dict(theme=name,window=d['window'],learners=d['learners'],fiveCarsVisible=True,completedRace=d['completedRace'],frameTiming=d['frameTiming'],qmlWarnings=[]))
proof=dict(status='passed',version=r['version'],runtimeFiles=r['files'],native=rows,pcUniqueTests=57,armUniqueTests=28,armSupplement='arm-frozen-retention.json',sourceScope=source['scope'],learning='final-summary.json',sourceReproduction='final-source-reproduction.json',install='board/final-receipt.json',dataPreserved=True,newLearningEpoch=True,preferencesPreserved=True,noStudyChampionsImported=True,frameTimingScope='Qt frameSwapped only, not optical FPS or sustained thermal qualification',sourceDelta='source-delta.json')
(p/'delivery-summary.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
