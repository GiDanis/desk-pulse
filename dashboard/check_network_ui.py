"""Real Main LAN surfaces and Qt worker failure/recovery; isolated synthetic I/O."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from theme_fixture_support import isolate_process,LegacyHarness


def verify(profile,capture=None):
    private,base=isolate_process();h=None;services=[];checks=[]
    try:
        from PySide6.QtCore import QObject,qVersion
        from network import NetworkService
        from network_core import demo_snapshot
        from iliadbox import NetworkError
        from check_network import FakeRouter,CONFIG,NOW
        h=LegacyHarness(base,profile)
        notifications=[]
        h.state.settingsChanged.connect(lambda:notifications.append("settings"))
        h.network.changed.emit();h.pump(20)
        assert not notifications,"LAN refresh must not invalidate appearance/settings"
        assert "network" in h.state.visibleModules
        checks.append("providerUpdatesDoNotReloadTheme")
        def settle(service):
            until=time.monotonic()+6
            while service._busy and time.monotonic()<until:h.pump(5)
            assert not service._busy,'worker timeout'
        config=base/'config/app.json';config.write_text(json.dumps(CONFIG));config.chmod(0o600)
        router=FakeRouter();wall=[NOW];mono=[1000]
        def make():
            s=NetworkService(auto_refresh=False,config_path=config,state_dir=base/'network',transport=router,clock=lambda:wall[0],monotonic=lambda:mono[0]);services.append(s);return s
        with patch('network.local_info',return_value={'state':'configured','interface':'test0','address':'192.0.2.20'}):
            s=make();assert s.refresh() and not s.refresh();settle(s);assert s.moduleState['status']=='active'
            identity=s._snapshot['devices'][0]['id'];assert s.toggleFavourite(identity);settle(s)
            assert s.setAlias(identity,'Studio');settle(s)
            restored=make();assert restored.moduleState['status']=='stale';assert restored.moduleState['data']['favourites'][0]['name']=='Studio'
            before=deepcopy(s._snapshot);router.failure=NetworkError('transport','Synthetic unavailable');mono[0]+=60
            assert s.refresh();settle(s);assert s._snapshot==before and s.moduleState['data']['devices'][0]['previous']
            router.failure=None;mono[0]+=300;wall[0]+=300;s._tick();settle(s);assert s.moduleState['status']=='active'
            before=deepcopy(s._snapshot);mono[0]+=60
            with patch.object(s.store,'commit',side_effect=NetworkError('storage','Synthetic disk failure')):
                assert s.refresh();settle(s)
            assert s._snapshot==before and s.moduleState['status']=='error' and s._halted
            mono[0]+=60;assert s.refresh();settle(s);assert not s._halted
            router.failure=NetworkError('auth','Synthetic revoked');mono[0]+=60;assert s.refresh();settle(s)
            assert s._halted and not s.moduleState['data']['polling'];attempts=len(router.calls);mono[0]+=1800;s._tick();assert len(router.calls)==attempts
            router.failure=None;mono[0]+=60;assert s.refresh();settle(s);assert not s._halted
            checks+=['singleFlight','preferencesAndAliasesSurviveRestart','cacheNeverCurrentAtColdStart','failureRetainsPrevious','unwritableCacheNoConfirmation','boundedBackoffAndAuthHalt','manualRecovery']
            assert s.togglePolling();settle(s);wall[0]+=400;mono[0]+=400;s._tick();assert s.moduleState['status']=='stale' and not s._busy
            # Hold a real preference commit to prove GUI responsiveness and no early confirmation.
            entered=threading.Event();release=threading.Event();original=s.store.commit;completions=[];s.refreshFinished.connect(lambda ok,msg:completions.append(ok))
            def slow(**kwargs):
                entered.set();assert release.wait(3);original(**kwargs)
            with patch.object(s.store,'commit',side_effect=slow):
                try:
                    assert s.setAlias(identity,'Nuovo alias');until=time.monotonic()+2
                    while not entered.is_set() and time.monotonic()<until:h.pump(5)
                    assert entered.is_set();h.pump(30);assert s._busy and not completions
                finally:release.set()
                settle(s)
            assert completions==[True];checks+=['pausedPollingStillAges','durablePreferencesOffGuiThread']
        h.root.setProperty('familyId','network');h.pump(180)
        def grab(label):
            h.pump(180);assert not h.messages,h.messages
            if capture:
                directory=Path(capture);directory.mkdir(parents=True,exist_ok=True);assert h.window.grabWindow().save(str(directory/(profile['theme']+'-'+profile['variant']+'-'+label+'.png')))
        overview=h.root.findChild(QObject,'networkOverview');assert overview.property('readiness')=='ready'
        assert h.value('activeContentId')=='network.overview';grab('overview')
        h.expression('openNetworkDevice(networkRows[0].id)');h.pump(80)
        selected=h.value('networkSelectedId');h.expression('activateKey(5)');h.pump(80)
        assert h.value('networkSelectedId')==selected,'Favourite removal must not replace the open detail'
        assert not h.value('networkSelected')['favourite']
        h.expression('activateKey(5)');h.pump(80);h.expression('back()');h.pump(80)
        h.expression('networkSelectedId=networkRows[0].id')
        checks.append('detailIdentityRetainedAfterFavouriteChange')
        h.expression('activateKey(2)');assert h.value('networkTabsSelected');h.expression('activateKey(6)');h.pump(180)
        assert h.value('activeContentId')=='network.devices';h.expression('activateKey(8)');h.expression('activateKey(5)');h.pump(180)
        assert h.value('overlay')=='networkDetail';grab('detail')
        for i in range(4):h.expression('activateKey(6)');h.expression('activateKey(8)');h.pump(50)
        h.expression('back()');h.expression('pushOverlay("networkSettings")');h.pump(180);grab('settings')
        h.expression('activateKey(8)');h.expression('activateKey(5)');assert not h.network.moduleState['data']['polling']
        h.expression('back()');h.root.setProperty('networkFilter',2);h.pump(50);grab('devices')
        # No favourites must not hide Rete; empty filter remains navigable.
        h.network._snapshot['preferences']['favourites']=[];h.network.changed.emit();h.pump(80)
        assert h.state.networkAvailable and not h.value('networkRows');h.expression('activateKey(2)');h.expression('activateKey(5)');h.pump(80)
        h.network._status='stale';h.network.changed.emit();h.root.setProperty('networkFilter',1);h.pump(80)
        assert not h.value('networkRows');h.root.setProperty('networkFilter',3);h.pump(80);assert len(h.value('networkRows'))==6;grab('previous')
        h.expression('openNetworkDevice(networkRows[0].id)');h.pump(80);assert h.value('networkSelected')['previous']
        # Many rows / long names / all address sections preserve stable selection.
        snap=demo_snapshot(h.now)
        for i in range(250):
            row=deepcopy(snap['devices'][i%6]);row['id']='synthetic-'+str(i);row['name']='Dispositivo con un nome molto lungo '+str(i);snap['devices'].append(row)
        h.network._snapshot=snap;h.network._status='active';h.network.changed.emit();h.expression('back()');h.root.setProperty('networkFilter',0);h.pump(80)
        h.root.setProperty('networkSelectedId',snap['devices'][-1]['id']);h.pump(80);assert h.value('networkSelected')['id']==snap['devices'][-1]['id'];grab('many-rows')
        checks+=['fourTypedSurfaces','keypadFocusAndTabs','filtersNoEmptyModule','detailSections','favouriteControls','manyHostsLongNames']
        assert not h.messages and not h.transport,(h.messages,h.transport)
        return {'status':'passed','profile':profile,'qt':qVersion(),'checks':checks,'warnings':h.messages}
    finally:
        for s in services:s.close()
        if h:h.close()
        private.cleanup()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--child');parser.add_argument('--capture');args=parser.parse_args()
    if args.child:print(json.dumps(verify(json.loads(args.child),args.capture),ensure_ascii=False))
    else:
        for theme,variant in [('base','day'),('functional','night')]:
            command=[sys.executable,__file__,'--child',json.dumps({'theme':theme,'variant':variant,'motion':'off'})]
            if args.capture:command+=['--capture',args.capture]
            result=subprocess.run(command,timeout=45,capture_output=True,text=True);print(result.stdout);print(result.stderr,file=sys.stderr);assert result.returncode==0
