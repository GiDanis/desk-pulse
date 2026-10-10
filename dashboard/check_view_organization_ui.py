"""Real Main dashboard projections, keypad drill-down and native containment."""
import argparse
import json
from pathlib import Path
from theme_fixture_support import isolate_process, LegacyHarness

parser = argparse.ArgumentParser()
parser.add_argument('--theme', choices=['base', 'functional', 'apple'], default='base')
parser.add_argument('--palette', choices=['day', 'night'], default='day')
parser.add_argument('--capture-dir', type=Path)
args = parser.parse_args()
private, data = isolate_process()
h = None
closed=False
try:
    from PySide6.QtCore import QObject, QPointF, qVersion
    from theme_bundle import BundleManager, validate_project
    from theme_test_support import as_value
    project = Path(__file__).resolve().parents[1] / 'theme-projects/apple-calm/bundle'
    if args.theme == 'apple':
        valid = validate_project(project)
        cache = json.loads((project.parent / 'evidence/preflight-cache.json').read_text())
        assert cache['digest'] == valid['digest'] and cache['result']['status'] == 'passed', cache
        BundleManager(data).import_bundle(project, preflight=lambda *_: cache['result'], require_preflight=True)
    h = LegacyHarness(data, {'theme':'base' if args.theme == 'apple' else args.theme, 'variant':args.palette, 'motion':'off'})
    if args.theme == 'apple':
        assert h.service.selectDraft('studio.applecalm')
        h.wait_ready()
    output = args.capture_dir or Path(private.name) / 'captures'
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    def visit(family, index=0, discipline='sport'):
        h.root.setProperty('overlay', '')
        h.root.setProperty('overlayStack', [])
        h.root.setProperty('sportDashboardReturn', False)
        h.root.setProperty('sportHubSelectedId', discipline)
        h.root.setProperty('familyId', family)
        indices=[0]*8
        indices[{'oggi':0, 'meteo':1, 'account':2, 'sports':3, 'casa':6, 'network':7}[family]]=index
        h.root.setProperty('viewIndex', indices)
        h.wait_ready();h.pump(160)
        host=next(obj for obj in h.root.findChildren(QObject) if obj.objectName() in ['homeNow','homeClock','homeDay','weatherNow','weatherForecast','accountPanel','sportHub','casaOverview','casaDevices','networkOverview','networkDevices'] and obj.property('active'))
        return host,as_value(host.property('currentItem'))
    def tree(item):
        yield item
        for child in item.childItems():
            yield from tree(child)
    def capture(name):
        h.pump(80)
        assert h.window.grabWindow().save(str(output/(name+'.png')))
    families=[('oggi',i,'sport') for i in range(3)]+[('meteo',i,'sport') for i in range(2)]+[('account',0,'sport')]+[('sports',0,d) for d in ['sport','team','f1','motogp']]+[('casa',i,'sport') for i in range(3)]+[('network',i,'sport') for i in range(3)]
    for family,index,discipline in families:
        host,item=visit(family,index,discipline)
        assert item is not None,(family,index,h.messages)
        name=h.value('dashboardViewId') or h.value('activeContentId')
        cards=[c for c in tree(item) if c.objectName().startswith('dashboardCard') and c.isVisible()]
        for c in cards:
            point=c.mapToScene(QPointF(0,0))
            assert 23.5 <= point.x() and point.x()+c.width()<=936.5
            assert 119.5 <= point.y() and point.y()+c.height()<=624.5,(name,point.y(),c.height())
        if cards:
            assert abs(max(c.mapToScene(QPointF(0,0)).y()+c.height() for c in cards)-624)<1
        capture(name)
        reports.append({'view':name,'surface':h.value('activeContentId'),'cards':len(cards)})
        if family in ['oggi','meteo','account','sports','casa','network']:
            h.expression('activateKey(5)');h.wait_ready();h.pump(120)
            route=h.value('overlay')
            assert route,(name,'no detail route')
            capture(name+'-detail')
            if family in ['casa','network'] and route in ['casaList','networkList']:
                h.expression('activateKey(8)');h.expression('activateKey(5)');h.wait_ready()
                assert h.value('overlay') in ['casaDetail','networkDetail']
                h.expression('activateKey(7)');h.wait_ready()
                assert h.value('overlay')==route
            h.expression('activateKey(7)');h.wait_ready();h.pump(120)
            assert h.value('overlay')==''
            assert h.value('familyId')==family,(name,h.value('familyId'))
            assert (h.value('dashboardViewId') or h.value('activeContentId'))==name,(name,h.value('dashboardViewId'))
    # A retained Canvas must repaint when the palette changes, even with no
    # new network sample. Assert actual pixels within the chart, not just DTOs.
    host,item=visit('network',0)
    for palette in ['night' if args.palette=='day' else 'day',args.palette]:
        assert h.service.setSection('paletteMode',palette)
        h.wait_ready();h.pump(200)
        item=as_value(host.property('currentItem'))
        canvases=[c for c in tree(item) if c.metaObject().indexOfProperty('drawing')>=0]
        assert canvases
        canvas=canvases[0];point=canvas.mapToScene(QPointF(0,0));color=as_value(canvas.property('visualStyle')).property('accent')
        shot=h.window.grabWindow()
        pixels=sum(all(abs(shot.pixelColor(x,y).getRgb()[i]-color.getRgb()[i])<=5 for i in range(3))
                   for x in range(int(point.x()),int(point.x()+canvas.width()))
                   for y in range(int(point.y()),int(point.y()+canvas.height())))
        assert pixels>5,(palette,pixels,color.name())
    # Calendars and tables remain available as secondary contextual commands.
    for discipline in ['sport','team','f1','motogp']:
        visit('sports',0,discipline)
        for action,route in [(4,'sportList' if discipline in ['sport','team'] else 'racingList'),(5,'sportTable' if discipline in ['sport','team'] else 'racingTable')]:
            h.expression('activateKey(9)');h.wait_ready()
            h.root.setProperty('menuIndex',action);h.expression('activateKey(5)');h.wait_ready()
            assert h.value('overlay')==route,(discipline,action,h.value('overlay'))
            h.expression('activateKey(7)');h.wait_ready();assert h.value('overlay')=='menu'
            h.expression('activateKey(7)');h.wait_ready();assert h.value('familyId')=='sports'
    # Regression: league opens every game in the round, independently of the
    # favourite; a separate dashboard opens the club route or its picker.
    from copy import deepcopy
    original=deepcopy(h.sport._snapshot)
    sample=deepcopy(original['fixtures'][0])
    fixtures=[]
    for i in range(10):
        row=deepcopy(sample)
        row.update(rawStatus={},homeScore=None,awayScore=None,minute='',fetchedAt=h.now,canonicalMatchId='serie-a-regression-'+str(i),round='7',status='scheduled',
                   kickoffUtc=h.now+3600*(i+1),homeTeamId='inter' if i==9 else 'other-'+str(i),
                   awayTeamId='away-'+str(i),homeTeam='Inter' if i==9 else 'Club '+str(i),awayTeam='Ospite '+str(i))
        fixtures.append(row)
    h.sport._snapshot['fixtures']=fixtures
    h.sport._favourite='inter'
    h.sport._team.provider_id='8636';h.sport._team.team_id='inter';h.sport._team.snapshot=deepcopy(h.team)
    h.sport.changed.emit();h.wait_ready()
    visit('sports',0,'sport')
    assert h.state.dashboardSummary('sport-sport',h.now)['eventId']=='serie-a-regression-0'
    h.expression('activateKey(5)');h.wait_ready()
    assert h.value('overlay')=='sportList'
    assert {m['canonicalMatchId'] for m in h.value('sportRows')}=={m['canonicalMatchId'] for m in fixtures}
    assert all(m['statusText']=='In programma' and m['scoreText']=='—' for m in h.value('sportRows'))
    capture('serie-a-all-ten-games')
    for _ in range(9):h.expression('activateKey(8)')
    assert h.value('sportIndex')==9
    h.expression('activateKey(5)');h.wait_ready()
    assert h.value('overlay')=='sportDetail' and h.value('sportMatchId')=='serie-a-regression-9'
    h.expression('activateKey(7)');h.wait_ready();assert h.value('overlay')=='sportList' and h.value('sportIndex')==9
    h.expression('activateKey(7)');h.wait_ready();assert h.value('familyId')=='sports'
    visit('sports',0,'team');capture('favourite-dashboard')
    assert h.state.dashboardSummary('sport-team',h.now)['eventId']=='serie-a-regression-9'
    h.expression('activateKey(5)');h.wait_ready();assert h.value('overlay')=='sportTeam'
    capture('favourite-club-details')
    h.expression('activateKey(7)');h.wait_ready()
    assert h.value('familyId')=='sports' and h.value('sportHubSelectedId')=='team'
    h.sport._favourite='';h.sport.changed.emit()
    visit('sports',0,'team');h.expression('activateKey(5)');h.wait_ready()
    assert h.value('overlay')=='sportTeamPicker'
    h.expression('activateKey(7)');h.wait_ready();assert h.value('familyId')=='sports'
    h.state.toggleModuleVisibility('sport');h.wait_ready()
    assert not any(row['id'] in ['sport','team'] for row in h.value('sportDisciplines'))
    h.state.toggleModuleVisibility('sport');h.wait_ready()
    h.sport._snapshot=original;h.sport._favourite='';h.sport._team.snapshot=None;h.sport.changed.emit()
    # Repeated geometry requests reuse a small projection; a provider signal
    # invalidates it, and crossing the clock bucket reevaluates event priority.
    from unittest.mock import patch
    from dashboard_summary import build_summary
    visit('oggi',0)
    h.state._invalidate_dashboards()
    with patch('dashboard_summary.build_summary', wraps=build_summary) as projected:
        h.state.dashboardSummary('sport-f1',h.now)
        h.state.dashboardSummary('sport-f1',h.now+1)
        assert sum(c.args[0]=='sport-f1' for c in projected.call_args_list)==1
        h.weather.changed.emit()
        h.state.dashboardSummary('sport-f1',h.now)
        assert sum(c.args[0]=='sport-f1' for c in projected.call_args_list)==1
        h.racing['f1'].changed.emit()
        h.state.dashboardSummary('sport-f1',h.now)
        assert sum(c.args[0]=='sport-f1' for c in projected.call_args_list)==2
        h.state.dashboardSummary('sport-f1',h.now+6)
        assert sum(c.args[0]=='sport-f1' for c in projected.call_args_list)==3
    # One axis always changes topic, one changes dashboard, independent of focus.
    visit('network',0);h.expression('activateKey(8)');h.pump(160)
    assert h.value('dashboardViewId')=='rete-iliadbox'
    h.expression('activateKey(8)');h.wait_ready();assert h.value('dashboardViewId')=='rete-dispositivi'
    h.expression('activateKey(8)');h.wait_ready();assert h.value('dashboardViewId')=='rete-dispositivi'
    h.expression('activateKey(4)');h.wait_ready();assert h.value('familyId')=='casa'
    visit('sports');h.expression('activateKey(8)');h.pump(160);assert h.value('dashboardViewId')=='sport-team'
    h.expression('activateKey(8)');h.wait_ready();assert h.value('dashboardViewId')=='sport-f1'
    for scale in [1.1,1.0]:
        assert h.service.setToken('typography.textScale',scale)
        for family,index,discipline in [('sports',0,'f1'),('casa',1,'sport'),('network',1,'sport')]:
            host,item=visit(family,index,discipline)
            for c in tree(item):
                if c.objectName().startswith('dashboardCard') and c.isVisible():
                    point=c.mapToScene(QPointF(0,0));assert point.y()+c.height()<=624.5
            capture(h.value('dashboardViewId')+'-scale-'+str(scale))
    h.close()
    closed=True
    assert not h.transport,h.transport
    assert not h.messages,h.messages
    report={'status':'passed','qt':qVersion(),'platform':h.app.platformName(),'theme':args.theme,'palette':args.palette,'views':reports,'keypad':'dashboard axes, drill-down and origin return passed','networkDenied':True,'qmlWarnings':h.messages,'physicalPanel':'notVerified','serieAAllTenGamesAccessible':True,'favouriteRouteSeparated':True,'noFavouritePickerVerified':True,'footballVisibilityHidesBothDashboards':True}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
finally:
    if h and not closed: h.close()
    private.cleanup()
