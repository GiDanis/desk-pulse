"""A0.4 reproducible corpus runner: schema, real legacy Main and future binding status.

Parent orchestration imports no Qt. Each legacy profile gets a bounded child with
private XDG/store/SQLite before QGuiApplication; never operates the kiosk service.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from theme_fixture_support import CORPUS,ROOT,isolate_process,read_corpus


def contract_lane(cases,contract):
    from theme_api_contract import ContractError
    structural=json.loads((CORPUS/'domains/context-structural.json').read_text())
    assert structural['generatedFromApiFingerprint']==contract.fingerprint
    for row in structural['vectors']:contract.validate_snapshot(row['type'],row['snapshot'])
    vectors=json.loads((CORPUS/'domains/semantic-values.json').read_text())['vectors'];results=[]
    for i,row in enumerate(vectors):
        accepted=True
        try:contract.validate_snapshot(row['type'],row['value'])
        except ContractError:accepted=False
        assert accepted==row['accepted'],(i,accepted,row)
        if accepted and 'expectedValue'in row:assert row['value']['value']==row['expectedValue'] and type(row['value']['value'])==type(row['expectedValue'])
        results.append({'id':i,'status':'passed','expectedAccepted':row['accepted']})
    bytype={row['type']:row for row in structural['vectors']}
    coverage=[]
    for case in cases:
        context=contract.surfaces[case['surfaceId']]['context'];assert context in bytype
        contract.validate_snapshot(context,deepcopy(bytype[context]['snapshot']))
        coverage.append({'id':case['id'],'covers':case['covers'],'family':case['family'],'status':'passed','scope':'Context structural validation plus independent numeric/false/null negative vectors; domain semantic assertions are in legacyUi.','publicApiBinding':'deferredA1'})
    return {'status':'passed','contextStructuralVectors':len(structural['vectors']),'semanticVectors':results,'coverage':coverage,'qmlModuleVerified':False}


def child(profile,cases):
    private,base=isolate_process()
    from theme_fixture_support import LegacyHarness
    from PySide6.QtCore import qVersion
    import PySide6
    harness=None;results=[]
    try:
        harness=LegacyHarness(base,profile)
        for case in cases:
            try:results.append(harness.run_case(case))
            except Exception as error:
                results.append({'id':case['id'],'covers':case['covers'],'surfaceId':case['surfaceId'],'family':case['family'],'variant':case['variant'],'status':'failed','error':str(error),'traceback':traceback.format_exc(),'publicApiBinding':'deferredA1'})
                break
        return {'status':'passed' if len(results)==len(cases) and all(x['status']=='passed' for x in results) else 'failed','profile':profile,'qt':qVersion(),'pyside':PySide6.__version__,'backend':os.environ['QT_QPA_PLATFORM'],'renderBackend':os.environ.get('QT_QUICK_BACKEND','Qt default'),'coverage':results,'expectedScenarios':len(cases),'qmlWarnings':harness.messages,'positiveControls':harness.positive_control,'isolation':{'privateXdg':True,'privateStore':True,'privateSQLite':True,'domainClock':'module-local fixed wall time; Qt/monotonic real','transport':'socket.connect denied and positive control observed'},'publicApiBinding':'deferredA1'}
    finally:
        if harness:harness.close()
        private.cleanup()


def execute_child(profile,timeout,selected=None):
    command=[sys.executable,str(Path(__file__).resolve()),'--child',json.dumps(profile)]
    if selected:command+=['--select',selected]
    started=time.monotonic()
    try:result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as error:return {'status':'failed','profile':profile,'error':'bounded child timeout','timeoutSeconds':timeout,'output':str(error.stdout or '')[-6000:]}
    try:report=json.loads(result.stdout)
    except json.JSONDecodeError:report={'status':'failed','profile':profile,'error':'child did not produce JSON','stdout':result.stdout[-10000:],'stderr':result.stderr[-10000:]}
    report['exitCode']=result.returncode;report['elapsedSeconds']=round(time.monotonic()-started,3)
    if result.returncode:report['status']='failed';report.setdefault('stderr',result.stderr[-10000:])
    return report


def coverage_summary(lanes,cases):
    """Supplementary scenarios must never inflate the canonical requirement count."""
    rows=[row for lane in lanes for row in lane.get('coverage',[]) if row['status']=='passed']
    passed={row['id'] for row in rows}
    covered={identifier for row in rows for identifier in row['covers']}
    required={identifier for case in cases for identifier in case['covers']}
    return {'uniqueScenariosPassed':len(passed),
            'uniqueCanonicalRequirementsPassed':len(covered & required),
            'missingScenarios':sorted({case['id'] for case in cases}-passed),
            'missingRequirements':sorted(required-covered)}


REGRESSIONS={
    'check_theme_semantic_residuals.py':['Home next event absent/future/started/expired','midnight/year boundary','partial weather retains complete cache','scene occupied-region collision and actor continuity'],
    'check_dashboard.py':['Home with/without next event','clock boundaries','navigation','offline bulletin recovery','notification settings'],
    'check_theme_ui.py':['real Qt focus','rapid swap/navigation','save failure','scene continuity','two engines'],
    'check_theme_motion.py':['animation interruption','settle','reduced/off','no per-frame Python publication'],
    'check_theme_recovery.py':['missing catalog independent fallback','cold urgent','preserved navigation'],
    'check_notifications.py':['six modes','Unicode long text','preview no DB effects','pending first frame','eight-second deadline','stale callback','renderer error','not-ready timeout','urgent while staging','cancel while loading','cold urgent emergency'],
    'check_theme_persistence.py':['real QSettings atomic apply','save failure','rollback'],
    'check_settings.py':['all menu sections','conditional disabled rows','quiet midnight','thresholds','device readonly'],
    'check_sport_ui.py':['selected ID retention','removed fixture','reordered/round selection','queued previous worker'],
    'check_sport_team_ui.py':['calendar/results/info/squad','picker favourite','SerieA filter','old complete offline data'],
    'check_fantacalcio_ui.py':['votes missing/zero/provisional/history','team route x match','future empty states'],
    'check_motorsport_ui.py':['F1/MotoGP x applicable tabs','driver details/pits/laps/tyres/timing','queued selection','zero/missing honest data'],
    'check_events.py':['source revision order','dedup','seen/dismiss/notified flags','event expiry'],
}

def regression_lane(timeout):
    results=[]
    for script,scope in REGRESSIONS.items():
        started=time.monotonic();command=[sys.executable,str(Path(__file__).resolve()),'--regression-child',script]
        try:
            value=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
            results.append({'script':script,'status':'passed' if value.returncode==0 else 'failed','exitCode':value.returncode,'elapsedSeconds':round(time.monotonic()-started,3),'scope':scope,'stdout':value.stdout[-20000:],'stderr':value.stderr[-20000:],'isolation':'private XDG/config/data/cache/state/store before imports; socket/DNS deny; process exit owns teardown'})
        except subprocess.TimeoutExpired as error:results.append({'script':script,'status':'failed','scope':scope,'error':'bounded regression child timeout','timeoutSeconds':timeout,'stdout':str(error.stdout or '')[-20000:]})
    command=[sys.executable,str(Path(__file__).resolve()),'--fault-child','loading']
    try:
        value=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
        results.append({'script':'fault-child:loading','status':'passed' if value.returncode==0 else 'failed','exitCode':value.returncode,'scope':['real Loader.Loading watchdog','incubation positive control'],'stdout':value.stdout[-20000:],'stderr':value.stderr[-20000:]})
    except subprocess.TimeoutExpired:results.append({'script':'fault-child:loading','status':'failed','error':'bounded loading fault child timeout'})
    return {'status':'passed' if all(x['status']=='passed' for x in results) else 'failed','results':results,'atomicCoverageAttribution':'Regression assertions have their own scopes; suite execution does not fabricate per-requirement legacyUi PASS.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--track',choices=['all','contractData','legacyUi','regressions'],default='all');parser.add_argument('--profiles',help='Comma-separated theme:variant:motion; default full corpus matrix')
    parser.add_argument('--fault-child',choices=['loading']);parser.add_argument('--regressions',action='store_true',help='Also run isolated functional/fault/race regression children');parser.add_argument('--regression-child');parser.add_argument('--output',type=Path);parser.add_argument('--child');parser.add_argument('--select',help='Scenario ID or family, diagnostic subset explicitly reported');parser.add_argument('--timeout',type=float,default=180)
    args=parser.parse_args()
    if args.fault_child:
        private,base=isolate_process()
        from theme_fixture_support import loading_watchdog_lane
        try:result=loading_watchdog_lane(base);print(json.dumps(result))
        finally:private.cleanup()
        return 0
    if args.regression_child:
        private,base=isolate_process()
        # Existing suites own offline/fake-transport transitions; keep DNS/socket denial.
        os.environ.pop('SMARTPC_SPORT_OFFLINE',None);os.environ.pop('SMARTPC_RACING_OFFLINE',None)
        import runpy
        from unittest.mock import patch
        network=[]
        def denied(*a,**kw):network.append('denied');raise RuntimeError('A0.4 regression network denied')
        sys.argv=[str(ROOT/args.regression_child)]
        try:
            with patch('socket.socket.connect',side_effect=denied),patch('socket.getaddrinfo',side_effect=denied):runpy.run_path(str(ROOT/args.regression_child),run_name='__main__')
        finally:private.cleanup()
        return 0
    catalog,cases,contract=read_corpus()
    if args.select:
        cases=[case for case in cases if case['id']==args.select or case['family']==args.select];assert cases,'unknown scenario selection'
    if args.child:
        try:report=child(json.loads(args.child),cases)
        except Exception as error:report={'status':'failed','error':str(error),'traceback':traceback.format_exc(),'profile':json.loads(args.child)}
        print(json.dumps(report,ensure_ascii=False));return 0 if report['status']=='passed' else 1
    report={'reportVersion':1,'corpusVersion':catalog['corpusVersion'],'apiFingerprint':contract.fingerprint,'status':'passed','requiredScenarios':len(contract.documents['surfaces.json']['fixtureRequirements']['requiredCases']),'selectedScenarios':len(cases),'requiredSurfaces':len(contract.surfaces),'requiredFamilies':len(catalog['families']),'tracks':{},'publicApiBinding':{'status':'deferredA1','reason':'Legacy-only lane; real runtime API import and adapter binding are verified separately; no fabricated complete variant-binding PASS'},'scope':'Isolated synthetic legacy UI and contract data; no live provider or physical keypad proof, no GPU time/performance claim.'}
    if args.track in ('all','contractData'):report['tracks']['contractData']=contract_lane(cases,contract)
    if args.track in ('all','legacyUi'):
        if not (CORPUS/'renderers/CanvasScene.qml').is_file():
            parser.error('legacyUi requires source checkout or package built with --diagnostics; production excludes diagnostic renderers')
        profiles=catalog['profiles'] if not args.profiles else [dict(zip(('theme','variant','motion'),value.split(':'))) for value in args.profiles.split(',')]
        for profile in profiles:assert set(profile)=={'theme','variant','motion'} and profile['variant'] in ('day','night') and profile['motion'] in ('normal','reduced','off')
        lanes=[execute_child(profile,args.timeout,args.select) for profile in profiles]
        report['tracks']['legacyUi']={'status':'passed' if all(lane['status']=='passed' for lane in lanes) else 'failed','profiles':lanes,**coverage_summary(lanes,cases)}
    if args.regressions or args.track=='regressions':
        report['tracks']['regressions']=regression_lane(args.timeout)
    report['status']='passed' if all(track['status']=='passed' for track in report['tracks'].values()) else 'failed'
    report['fullProfileMatrixExecuted']=args.track in ('all','legacyUi') and not args.profiles and not args.select
    report['inapplicableCombinations']=catalog.get('inapplicableCombinations',[])
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='passed' else 1

if __name__=='__main__':sys.exit(main())
