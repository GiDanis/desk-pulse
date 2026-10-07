"""Private A0.4 fixture support. Import after isolate_process(), before any QObject.

This module does not register SmartPC.ThemeApi; the legacy runner loads real Main.
Domain wall clocks are module-local proxies; Qt and perf_counter remain real.
"""
from copy import deepcopy
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
CORPUS=ROOT/'fixtures/theme-runtime'


def isolate_process():
    """All settings, cache, state, transfers and DB are private before Qt imports."""
    private=tempfile.TemporaryDirectory(prefix='smartpc-runtime-fixture-')
    base=Path(private.name).resolve()
    for key,name in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:
        os.environ[key]=str(base/name);(base/name).mkdir()
    os.environ['STATE_DIRECTORY']=str(base/'state')
    os.environ['SMARTPC_THEME_STORE']=str(base/'themes')
    os.environ['SMARTPC_SPORT_OFFLINE']='1';os.environ['SMARTPC_RACING_OFFLINE']='1'
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')
    # An inherited kiosk account path must never be observed by fixture processes.
    for key in ['SMARTPC_ACCOUNT_PATH','SMARTPC_ACCOUNT_SNAPSHOT','SMARTPC_THEME_TRACE_OUTPUT']:
        os.environ.pop(key,None)
    assert not str(base).startswith(('/opt/smartpc','/var/lib/smartpc'))
    return private,base


def read_corpus():
    catalog=json.loads((CORPUS/'catalog.json').read_text())
    from theme_api_contract import ThemeApiContract
    contract=ThemeApiContract()
    assert catalog['apiFingerprint']==contract.fingerprint,'stale corpus fingerprint'
    requirements={r['id'] for r in contract.documents['surfaces.json']['fixtureRequirements']['requiredCases']}
    cases=[]
    for row in catalog['scenarios']:
        file=(CORPUS/row['file']).resolve();assert file.is_relative_to(CORPUS.resolve())
        assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256'],'scenario digest mismatch: '+row['id']
        data=json.loads(file.read_text());assert data['id']==row['id'] and data['covers']==row['covers']
        assert data['publicApiBinding']=='deferredA1';cases.append(data)
    actual=[x for row in cases for x in row['covers']]
    assert len(actual)==len(set(actual)) and set(actual)==requirements,'coverage stale/missing/duplicated'
    assert {x['family'] for x in cases}==set(catalog['families'])
    for name,digest in catalog.get('seedInputs',{}).items():
        assert hashlib.sha256((ROOT/'fixtures'/name).read_bytes()).hexdigest()==digest,'seed digest mismatch: '+name
    for name,digest in catalog['domainInputs'].items():
        assert hashlib.sha256((CORPUS/name).read_bytes()).hexdigest()==digest,'domain digest mismatch: '+name
    for name,digest in catalog.get('rendererInputs',{}).items():
        file=(CORPUS/name).resolve();assert file.is_relative_to(CORPUS.resolve()),'renderer path escapes corpus'
        # Production deliberately omits these files. The legacy track separately
        # requires the diagnostic renderer, while contractData remains usable there.
        if file.exists():
            assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==digest,'renderer digest mismatch: '+name
    return catalog,cases,contract


class LegacyHarness:
    """Real Main/ThemeService and seeded domain services with denied network."""
    KEPT=('familyId','viewIndex','overlay','overlayStack','menuIndex','settingsIndex','optionIndex','infoPage','infoIndex','sportView','sportMatchId','sportIndex','sportFocusedId','sportDetailPage','sportDetailOffset','sportTeamDetail','teamTab','teamIndex','teamFocusedId','teamPickerIndex','teamSerieAOnly','fantasyTeamIndex','fantasyPlayerIndex','racingViewNames','racingEventId','racingSessionId','racingDriverId','racingDriverLive','racingDriverPage','racingIndex','racingFocusedId','racingDetailPage','racingEventPage','racingInfoIndex','racingTimingPage','racingStandingTab','racingSettingsKind','alertIndex','alertFocusedId','alertScroll','selectedAlert')
    def __init__(self,base,profile):
        from PySide6.QtCore import QObject,Property,Signal,Slot,QSettings,QUrl,QDateTime,qInstallMessageHandler
        from PySide6.QtGui import QGuiApplication,QWindow
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow
        import shiboken6
        import sport,sport_team,motorsport,events as events_module,event_core
        from state import DashboardState
        from events import EventService
        from sport_team_core import parse_team
        from weather import normalize_response
        self.base=base;self.profile=profile;self.messages=[];self.effects={};self.transport=[];self.stack=ExitStack()
        self.app=QGuiApplication([]);self.app.setOrganizationName('SmartPC');self.app.setApplicationName('Dashboard')
        self.previous_handler=qInstallMessageHandler(lambda kind,context,message:self.messages.append(message))
        # Deny every new socket connection; a positive control proves this guard runs.
        def denied(*args,**kwargs):
            self.transport.append('socket.connect');raise RuntimeError('A0.4 fixture network denied')
        self.stack.enter_context(patch('socket.socket.connect',side_effect=denied))
        self.stack.enter_context(patch('socket.getaddrinfo',side_effect=denied))
        import socket
        try:socket.socket().connect(('127.0.0.1',1))
        except RuntimeError:pass
        assert self.transport==['socket.connect'];self.transport.clear()
        self.now=1790848800.0
        proxy=SimpleNamespace(**{name:getattr(time,name) for name in dir(time) if not name.startswith('__')});proxy.time=lambda:self.now
        for module in (sport,sport_team,motorsport,events_module,event_core):self.stack.enter_context(patch.object(module,'time',proxy))
        class Snapshot(QObject):
            changed=Signal()
            def __init__(obj,data):super().__init__();obj.value=data
            @Property('QVariantMap',notify=changed)
            def moduleState(obj):return obj.value
        class System(QObject):
            changed=Signal()
            def __init__(obj):super().__init__();obj.monitor=False
            @Property('QVariantMap',notify=changed)
            def data(obj):return {'version':'fixture','qt':'fixture','display':'960×640','network':'Non disponibile','ip':'','os':'','model':'Synthetic isolated board'}
            @Property(float,notify=changed)
            def updatedAt(obj):return self.now
            @Slot(bool)
            def setMonitoring(obj,enabled):obj.monitor=enabled
            @Slot()
            def refresh(obj):pass
        source=json.loads((CORPUS/'domains/weather-zero.json').read_text())
        actual=normalize_response(source['raw'])
        for key,value in source['expectedLegacy'].items():assert actual[key]==value,(key,actual[key],value)
        self.weather=Snapshot({'status':'active','source':'Open-Meteo fixture','updatedAt':self.now,'error':'','data':actual})
        self.account=Snapshot({'status':'active','source':'Account fixture','updatedAt':self.now,'error':'','data':{'plan':'Fixture','credits':None,'windows':[{'name':'5 ore','usedPercent':0,'remainingPercent':100,'resetAt':self.now+3600,'durationMins':300}]}})
        self.system=System()
        seed=json.loads((ROOT/'fixtures/sport-normalized-sample.json').read_text());seed['fetchedAt']=seed['standingsFetchedAt']=self.now
        QSettings('SmartPC','Dashboard').setValue('sport/season',seed['season'])
        self.sport=sport.SportService(auto_refresh=False,cache_path=base/'cache/sport.json',state_path=base/'state/goals.json',initial=seed,verified=False)
        self.sport._offline=True;self.sport._age_timer.stop()
        self.sport._team.offline=True
        self.seed=deepcopy(seed)
        self.team=parse_team(json.loads((ROOT/'fixtures/sport-team-inter.json').read_text()),'8636','inter',self.now)
        self.racing={}
        for kind in ('f1','motogp'):
            data=json.loads((ROOT/('fixtures/racing-'+kind+'-normalized.json')).read_text())['snapshot']
            service=motorsport.MotorsportService(kind,auto_refresh=False,cache_directory=base/'cache',initial=data)
            service._offline=True;service._age.stop() if hasattr(service,'_age') else None
            self.racing[kind]=service
        self.events=EventService(path=base/'state/events.sqlite3',auto_refresh=False);self.events._tick_timer.stop()
        from casa import CasaService
        self.casa=CasaService(auto_refresh=False,demo=True,clock=lambda:self.now)
        from network import NetworkService
        self.network=NetworkService(auto_refresh=False,demo=True,clock=lambda:self.now)
        self.state=DashboardState(self.weather,self.system,self.account,self.events,sport=self.sport,racing=self.racing,casa=self.casa,network=self.network)
        self.state.markCommandsSeen();self.state._quiet_enabled=False;self.events.set_quiet(False,0,1)
        self.state._night_mode=profile['variant'];self.state._brightness_mode='manual';self.state._manual_brightness=100
        self.service=self.state.appearance
        self.service.catalog.scene_renderers['fixture.canvas']={'file':'fixtures/theme-runtime/renderers/CanvasScene.qml','apiVersion':1,'sceneMode':'canvas','respectsOccupiedRegions':True}
        self.service._resolved_cache.clear()
        self.service.beginEdit();assert self.service.selectDraft(profile['theme'])
        assert self.service.setSection('paletteMode',profile['variant']);assert self.service.setSection('motionMode',profile['motion'])
        self.engine=QQmlApplicationEngine();self.engine.setInitialProperties({'dashboardState':self.state});self.engine.load(QUrl.fromLocalFile(str(ROOT/'Main.qml')))
        assert self.engine.rootObjects(),self.messages
        self.root=self.engine.rootObjects()[0];self.window=shiboken6.wrapInstance(shiboken6.getCppPointer(self.root)[0],QQuickWindow)
        if os.environ['QT_QPA_PLATFORM']=='offscreen':self.window.setVisibility(QWindow.Visibility.Windowed);self.window.resize(960,640)
        self.root.findChild(QObject,'clockTimer').setProperty('running',False)
        self.root.setProperty('now',QDateTime.fromSecsSinceEpoch(int(self.now)))
        self.wait_ready();self.pump(180)
        # Provider and delivery hooks are downstream of QML slots. Wraps preserve actual effects.
        for label,obj,names in [('sport',self.sport,['selectMatch','selectTeamMatch','selectFantacalcio','clearTeamSelection','clearFantacalcio','setFavourite','refresh','refreshManual','refreshTeam','refreshFantacalcio']),('f1',self.racing['f1'],['select','selectDriver','clearSelection','refresh','refreshDetails']),('motogp',self.racing['motogp'],['select','selectDriver','clearSelection','refresh','refreshDetails']),('events',self.events._engine,['mark_seen','dismiss','mark_notified'])]:
            for name in names:
                if not hasattr(obj,name):continue
                original=getattr(obj,name);key=label+'.'+name;self.effects[key]=0
                def observed(*args,_key=key,_fn=original,**kwargs):self.effects[_key]+=1;return _fn(*args,**kwargs)
                self.stack.enter_context(patch.object(obj,name,side_effect=observed))
        # Positive control through real backend delegation, then reset permitted setup effects.
        from PySide6.QtCore import QCoreApplication,QEvent,Qt
        from PySide6.QtGui import QKeyEvent
        self.root.setProperty('familyId','sport');self.root.setProperty('sportView','RISULTATI');self.wait_ready()
        for _ in range(2):
            for kind in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
                QCoreApplication.sendEvent(self.window,QKeyEvent(kind,Qt.Key_5,Qt.KeyboardModifier.NoModifier))
            self.pump(40)
        assert self.value('overlay')=='sportDetail' and self.effects['sport.selectMatch']>0,'Qt input oracle did not observe backend delegation'
        end=time.monotonic()+3
        while self.sport._worker and time.monotonic()<end:self.pump(5)
        assert not self.sport._worker,'positive-control worker did not finish'
        self.root.setProperty('overlay','');self.root.setProperty('overlayStack',[]);self.root.setProperty('familyId','oggi');self.wait_ready()
        self.positive_control={'providerDelegationViaQKeyEvent':True,'networkDenied':True}
        self.reset_effects()

    def value(self,name):
        from theme_test_support import as_value
        return as_value(self.root.property(name))
    def expression(self,text):
        from PySide6.QtQml import QQmlExpression, QQmlEngine
        expr=QQmlExpression(QQmlEngine.contextForObject(self.root),self.root,text);result=expr.evaluate()
        assert not expr.hasError(),str(expr.error().toString())
        from theme_test_support import as_value
        return as_value(result[0])
    def pump(self,ms=30):
        end=time.monotonic()+ms/1000
        while time.monotonic()<end:self.app.processEvents();time.sleep(.001)
    def wait_ready(self):
        from theme_test_support import wait_ready
        wait_ready(self.app,self.root,timeout=5)
        end=time.monotonic()+5
        while self.service.candidateAppearance and time.monotonic()<end:self.pump(5)
        assert not self.service.candidateAppearance,'candidate did not commit'
    def reset_effects(self):
        for key in self.effects:self.effects[key]=0
        self.transport.clear()
    def actor(self):
        from PySide6.QtCore import QObject
        from theme_test_support import as_value
        host=self.root.findChild(QObject,'sceneHost');return host,as_value(host.property('actorState'))
    def setup(self,case):
        self.root.setProperty('overlay','');self.root.setProperty('overlayStack',[])
        self.state._theme_recovery_error='';self.state._night_mode=self.profile['variant'];self.state._first_run=False;self.state.settingsChanged.emit()
        assert self.service.setSection('paletteMode',self.profile['variant'])
        assert self.service.setSection('motionMode',self.profile['motion'])
        assert self.service.setSection('scene',{'enabled':False,'renderer':'builtin.actor'})
        self.events.set_demo_scenario('nessuno');self.root.setProperty('selectedAlert',{})
        self.sport._snapshot=deepcopy(self.seed);self.sport._favourite='';self.sport._error='';self.sport._team.snapshot=None
        self.sport.changed.emit()
        source=json.loads((CORPUS/'domains/weather-zero.json').read_text())
        from weather import normalize_response
        self.weather.value={'status':'active','source':'Open-Meteo fixture','updatedAt':self.now,'error':'','data':normalize_response(source['raw'])};self.weather.changed.emit()
        # Keep a stack and non-first-row selections to detect reset-on-style regressions.
        self.root.setProperty('sportDetailOffset',2);self.root.setProperty('racingInfoIndex',2)
        self.root.setProperty('optionIndex',2);self.root.setProperty('infoIndex',2)
        for setup in case['domainSetup']:
            family,variant=setup.split(':',1)
            if family=='weather':
                empty=variant in ('unavailable','pending','error');self.weather.value.update(status=variant,data={} if empty else self.weather.value['data'],error='Synthetic disconnected' if variant=='offline' else '')
                self.weather.changed.emit()
            elif family=='standings':self.sport._snapshot['standings']=[] if variant=='empty' else self.seed['standings'][:2]
            elif family=='fixtures':
                if variant=='favourite':self.sport._favourite='inter'
            elif family=='match':
                target=deepcopy(next(m for m in self.seed['fixtures'] if m.get('status')!='scheduled'))
                status=variant if variant in ('scheduled','live','finished') else 'finished'
                target.update(status=status,homeScore=None if status=='scheduled' else 0,
                              awayScore=None if status=='scheduled' else 0,
                              kickoffUtc=self.now+3600 if status=='scheduled' else self.now-1800 if status=='live' else self.now-10800,
                              fetchedAt=self.now)
                # Main selects by ID with find(). A duplicate would let it consume
                # the untouched seed and falsely pass the intended status×tab case.
                identity=target['canonicalMatchId'];fixtures=self.sport._snapshot['fixtures']
                assert sum(m['canonicalMatchId']==identity for m in fixtures)==1,'fixture identity is not unique'
                self.sport._snapshot['fixtures']=[target if m['canonicalMatchId']==identity else m for m in fixtures]
                self.root.setProperty('sportMatchId',target['canonicalMatchId']);self.root.setProperty('sportTeamDetail',variant=='teamRoute')
                if variant=='teamRoute':
                    self.sport._favourite='inter';self.sport._team.provider_id='8636';self.sport._team.team_id='inter';self.sport._team.snapshot=deepcopy(self.team)
                    self.root.setProperty('sportMatchId',self.team['fixtures'][0]['canonicalMatchId'])
            elif family=='team':
                if variant!='noFavourite':
                    self.sport._favourite='inter';self.sport._team.provider_id='8636';self.sport._team.team_id='inter';self.sport._team.snapshot=deepcopy(self.team)
                    if variant=='partialCalendar':self.sport._team.snapshot['fixtures']=self.sport._team.snapshot.get('fixtures',[])[:1]
            elif family=='racing':
                self.root.setProperty('familyId',variant);data=self.racing[variant].moduleState['data'];events=data.get('events',[])
                chosen=next((e for e in events if any(s.get('kind')=='RAC' and s.get('results') for s in e['sessions'])),events[0]);session=next((s for s in chosen['sessions'] if s.get('kind')=='RAC' and s.get('results')),next((s for s in chosen['sessions'] if s.get('results')),chosen['sessions'][0]))
                self.root.setProperty('racingEventId',chosen['id']);self.root.setProperty('racingSessionId',session['id'])
                rows=session.get('results',[]);self.root.setProperty('racingDriverId',rows[0]['id'] if rows else '')
            elif family=='notification':
                self.events.set_demo_scenario('urgente' if variant=='urgent' else 'banner grande' if variant=='large' else 'banner' if variant=='small' else 'prossimo')
                if variant in ('detail','inbox'):self.events._finish_banner();self.pump(20)
                if variant=='detail':self.root.setProperty('selectedAlert',self.events.state['items'][0] if hasattr(self.events,'state') else self.value('alertItems')[0])
            elif family=='shell':
                if variant=='overlay':self.root.setProperty('overlay','menu')
                if variant=='night':
                    assert self.service.setSection('paletteMode','night');self.state._night_mode='night';self.state.settingsChanged.emit()
                if variant=='urgent':self.events.set_demo_scenario('urgente')
                if variant=='recovery':self.state._theme_recovery_error='Synthetic missing manifest';self.state.settingsChanged.emit()
            elif family=='scene':
                assert self.service.setSection('scene',{'enabled':True})
                if variant=='paused':self.root.setProperty('overlay','menu')
                if variant in ('normal','reduced','off'):assert self.service.setSection('motionMode',variant)
                if variant=='canvas':
                    # App-registered example renderer, not a theme-provided public API implementation.
                    assert self.service.setSection('scene',{'enabled':True,'renderer':'fixture.canvas'})
        self.sport.changed.emit()
        for name,value in case['initialProperties'].items():assert self.root.setProperty(name,value),(name,value)
        if self.value('overlay'):self.root.setProperty('overlayStack',['','menu'])
        if case['id']=='overlay.commands:firstRun':self.state._first_run=True;self.state.settingsChanged.emit()
        if case['surfaceId']=='racing.driver.detail' and case['variant']=='liveTiming':
            service=self.racing['f1'];timing=service._timing.state
            timing.apply('SessionInfo',{'Key':900,'Name':'Race','StartDate':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(self.now-300))},self.now)
            timing.apply('SessionStatus',{'Status':'Started'},self.now)
            timing.apply('DriverList',{'1':{'FullName':'Test driver','TeamName':'Test team'}},self.now)
            timing.apply('TimingData',{'Lines':{'1':{'Position':'1','BestLapTime':{'Value':'1:20.000'}}}},self.now)
            timing.connected=True;service.changed.emit();self.pump(20)
            live_rows=service.moduleState['data']['live'].get('rows',[])
            assert live_rows,'synthetic timing row absent'
            self.root.setProperty('racingDriverId',live_rows[0]['id'])
        self.wait_ready();self.pump(220)
        deadline=time.monotonic()+5
        def workers():return self.sport._worker or self.sport._team.worker or self.sport._fantasy.worker or any(service._worker for service in self.racing.values())
        while workers() and time.monotonic()<deadline:self.pump(5)
        assert not workers(),'domain setup completion barrier timeout'
        self.reset_effects()
    def event_flags(self):
        rows=self.events._engine.db.execute('SELECT id, rank, payload, seen, dismissed_level, notified_level, cancelled FROM events ORDER BY id').fetchall()
        return [tuple(row) for row in rows]
    def assert_match_domain(self,case):
        expected=case.get('expectedDomain')
        if expected is None:return
        data=self.sport.moduleState['data']
        if self.value('sportTeamDetail'):data=data['favouriteTeam']['data']
        rows=[match for match in data['fixtures'] if match['canonicalMatchId']==self.value('sportMatchId')]
        assert len(rows)==1,(case['id'],'selected backend identity is not unique')
        for field,value in expected.items():
            actual=rows[0][field]
            assert actual==value and type(actual) is type(value),(case['id'],'domain',field,actual,value)
    def run_case(self,case):
        self.setup(case)
        for expected in case['expectedExpressions']:assert self.expression(expected),(case['id'],expected)
        self.assert_match_domain(case)
        self.assert_surface(case)
        host,actor=self.actor();actor.setProperty('pose','playing')
        before={key:self.value(key) for key in self.KEPT};flags=self.event_flags();deadline=self.events._banner_until
        draft=deepcopy(self.service.draft);oldrevision=self.service.revision
        for action in case['actions']:
            assert self.service.setToken(action['token'],action['value']),self.service.lastError
            self.wait_ready();self.pump(10)
        assert self.service.revision>oldrevision,'no observed style publication'
        assert self.expression('style.radiusRow')==6,'actual typed facade did not update'
        draft.setdefault('overrides',{}).setdefault('tokens',{})['shape.radiusRow']=6
        assert self.service.draft==draft,'unrelated appearance draft fields changed'
        for expected in case['expectedExpressions']:assert self.expression(expected),(case['id'],'after',expected)
        self.assert_match_domain(case)
        after={key:self.value(key) for key in self.KEPT};assert before==after,(case['id'],{k:(before[k],after[k]) for k in before if before[k]!=after[k]})
        assert self.actor()==(host,actor) and actor.property('pose')=='playing','actor identity/pose reset'
        assert self.event_flags()==flags,'theme change changed event delivery flags'
        assert self.events._banner_until==deadline,'theme change restarted notification deadline'
        assert not any(self.effects.values()),(case['id'],self.effects)
        assert not self.transport,(case['id'],self.transport)
        assert self.window.activeFocusItem() and self.window.activeFocusItem().objectName()=='inputOwner','input focus lost'
        self.assert_surface(case)
        assert not self.messages,(case['id'],self.messages)
        return {'id':case['id'],'covers':case['covers'],'family':case['family'],'surfaceId':case['surfaceId'],'variant':case['variant'],'status':'passed','assertions':(len(case['expectedExpressions'])+len(case.get('expectedDomain',{})))*2+10,'styleRevisionBefore':oldrevision,'styleRevisionAfter':self.service.revision,'effects':dict(self.effects),'eventFlagsPreserved':True,'deadlinePreserved':True,'actorIdentityPreserved':True,'inputFocus':'inputOwner','publicApiBinding':'deferredA1'}
    def assert_surface(self,case):
        from PySide6.QtCore import QObject
        from theme_test_support import as_value
        sid=case['surfaceId'];names={'home.now':'homeNow','home.clock':'homeClock','home.day':'homeDay','weather.now':'weatherNow','weather.forecast':'weatherForecast','account.usage':'accountPanel','sport.overview':'sportPanel','sport.team':'sportTeamPanel','racing.overview':'racingPanel','casa.overview':'casaOverview','casa.devices':'casaDevices','network.overview':'networkOverview','network.devices':'networkDevices','alerts.badge':'unreadAlertsBadge','alerts.banner.small':'eventBanner','alerts.banner.large':'eventLargeBanner','alerts.urgent':'eventUrgent','alerts.inbox':'alertsInbox','alerts.detail':'alertDetail'}
        if sid in names:
            obj=self.root.findChild(QObject,names[sid]);assert obj is not None and obj.property('readiness')=='ready',(sid,'not ready')
            item=as_value(obj.property('currentItem'));assert item is not None,(sid,'no renderer')
            assert obj.property('visible'),(sid,'not exposed')
            assert obj.property('width')>0 and obj.property('height')>0,(sid,'zero geometry')
        elif sid=='scene.main':
            host,actor=self.actor();assert host.property('sceneEnabled') and actor is not None
            renderer=self.service.resolvedAppearance['scene']['renderer']
            assert host.property('traceLoadedRenderer')==renderer,'scene renderer identity not loaded'
            loaders=[obj for obj in host.findChildren(QObject) if obj.metaObject().className()=='QQuickLoader']
            from PySide6.QtQml import QQmlEngine,QQmlExpression
            assert len(loaders)==1,'scene Loader identity is ambiguous'
            ready=QQmlExpression(QQmlEngine.contextForObject(loaders[0]),loaders[0],'status === 1').evaluate()
            assert ready[0] is True and not ready[1],'scene Loader is not Ready'
            item=as_value(loaders[0].property('item'));assert item is not None and as_value(item.property('actorState'))==actor,'scene renderer does not receive persistent actor'
            mode=self.service.resolvedAppearance['motionMode'];assert actor.property('motionMode')==mode
            assert actor.property('paused')==bool(host.property('suspended') or host.property('regionBlocked') or mode!='normal'),'scene motion policy mismatch'
            if case['variant'] in ('normal','reduced','off'):assert mode==case['variant']
            if case['variant']=='canvas':assert host.property('canvasScene') and renderer=='fixture.canvas','canvas variant not actually instantiated'
            if case['variant']=='paused':assert host.property('suspended') and actor.property('paused')
        elif sid in ('settings.casa','casa.detail','settings.network','network.detail'):
            host=self.root.findChild(QObject,'overlayHost')
            assert host and host.property('readiness')=='ready' and host.property('visible'),sid
        elif sid.startswith('settings.') and sid not in ('settings.sport','settings.racing'):
            assert self.expression('settingsPanel.active && settingsPanel.rows.length > 0'),sid
        elif sid=='shell.main':assert self.window.width()==960 and self.window.height()==640
        else:assert self.value('overlay')==case['initialProperties'].get('overlay'),sid
        if sid not in names and sid not in ('shell.main','scene.main','settings.casa','casa.detail','settings.network','network.detail'):
            source={'device.info':'DeviceInfo','sport.team.detail':'SportTeamOverlay','sport.team.picker':'SportTeamOverlay'}.get(sid, 'MotorsportOverlay' if sid.startswith('racing.') or sid=='settings.racing' else 'SportOverlay' if sid.startswith('sport.') or sid=='settings.sport' else 'SettingsPanel' if sid.startswith('settings.') else 'DashboardOverlay')
            components=[obj for obj in self.root.findChildren(QObject) if obj.metaObject().className().startswith(source+'_') and obj.metaObject().indexOfProperty('dashboard')>=0]
            assert len(components)==1 and components[0].property('visible') and components[0].property('width')>0 and components[0].property('height')>0,(sid,'legacy component not exposed',source)
    def close(self):
        from PySide6.QtCore import QThreadPool,qInstallMessageHandler
        self.events.close();self.sport.close();self.network.close();self.casa.close()
        for service in self.racing.values():service.close()
        self.window.close();self.engine.deleteLater();self.pump(20)
        assert QThreadPool.globalInstance().waitForDone(3000),'fixture worker teardown timeout'
        self.stack.close();qInstallMessageHandler(self.previous_handler)


def loading_watchdog_lane(base):
    """Hold the actual Qt incubator; test its positive control and Loading watchdog.

    A service/host error is the oracle, not a duplicate harness timeout timer.
    This exercises the app's existing registered example presentation in isolation.
    """
    from PySide6.QtCore import QObject
    from PySide6.QtQml import QQmlIncubationController,QQmlExpression,QQmlEngine
    harness=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
    controller=QQmlIncubationController()
    try:
        host=harness.root.findChild(QObject,'homeNow')
        harness.engine.setIncubationController(controller)
        def loading():
            expr=QQmlExpression(QQmlEngine.contextForObject(host),host,'pendingLoader !== null && pendingLoader.status === 2')
            result=expr.evaluate();assert not expr.hasError();return bool(result[0])
        def until(predicate,timeout,drive=False):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                harness.pump(5)
                if drive:controller.incubateFor(20)
                if predicate():return
            raise AssertionError('loading fixture causal barrier timeout')
        assert harness.service.setSection('presentations',{'home.now':'example.home.summary'})
        until(loading,1)
        assert harness.service.candidateAppearance and host.property('loadedPresentationId')!='example.home.summary'
        until(lambda:not harness.service.candidateAppearance,2,drive=True)
        assert host.property('loadedPresentationId')=='example.home.summary','incubator positive control failed'
        harness.service.cancel();until(lambda:host.property('loadedPresentationId')!='example.home.summary',2,drive=True)
        harness.service.beginEdit();revision=harness.service.revision
        assert harness.service.setSection('presentations',{'home.now':'example.home.summary'})
        until(loading,1)
        until(lambda:bool(harness.service.lastError),5)
        assert 'Timeout caricamento' in harness.service.lastError,harness.service.lastError
        assert harness.service.revision==revision and not harness.service.readyToApply,'Loading timeout published a failed candidate'
        assert host.property('currentItem') is not None and host.property('readiness')=='ready','Loading watchdog discarded the previous presentation'
        assert harness.window.activeFocusItem().objectName()=='inputOwner'
        harness.service.cancel();controller.incubateFor(100);harness.wait_ready()
        assert not harness.messages,harness.messages
        return {'status':'passed','scope':'Actual asynchronous Loader.Loading held by QQmlIncubationController; real 3s app watchdog','positiveControl':'incubateFor releases the same renderer and commits','failedCandidateDidNotPublish':True,'previousRendererRetained':True,'focus':'inputOwner','timeoutErrorKind':'loadingTimeout','qmlWarnings':harness.messages}
    finally:
        # Controller is kept alive until the engine has finished with pending jobs.
        controller.incubateFor(100);harness.close()
