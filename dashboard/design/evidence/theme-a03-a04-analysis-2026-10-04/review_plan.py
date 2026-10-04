from pathlib import Path
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parents[4];folder=Path(__file__).resolve().parent
files=[root/'dashboard/design/theme-engine-a03-a04-implementation-analysis.md',folder/'README.md',*(root/'dashboard/design'/name for name in ('release-masterplan.md','theme-engine-a0-a1-implementation-analysis.md','theme-engine-a0-contracts-report.md','theme-engine-ai-execution-plan.md','theme-engine-implementation-guide.md'))]
issues=[];links=0;anchors=0
for source in files:
 for target in re.findall(r'\]\(([^)]+)\)',source.read_text()):
  if '://' in target:continue
  links+=1;parts=target.strip('<>').split('#',1);path=(source.parent/parts[0]).resolve() if parts[0] else source
  if not path.exists():issues.append({'source':str(source.relative_to(root)),'target':target,'reason':'missingFile'});continue
  if len(parts)>1 and path.suffix=='.md':
   anchors+=1;slugs=[];counts={}
   for line in path.read_text().splitlines():
    if not re.match(r'^#{1,6} ',line):continue
    h=re.sub(r'^#{1,6} ','',line).strip().lower();slug=re.sub(r'[^\w\- ]','',h).replace(' ','-')
    n=counts.get(slug,0);counts[slug]=n+1;slugs.append(slug if n==0 else slug+'-'+str(n))
   if parts[1] not in slugs:issues.append({'source':str(source.relative_to(root)),'target':target,'reason':'missingAnchor'})
assert not issues,issues
plan=json.loads((folder/'fixture-plan.json').read_text());cov=plan['canonicalCoverage'];trace=json.loads((folder/'trace-plan.json').read_text());source=json.loads((folder/'source-audit.json').read_text());board=json.loads((folder/'board-baseline.json').read_text())
assert len(cov)==108 and len({c['surfaceId'] for c in cov})==44 and len(plan['families'])==16
assert all(c['executionStatus']=='notExecuted' and c['tracks']['publicApiBinding']=='deferredA1' for c in cov)
assert plan['runtimeImplemented'] is False and trace['runtimeImplemented'] is False
assert source['baselineFilesCompared']==197 and not source['mismatches'] and not board['mismatches']
manifest=json.loads((root/'dashboard/design/evidence/theme-a0-contracts-2026-10-04/installed-manifest.json').read_text())
assert all(hashlib.sha256((root/'dashboard'/name).read_bytes()).hexdigest()==sha for name,sha in manifest['sha256'].items())
changed=subprocess.check_output(['git','diff','--name-only'],cwd=root,text=True).splitlines();new=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=root,text=True).splitlines()
assert all(p.startswith('dashboard/design/') for p in changed+new),changed+new
review={'analysisOnly':True,'localLinksChecked':links,'anchorsChecked':anchors,'issues':issues,'canonicalCasesPlanned':108,'surfacesPlanned':44,'families':16,'runtimeFixtureCasesExecuted':0,'runtimeImplemented':False,'baselineRuntimeFilesUnchanged':197,'apiFingerprintUnchanged':plan['apiFingerprint'],'newBoardPerformanceMeasured':False,'newBoardRuntimeTest':False,'boardRestarted':False,'existingGeneratedContractCheck':'verified with scripts/generate-theme-api-contract.py --check','documentationAndAnalysisFilesOnly':True}
(folder/'analysis-review.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review))
