from pathlib import Path
import json,hashlib,ast,sys,math
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
sys.path.insert(0,str(root));from theme_api_contract import ThemeApiContract
c=ThemeApiContract(root);required=c.surfaces_document['fixtureRequirements']['requiredCases']
write=lambda name,value:(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
installed=json.loads((root/'design/evidence/theme-a0-contracts-2026-10-04/installed-manifest.json').read_text())
sha={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in installed['sha256']}
assert sha==installed['sha256']
files=['app.py','keypad.py','theme_service.py','theme_core.py','Main.qml','components/ViewHost.qml','components/NotificationHost.qml','components/SceneHost.qml','components/AnimatedLayer.qml','components/NotificationPreview.qml','components/MotionController.qml','motion/FadeRecipe.qml','motion/SlideRecipe.qml','theme_test_support.py','verify_notifications_board.py','events.py','event_core.py','state.py','system_info.py','check_notifications.py']
records=[]
for name in files:
 p=root/name;row={'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'lines':len(p.read_text().splitlines())}
 if p.suffix=='.py':
  row['functions']=[{'name':n.name,'line':n.lineno,'endLine':n.end_lineno} for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
 else:row['hooks']=[{'line':i,'text':s.strip()} for i,s in enumerate(p.read_text().splitlines(),1) if any(t in s for t in ('function commit','function prepare','function ready','function fail','onAfterAnimating:','onFrameSwapped:','onAppearanceChanged:','function play','function settle','onLoaded:','asynchronous:','onStopped:'))]
 records.append(row)
write('source-audit.json',{'analysisOnly':True,'sourceCommit':'f67a5af04014b2f14562ead409eeb1d2b63309ea','installedCodeCommit':installed['gitCommit'],'baselineFilesCompared':len(sha),'mismatches':[],'api':c.metadata(),'sourceCoverage':c.check_source_coverage(),'files':records})
legacy=[]
for name in ('stress-presets','stress-fonts'):
 p=root/('design/evidence/notification-engine-migration/eglfs/'+name+'/report.json');r=json.loads(p.read_text());values=[x['ms'] for x in r['themeFrames']]
 p95=lambda vals:round(sorted(vals)[int((len(vals)-1)*.95)],3)
 assert p95(values)==r['requestToThemeFrameMs']['p95']
 warm=[x['ms'] for x in r['themeFrames'] if x['swap']>6];assert p95(warm)==r['requestToThemeFrameMs']['warmP95']
 legacy.append({'profile':name,'report':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'historicalSamples':len(values),'requestToThemeFrameMs':r['requestToThemeFrameMs'],'prepareMs':r['prepareMs'],'memoryMiB':r['memoryMiB'],'recomputedP95':p95(values),'legacyWarmAfterSixSamples':len(warm),'legacyWarmRule':'swap > 6; not first-use-per-mode/renderer exclusion','warmIntervalRule':'firstUseOfModeAndTheme == false','legacyStatistic':'floor((n-1)*q), q=0.95; no interpolation','historicalGateResidualMs':round(r['requestToThemeFrameMs']['p95']-150,3),'revisionOfEachHostVerified':False,'newPerformanceMeasurement':False})
write('historical-baseline-review.json',{'analysisOnly':True,'profiles':legacy,'notes':['prepareMs measures synchronous selectDraft duration, including validation/resolve and synchronous signal propagation; not full host preparation','SceneHost is outside ThemeService requiredContents; no scene per-revision acknowledgement','Render-thread/GUI-thread association must be prototyped, not inferred from callback arrival']})
families={
 'home':{'existing':['check_dashboard.py','check_theme_ui.py'],'seeds':[],'mustCover':['with/without next event','zero weather','clock boundary','no reserved empty card']},
 'weather':{'existing':['check_dashboard.py'],'seeds':[],'mustCover':['zero precipitation and temperature','unavailable/partial forecast','offline old complete data','raw numeric values API binding deferred A1']},
 'account':{'existing':['check_dashboard.py','check_notifications.py'],'seeds':[],'mustCover':['zero usage','missing credits','many windows/scroll','threshold warning/critical','no false freshness']},
 'shell':{'existing':['check_dashboard.py','check_theme_ui.py','check_theme_recovery.py'],'seeds':[],'mustCover':['page/overlay/night/urgent/recovery','inputOwner focus','module disappears','legacy layout observer, no ShellHost yet']},
 'general':{'existing':['check_dashboard.py','check_settings.py'],'seeds':[],'mustCover':['first-run/manual commands','menu option identity','summary oggi/meteo','stack retention']},
 'settings':{'existing':['check_settings.py','check_theme_persistence.py','check_theme_authoring_ui.py'],'seeds':[],'mustCover':['all 13 canonical sections','conditional/disabled row identity','draft/preview/cancel/save failure','cooldowns and quiet midnight','racing kind-qualified rows']},
 'device':{'existing':['check_settings.py'],'seeds':[],'mustCover':['4 tabs','missing OS/network values','visible system timer allowed baseline','read-only info']},
 'sport-overview':{'existing':['check_sport_ui.py'],'seeds':['fixtures/sport-normalized-sample.json'],'mustCover':['all four views','removed selected match','zero scores versus missing','reordered list keeps ID']},
 'sport-list':{'existing':['check_sport_ui.py'],'seeds':['fixtures/sport-normalized-sample.json'],'mustCover':['round/favourite','empty/partial standings','row beyond first viewport']},
 'sport-match':{'existing':['check_sport_ui.py','check_fantacalcio_ui.py'],'seeds':['fixtures/sport-fotmob-detail-sample.json','fixtures/fantacalcio-fotmob-roma-inter.json','fixtures/fantacalcio-2026-27-5-roma-inter.html'],'mustCover':['scheduled/live/finished x applicable tab','team route x detail','votes missing/zero/provisional/history','provider counters']},
 'team':{'existing':['check_sport_team_ui.py'],'seeds':['fixtures/sport-team-inter.json'],'mustCover':['no favourite','calendar/results/info/squad','Serie A filtering','partial data','selected ID removed/reordered']},
 'team-picker':{'existing':['check_sport_team_ui.py'],'seeds':['fixtures/sport-team-inter.json'],'mustCover':['none/selected','no automatic favourite change on swap']},
 'racing':{'existing':['check_motorsport_ui.py'],'seeds':['fixtures/racing-f1-normalized.json','fixtures/racing-motogp-normalized.json'],'mustCover':['f1 x applicable tab; motogp x applicable tab','zero delta versus missing','session/event selection retained','unsupported data honest fallback','incompatible tab combinations explicit']},
 'racing-driver':{'existing':['check_motorsport_ui.py'],'seeds':['fixtures/racing-openf1-details.json','fixtures/racing-motogp-normalized.json'],'mustCover':['details/pits/laps/tyres/live for applicable kind','absent fields not fabricated','removed driver','worker completion for previous selection']},
 'notifications':{'existing':['check_notifications.py','check_events.py','check_theme_authoring_ui.py'],'seeds':[],'mustCover':['all six modes','weather/account/sport/generic sources','zero unread versus empty','unknown/stale source','event id/revision/rank','pending first frame and eight-second deadline','no preview DB writes','Unicode/long text','urgent during load/save/preview/cancel']},
 'scene':{'existing':['check_theme_ui.py','check_theme_motion.py'],'seeds':[],'mustCover':['actor/canvas/enabled=false','normal/reduced/off/suspended/occupied regions','actor QObject identity','sequence allowed locomotion increments','SceneHost non-transactional load observation','no definitive companion format limitation']}}
def family(row):
 i=row['id'];ctx=row['context']
 if i=='shell.main':return 'shell'
 if i=='scene.main':return 'scene'
 if ctx=='NotificationContext':return 'notifications'
 if ctx=='SettingsContext':return 'settings'
 if ctx=='InfoContext':return 'device'
 if ctx=='DriverContext':return 'racing-driver'
 if ctx=='TeamPickerContext':return 'team-picker'
 if ctx=='TeamContext' or i=='sport.team':return 'team'
 if ctx=='MatchContext':return 'sport-match'
 if ctx=='SportListContext':return 'sport-list'
 if ctx=='RacingContext' or i=='racing.overview':return 'racing'
 if i=='sport.overview':return 'sport-overview'
 if i.startswith('home.'):return 'home'
 if i.startswith('weather.'):return 'weather'
 if i=='account.usage':return 'account'
 return 'general'
coverage=[]
for case in required:
 row=c.surfaces[case['surfaceId']];f=family(row)
 coverage.append({'requirementId':case['id'],'surfaceId':row['id'],'variant':case['variant'],'scenarioFamily':f,'legacySource':row['legacySource'],'legacyRoute':row.get('legacyRoute'),'tracks':{'contractData':'planned','legacyUi':'planned','publicApiBinding':'deferredA1'},'executionStatus':'notExecuted','atomicLabelIsNotFullCombinationCoverage':True})
assert len(coverage)==108 and len({r['surfaceId'] for r in coverage})==44
for f in families.values():
 for path in f['existing']+f['seeds']:assert (root/path).is_file(),path
write('fixture-plan.json',{'planVersion':1,'analysisOnly':True,'apiFingerprint':c.fingerprint,'status':'proposedNotRuntimeFixtures','families':families,'canonicalCoverage':coverage,'requiredTrackDistinction':['contractData (schema-valid and schema-negative vectors)','legacyUi (current Base views/routes plus state/effects oracle)','publicApiBinding (deferred until real module/hosts in A1)'],'profileMatrix':{'themes':['base','functional'],'variants':['day','night'],'motion':['normal','reduced','off'],'constraints':'All canonical atoms once; every surface across six variant/motion pairs on Base; Functional verticals and risk pairs; explicit valid domain/tab products. Conflicting scene/motion cases split into coherent scenarios; never silent skip.'},'crossProductsRequired':['racing kind x supported tab','sport status x applicable detail tab x direct/team route','six notification surfaces x variant x motion','source status x hasData x isStale with meaningful constraints','selected ID retained/reordered/removed x theme swap/refresh/supersession'],'proposedScenarioFormat':{'scenarioId':'string','covers':'requirement IDs','clock':'fixed epoch + relative monotonic offsets','legacyInput':'fixture references + explicit normalization','contractSnapshot':'optional typed contract vectors; no pretend live QObject','given':'domain/navigation/event/actor state','when':'ordered actions and deterministic causal barriers','then':'state/effect/frame/geometry assertions','allowedEffects':'tagged userAction/providerResult/timer only','profiles':'valid matrix','requiredCapabilities':'current or deferredA1','expectedFaults':'bounded injected failure identity','verification':'per-track/per-backend status; planned is never PASS'},'runtimeImplemented':False})
write('trace-plan.json',{'planVersion':1,'analysisOnly':True,'status':'proposedNotImplemented','clock':'process-local time.perf_counter_ns offset from session start; no Date.now duration','recordVersion':1,'correlationKeys':['sessionId','traceRequestId','operation','attemptId','serviceGeneration','appearanceRevision','hostInstanceId','localGeneration','frameSerial','surfaceId','rendererIdentity','eventId/eventRevision/rank'],'transactionOutcomes':['coherentSubmission','noVisualChange','rejected','superseded','cancelled','failed','timeout','recoveryFallback','unobservedFrame'],'phases':['request','configValidation','resolvedData(cache hit/miss)','catalogValidation/contrast/assets','fontAcquire/cacheRetire','imageHeaderCheck','candidateAnnounced','hostPrepare','loaderReady','presentationReady','candidateReport','snapshotPublish','hostCommitOrReuse','guiFrameSnapshot','sceneSynchronized','frameQueued','motionStoppedOrSettled','saveBegin/saveEnd','export'],'frameProtocol':['GUI afterAnimating captures immutable visible/mandatory participant signature, including inline shell/overlay observers','afterSynchronizing direct callback only latches already-copied primitive snapshot/frame serial; never touches QML/GUI/provider','frameSwapped direct callback stores local monotonic timestamp and matching sync serial; queued delivery carries frozen record','GUI consumer classifies snapshot/revision/visibility and expected frozen exits; old/new callbacks cannot be relabelled from current mutable state','prototype required on Qt 6.8.2 / PySide6 6.8.2.1 EGLFS and Qt 6.11; ambiguous/unmatched records remain unobserved; no fallback PASS'],'timestampQuality':'Python direct-callback entry includes any GIL acquisition delay; quantify in prototype, use calibrated native emitter timestamp if required; never assert zero observation delay','proofScope':'sampled Qt state correlated with scene synchronization/presentation submission; not general pixel verification, GPU time or optical response','boundedBuffer':{'maxEvents':16384,'payloadBytesLimit':8388608,'maxOpenRequests':16,'overflow':'recordsDropped count + invalid measurement; no success from missing records','disabled':'no allocations of records, serialization or frame subscriptions'},'legacyMetricsPreserved':['requestToThemeFrameMs','warmP95 rule swap > 6','frame interval first requested (mode,theme) warm rule','prepareMs legacy synchronous call duration'],'newMetrics':['inputToCoherentSubmissionMs (explicit causal input parent; historical setter metric separate)','requestToCoherentSubmissionMs','mandatoryParticipantsCommittedMs','requestToMotionSettledFrameMs','requestToPersistedMs','notificationIdRevisionRankToSubmissionMs','GUI event recording cost','render callback recording cost'],'performanceTarget':{'coherentSubmissionP95Ms':150,'ordinaryFrameWindowP95Ms':20,'thresholdsAreUnchanged':True,'A03MayCloseWithExplicitResidual':True,'timeoutsAndMissingFramesMustBeReported':True},'initialDiagnosticOverheadTargets':{'recordingCostPerRequestP95Ms':1,'extraDiagnosticPssMiB':8,'acceptance':'proposals to verify with paired trace off/on runs; inconclusive jitter reported, no automatic threshold expansion'},'runtimeImplemented':False})
print(json.dumps({'surfaces':len(c.surfaces),'canonicalCasesPlanned':len(coverage),'scenarioFamilies':len(families),'runtimeImplemented':False,'baselineFilesCompared':len(sha)}))
