"""Three real typed overlays, chart rendering and visible single-worker scheduling."""
from copy import deepcopy
import argparse,json,subprocess,sys,threading,time
from pathlib import Path
from unittest.mock import patch
from theme_fixture_support import isolate_process,LegacyHarness

def verify(profile,capture=None):
    private,base=isolate_process();h=None;services=[];checks=[]
    try:
        from PySide6.QtCore import qVersion
        from network import NetworkService
        from iliadbox import NetworkError
        from check_network_metrics import MetricsRouter
        from check_network import CONFIG,NOW
        h=LegacyHarness(base,profile)
        def settle(s):
            end=time.monotonic()+7
            while s._busy and time.monotonic()<end:h.pump(5)
            assert not s._busy,'worker did not settle'
        config=base/'config/app.json';config.write_text(json.dumps(CONFIG));config.chmod(0o600)
        router=MetricsRouter();mono=[1000];wall=[NOW]
        s=NetworkService(auto_refresh=False,config_path=config,state_dir=base/'network',transport=router,clock=lambda:wall[0],monotonic=lambda:mono[0]);services.append(s)
        with patch('network.local_info',return_value={'state':'configured','interface':'test0','address':'192.0.2.20'}):
            assert s.refresh();settle(s);inventory=deepcopy(s._snapshot);scheduled=s._next
            initial=len(router.calls);s._tick();assert len(router.calls)==initial and not s._busy
            s.setMetricsInterest('router','','state',1,0,'');assert s.refreshMetrics();settle(s)
            assert s._next==scheduled and s._snapshot==inventory
            assert not s.refreshMetrics(),'cooldown must reject repeat'
            notifications=[];s.changed.connect(lambda:notifications.append('inventory'))
            mono[0]+=30;wall[0]+=30;assert s.refreshMetrics();settle(s);assert not notifications
            s.setMetricsInterest('','','',1,0,'');mono[0]+=30;wall[0]+=30;initial=len(router.calls);s._tick();assert len(router.calls)==initial
            assert s.togglePolling();settle(s);s.setMetricsInterest('router','','history',24,0,'');initial=len(router.calls);s._tick();assert len(router.calls)==initial
            assert s.refreshMetrics();settle(s),'manual remains available while paused'
            assert s.togglePolling();settle(s)
            checks+=['outsideViewNoExtraReads','inventoryDeadlineUnchanged','singleFlightAndCooldown','pauseAndManual','metricsDoNotInvalidateAppearance']
            entered=threading.Event();release=threading.Event();original=s._metrics_store.save;completions=[];s.metricsRefreshFinished.connect(lambda ok,msg:completions.append(ok))
            def slow(caps):entered.set();assert release.wait(3);original(caps)
            s.setMetricsInterest('wifi','','radios',1,0,'')
            with patch.object(s._metrics_store,'save',side_effect=slow):
                try:
                    assert s.refreshMetrics();end=time.monotonic()+2
                    while not entered.is_set() and time.monotonic()<end:h.pump(5)
                    assert entered.is_set();h.pump(30);assert s._busy and not completions
                    s.setMetricsInterest('ports','','ports',1,0,'');assert not s.refreshMetrics()
                    assert s.setAlias(inventory['devices'][0]['id'],'Studio');assert s.refresh()
                finally:release.set()
                settle(s)
            # Preference queued first; manual inventory drained after its persistence.
            settle(s);assert s._snapshot['preferences']['aliases'][inventory['devices'][0]['id']]=='Studio'
            assert s._metrics_next<=mono[0], 'new interest was deferred by old completion'
            s._tick();settle(s);assert s._caps.get('catalog:ports')
            before=deepcopy(s._caps);mono[0]+=30;wall[0]+=30
            with patch.object(s._metrics_store,'save',side_effect=NetworkError('storage','Synthetic disk failure')):
                assert s.refreshMetrics();settle(s)
            assert s._caps==before and completions[-1] is False
            s.setMetricsInterest('router','','state',1,0,'');router.fail_path='/ftth/';mono[0]+=700;wall[0]+=700;assert s.refreshMetrics();settle(s)
            assert completions[-1] is False and not s._halted and s._caps['wan']['status']=='active' and s._caps['catalog:fibre']['status']=='error'
            checks+=['durableMetricCompletion','latestInterestAfterLateResponse','preferenceAndManualRefreshPriority','failedWriteRetainsSnapshot','optionalFailureNotFalseSuccess']
        # Exercise the actual Main action broker: success waits for worker persistence.
        h.state._network=s;s.changed.connect(h.state.networkChanged);s.metricsChanged.connect(h.state.networkMetricsChanged);s.metricsRefreshFinished.connect(h.state.networkMetricsRefreshFinished)
        h.state.networkChanged.emit();h.root.setProperty('familyId','network');h.expression('openNetworkMetrics("network.router")');h.pump(150)
        router.fail_path='';mono[0]+=30;wall[0]+=30
        factory=h.service.apiFactory;context=factory.create('network.router');payload=h.expression('publicSurfacePayload("network.router")');payload.update(active=True,interactive=True,viewportWidth=960,viewportHeight=640)
        assert factory.updateLegacy(context,payload)
        entered=threading.Event();release=threading.Event();original=s._metrics_store.save
        def held_for_broker(caps):entered.set();assert release.wait(3);original(caps)
        with patch.object(s._metrics_store,'save',side_effect=held_for_broker):
            try:
                handle=context.requestAction('network.metrics.refresh','network.router',{});assert handle.status=='pending',(handle.status,handle.errorCode,h.value('networkData')['modeText'],s._interest,s._metrics_next,mono[0])
                end=time.monotonic()+2
                while not entered.is_set() and time.monotonic()<end:h.pump(5)
                assert entered.is_set();h.pump(30);assert handle.status=='pending','broker confirmed before persistence'
            finally:release.set()
            settle(s);assert handle.status=='completed',handle.status
        factory.release(context);checks.append('actualMainBrokerWaitsForMetricPersistence')
        h.state._network=h.network;h.state.networkChanged.emit();h.state.networkMetricsChanged.emit();h.expression('back()');h.pump(100)
        h.root.setProperty('familyId','network');h.pump(180);h.expression('networkSelectedId=networkRows[1].id');selected=h.value('networkSelectedId')
        def grab(label):
            h.pump(220);assert not h.messages,h.messages
            if capture:
                out=Path(capture);out.mkdir(parents=True,exist_ok=True);assert h.window.grabWindow().save(str(out/(profile['theme']+'-'+label+'.png')))
        h.expression('networkOverviewSection="tools"');grab('tools')
        for target,route in [('networkRouter','router'),('networkWifi','wifi'),('networkPorts','ports')]:
            h.expression('openNetworkMetrics("network.'+route+'")');h.pump(220);assert h.value('overlay')==target;assert h.value('networkMetricsView')['title'];grab(route)
            if route=='wifi':
                h.expression('networkMetricsTabsSelected=false');h.expression('activateKey(5)');h.pump(100)
                assert h.value('networkMetricsSection')=='stations';grab('stations')
                h.expression('activateKey(5)');h.pump(100);assert h.value('networkMetricsSection')=='detail';grab('station-detail')
                h.expression('networkMetricsIndex=networkMetricsRows.findIndex(r=>r.id==="lan")');h.expression('activateKey(5)');h.pump(120);assert h.value('overlay')=='networkDetail'
                h.expression('back()');h.pump(120);assert h.value('overlay')==target
            if route=='ports':
                h.expression('networkMetricsIndex=2;networkMetricsTabsSelected=false');h.expression('activateKey(5)');h.pump(100);assert h.value('networkMetricsSection')=='hosts';grab('port-hosts')
            if route in ('router','ports'):
                h.expression('networkMetricsHours=1;networkMetricsSection="history"');grab(route+'-history');assert h.value('networkMetricsView')['hasChart']
                h.expression('activateKey(8)');grab(route+'-24h');assert h.value('networkMetricsHours')==24
                if route=='router':
                    h.expression('activateKey(5)');grab('temperature');h.expression('activateKey(5)');grab('fan')
                h.network._caps={};h.network.metricsChanged.emit();grab(route+'-empty');assert not h.value('networkMetricsView')['hasChart']
                from network_metrics import demo_caps
                h.network._caps=demo_caps(h.network._snapshot,h.now);h.network.metricsChanged.emit()
            h.expression('back()');h.pump(100);assert h.value('networkSelectedId')==selected
        assert not h.messages and not h.transport,(h.messages,h.transport)
        checks+=['threeTypedOverlays','keypadNavigationAndLanJoin','returnPreservesLanSelection','1h24hChartsAndEmptyState','temperatureAndFanSeparateAxes','zeroQmlWarnings']
        after=[];s.metricsRefreshFinished.connect(lambda *args:after.append(args));router.fail_path='';mono[0]+=30;wall[0]+=30
        entered=threading.Event();release=threading.Event();original=s._metrics_store.save
        def held(caps):entered.set();assert release.wait(3);original(caps)
        with patch.object(s._metrics_store,'save',side_effect=held):
            assert s.refreshMetrics();end=time.monotonic()+2
            while not entered.is_set() and time.monotonic()<end:h.pump(5)
            assert entered.is_set();threading.Timer(.1,release.set).start();s.close();h.pump(50)
        assert not s.refreshMetrics() and not after
        checks.append('shutdownSuppressesInflightCompletion')
        return {'status':'passed','profile':profile,'qt':qVersion(),'checks':checks,'warnings':h.messages}
    finally:
        for s in services:s.close()
        if h:h.close()
        private.cleanup()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--child');p.add_argument('--capture');a=p.parse_args()
    if a.child:print(json.dumps(verify(json.loads(a.child),a.capture),ensure_ascii=False))
    else:
        for theme,variant in [('base','day'),('functional','night')]:
            cmd=[sys.executable,__file__,'--child',json.dumps({'theme':theme,'variant':variant,'motion':'off'})]
            if a.capture:cmd+=['--capture',a.capture]
            result=subprocess.run(cmd,timeout=65,capture_output=True,text=True);print(result.stdout);print(result.stderr,file=sys.stderr);assert result.returncode==0
