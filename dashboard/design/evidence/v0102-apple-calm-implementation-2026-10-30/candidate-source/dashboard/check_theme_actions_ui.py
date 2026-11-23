"""Public actions against actual Main routing and seeded offline providers."""
import json
from pathlib import Path
import sys
from unittest.mock import patch
from theme_fixture_support import isolate_process, LegacyHarness


def verify():
    private,base=isolate_process();harness=None
    try:
        from theme_contexts import CONTRACT
        harness=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
        factory=harness.service.apiFactory;contexts=[];issues=[];records=[]
        factory.diagnostic.connect(lambda *args:issues.append(args))
        def context(surface):
            value=factory.create(surface);contexts.append(value)
            payload=harness.expression('publicSurfacePayload('+json.dumps(surface)+')')
            payload.update(active=True,interactive=True,viewportWidth=960,viewportHeight=640,
                model={key:harness.value(key) for key in ('weather','account','sport','racing','nextEvent')})
            assert factory.updateLegacy(value,payload),(surface,issues)
            return value
        def request(value,action,target='',args=None):
            return value.requestAction(action,target,args or {})
        for family,surface in [('oggi','home.now'),('meteo','weather.now')]:
            harness.root.setProperty('familyId',family);harness.root.setProperty('overlay','');harness.pump()
            value=context(surface)
            assert value.selection.selectedId==surface
            assert request(value,'details.open','invented').status=='failed'
            assert harness.value('overlay')==''
            assert request(value,'details.open',value.selection.selectedId).status=='completed'
            assert harness.value('overlay')=='detail'
            records.append(surface+'.details')
        harness.root.setProperty('familyId','sport');harness.root.setProperty('overlay','sportList');harness.pump()
        fixtures=context('sport.fixtures')
        assert fixtures.selection.tabId=='sport.fixtures'
        assert request(fixtures,'tabs.select','sport.standings').status=='completed'
        assert harness.value('overlay')=='sportTable'
        standings=context('sport.standings')
        assert standings.selection.tabId=='sport.standings'
        assert request(standings,'tabs.select','sport.fixtures').status=='completed'
        records.append('sport.list-tabs')
        harness.setup({'id':'action-racing','surfaceId':'racing.session.detail','variant':'normal',
            'domainSetup':['racing:f1'],'initialProperties':{'overlay':'racingSession'}})
        session=context('racing.session.detail')
        rows=harness.value('racingSession')['results'];assert len(rows)>1
        assert session.selection.tabId=='RISULTATI'
        assert request(session,'selection.select',rows[1]['id']).status=='completed'
        assert harness.value('racingResultIndex')==1
        assert request(session,'details.open',rows[1]['id']).status=='completed'
        assert harness.value('overlay')=='racingDriver'
        assert harness.value('racingDriverId')==rows[1]['id']
        driver=context('racing.driver.detail')
        assert driver.selection.tabId==harness.value('racingDriverTabs')[harness.value('racingDriverPage')]
        assert driver.selection.count==len(harness.value('racingDriverRows'))
        records.append('racing.session-driver-identity')
        harness.root.setProperty('overlay','racingSession');harness.pump();session=context('racing.session.detail')
        assert request(session,'tabs.select','SESSIONE').status=='completed'
        session=context('racing.session.detail');assert session.selection.tabId=='SESSIONE'
        assert session.selection.count==len(harness.value('racingInfoRows'))
        records.append('racing.selected-tab-and-info-rows')
        harness.root.setProperty('overlay','info');harness.pump();info=context('device.info')
        assert request(info,'tabs.select','RISORSE').status=='completed'
        info=context('device.info');assert info.selection.tabId=='RISORSE'
        records.append('info.selected-tab')
        # App-owned source aliases route the canonical public source identity.
        with patch.object(harness.state,'refreshSource',return_value=True) as refresh:
            assert harness.expression('publicDispatch({contentId:"settings.sources"},"sources.refresh","weather",{})')
            refresh.assert_called_once_with('meteo')
        harness.root.setProperty('overlay','commands');harness.pump();commands=context('overlay.commands')
        for i in range(commands.keyMap.count):
            command=commands.keyMap.get(i)
            if command.actionId in ('details.open','selection.select','settings.activate','tabs.select'):
                assert command.targetId,'invalid executable command target'
        assert request(commands,commands.keyMap.get(4).actionId,commands.keyMap.get(4).targetId).status=='completed'
        records.append('commands.no-invalid-empty-target')
        assert not harness.messages,harness.messages
        assert not harness.transport,harness.transport
        for value in contexts:factory.release(value)
        report={'status':'passed','checks':records,'qmlWarnings':harness.messages,
            'apiFingerprint':CONTRACT.fingerprint,'scope':'Actual Main broker, private providers/store, synthetic selection and Qt events; not physical HID.'}
        if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
    finally:
        if harness:harness.close()
        private.cleanup()

if __name__=='__main__':verify()
