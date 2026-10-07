"""Canonical settings IDs and truthful actions through the actual Main broker.

Runs with private preferences/SQLite and seeded offline services. This covers the
public data and application-owned behavior an AI settings renderer consumes;
it does not measure GPU performance or physical keypad presses.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch

from theme_fixture_support import isolate_process,LegacyHarness


def verify():
    private,base=isolate_process();harness=None
    try:
        from PySide6.QtCore import QObject
        from theme_contexts import CONTRACT
        harness=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
        factory=harness.service.apiFactory
        contexts=[];issues=[];factory.diagnostic.connect(lambda code,message:issues.append((code,message)))
        settings=harness.root.findChild(QObject,'settingsPanel')

        def context(surface):
            route=CONTRACT.surfaces[surface]['legacyRoute']
            harness.root.setProperty('overlay',route)
            harness.pump(30)
            value=factory.create(surface);contexts.append(value)
            update(value)
            return value

        def update(value):
            payload=harness.expression('publicSurfacePayload('+json.dumps(value.contentId)+')')
            payload.update(active=True,interactive=True,viewportWidth=960,viewportHeight=640)
            assert factory.updateLegacy(value,payload),(value.contentId,issues)

        def ids(value):return [value.rows.get(i).id for i in range(value.rows.count)]
        def row(value,identity):
            return next(value.rows.get(i) for i in range(value.rows.count) if value.rows.get(i).id == identity)
        def request(value,action,target='',arguments=None):
            result=value.requestAction(action,target,arguments or {})
            assert result.status in ('pending','completed','failed','rejected')
            return result

        # Documented IDs must work even when display labels and legacy targets
        # differ, and no renderer receives a private controller/model.
        index=context('settings.index')
        assert ids(index)==['appearance','display','modules','notifications','account','integrations','casa','sources']
        assert all(index.rows.get(i).enabled for i in range(index.rows.count))
        assert request(index,'settings.activate','display').status=='completed'
        assert harness.value('overlay')=='system'
        display=context('settings.display')
        assert ids(display)==['display.mode','display.manualBrightness','display.dayBrightness','display.nightBrightness','display.dayStart','display.nightStart']
        mode=row(display,'display.mode')
        assert mode.enabled and mode.control=='choice' and mode.options.count==2
        assert mode.value.value=='manual'
        assert request(display,'settings.adjust','display.mode',{'direction':1}).status=='completed'
        assert harness.state.brightnessMode=='auto'
        update(display)
        assert not row(display,'display.manualBrightness').enabled
        before=harness.state.manualBrightness
        assert request(display,'settings.adjust','display.manualBrightness',{'direction':-1}).status=='failed'
        assert harness.state.manualBrightness==before
        day=row(display,'display.dayBrightness')
        assert day.control=='number' and (day.minimum,day.maximum,day.step)==(20,100,5)
        assert day.value.value==harness.state.dayBrightness
        before=harness.state.dayBrightness
        assert request(display,'settings.adjust','display.dayBrightness',{'direction':-1}).status=='completed'
        assert harness.state.dayBrightness==max(20,before-5)

        modules=context('settings.modules')
        assert ids(modules)==['module.'+family['id'] for family in harness.value('allFamilies')]
        assert not row(modules,'module.oggi').enabled
        old=harness.state.visibleModules
        assert request(modules,'settings.adjust','module.meteo',{'direction':1}).status=='completed'
        assert ('meteo' in harness.state.visibleModules)!=('meteo' in old)
        # Remove the first conditional integration and prove ID-to-index lookup
        # still opens MotoGP rather than the adjacent entry.
        integrations=context('settings.integrations')
        assert ids(integrations)==['integration.sport','integration.f1','integration.motogp']
        assert request(integrations,'settings.activate','integration.motogp').status=='completed'
        assert harness.value('overlay')=='racingSettings' and harness.value('racingSettingsKind')=='motogp'
        racing=context('settings.racing')
        assert ids(racing)==['racing.motogp.season','racing.motogp.showOnHome','racing.motogp.source']
        before=harness.racing['motogp'].moduleState['data']['showOnHome']
        assert request(racing,'settings.adjust','racing.motogp.showOnHome',{'direction':1}).status=='completed'
        assert harness.racing['motogp'].moduleState['data']['showOnHome']!=before
        sport=context('settings.sport')
        assert ids(sport)==['sport.favouriteTeam','sport.showOnHome','sport.notifications','sport.season','sport.source']
        assert row(sport,'sport.notifications').actionId=='settings.activate'
        assert request(sport,'settings.adjust','sport.notifications',{'direction':1}).status=='failed'

        notification_rules=context('settings.notifications')
        assert ids(notification_rules)==['notifications.quiet','notifications.categories']
        assert request(notification_rules,'settings.activate','notifications.quiet').status=='completed'
        assert harness.value('overlay')=='notificationQuiet'
        quiet=context('settings.notifications.quiet')
        assert ids(quiet)==['notifications.quiet.enabled','notifications.quiet.start','notifications.quiet.end']
        old=harness.state.quietHoursEnabled
        assert request(quiet,'settings.adjust','notifications.quiet.enabled',{'direction':1}).status=='completed'
        assert harness.state.quietHoursEnabled!=old
        update(quiet)
        assert row(quiet,'notifications.quiet.start').enabled==harness.state.quietHoursEnabled
        assert (row(quiet,'notifications.quiet.start').minimum,row(quiet,'notifications.quiet.start').maximum,row(quiet,'notifications.quiet.start').step)==(0,1439,15)
        categories=context('settings.notifications.categories')
        assert ids(categories)==['notifications.weatherInterruptions','notifications.accountInterruptions','notifications.sportGoals']
        assert not row(categories,'notifications.sportGoals').enabled
        old=harness.state.weatherInterruptions
        assert request(categories,'settings.adjust','notifications.weatherInterruptions',{'direction':1}).status=='completed'
        assert harness.state.weatherInterruptions!=old
        account=context('settings.account')
        assert ids(account)==['account.warningThreshold','account.criticalThreshold']
        old=harness.state.accountWarningPercent
        assert request(account,'settings.adjust','account.warningThreshold',{'direction':-1}).status=='completed'
        assert harness.state.accountWarningPercent==max(1,old-5)

        sources=context('settings.sources')
        assert row(sources,'source.weather').targetId=='meteo'
        assert row(sources,'source.weather').actionId=='sources.refresh'
        assert row(sources,'source.weather').enabled
        # Both generic row activation and explicit public source requests must
        # return failure when the backend cooldown declines the refresh.
        with patch.object(harness.state,'refreshSource',return_value=False):
            assert request(sources,'settings.activate','source.weather').status=='failed'
            assert request(sources,'sources.refresh','meteo').status=='failed'

        appearance=context('settings.appearance')
        assert ids(appearance)==['appearance.palette','appearance.motion','appearance.theme','appearance.textScale','appearance.revision',
            'appearance.apply','appearance.cancel','appearance.import','appearance.export','appearance.advanced']
        assert appearance.draft.editing==harness.service.editing
        assert appearance.draft.readyToApply==harness.service.readyToApply
        assert row(appearance,'appearance.textScale').step==.05
        assert not row(appearance,'appearance.revision').enabled
        harness.reset_effects();domain_before=deepcopy(harness.state.eventsState)
        assert request(appearance,'settings.adjust','appearance.textScale',{'direction':1}).status=='completed'
        assert harness.service.draft['overrides']['tokens']['typography.textScale']==1.05
        update(appearance)
        assert appearance.draft.textScale==1.05 and appearance.draft.readyToApply
        assert not any(harness.effects.values()) and harness.state.eventsState==domain_before
        with patch('theme_service.QThreadPool'):
            saving=request(appearance,'settings.activate','appearance.apply')
        assert saving.accepted and saving.status=='pending','generic Apply must await persistence result'
        update(appearance)
        assert appearance.operation.status=='pending' and not appearance.draft.readyToApply
        assert not row(appearance,'appearance.textScale').enabled
        assert request(appearance,'appearance.cancel').status=='failed'
        harness.service._saved(False,'synthetic preference write fault')
        assert saving.status=='failed' and saving.errorCode=='synthetic preference write fault'
        update(appearance)
        assert appearance.operation.status=='failed' and appearance.draft.editing
        assert appearance.draft.textScale==1.05 and appearance.draft.error=='synthetic preference write fault'

        for operation in ('import','export'):
            with patch('theme_service.QThreadPool'):
                result=request(appearance,'settings.activate','appearance.'+operation)
            assert result.status=='pending',operation
            harness.service._pack_finished(False,'synthetic '+operation+' fault')
            assert result.status=='failed',operation
            update(appearance)
        assert request(appearance,'settings.activate','appearance.advanced').status=='completed'
        update(appearance)
        assert settings.property('advancedAppearance') and row(appearance,'appearance.cardRadius').control=='number'
        assert request(appearance,'settings.adjust','appearance.cardRadius',{'direction':1}).status=='completed'
        assert request(appearance,'settings.activate','appearance.simple').status=='completed'
        update(appearance)
        assert not settings.property('advancedAppearance') and appearance.rows.count==10

        notifications=context('settings.appearance.notifications')
        assert notifications.rows.count==25
        assert row(notifications,'notifications.visual.mode').value.value=='small'
        assert request(notifications,'settings.adjust','notifications.visual.mode',{'direction':1}).status=='completed'
        update(notifications)
        assert row(notifications,'notifications.visual.mode').value.value=='large'
        assert request(notifications,'settings.adjust','notifications.visual.padding',{'direction':1}).status=='completed'
        assert 'notifications.large.padding' in harness.service.draft['overrides']['tokens']
        assert request(notifications,'settings.activate','notifications.visual.reset').status=='completed'
        assert 'notifications.large.padding' not in harness.service.draft['overrides'].get('tokens',{})

        # Filtering a conditionally unavailable provider cannot shift canonical
        # integration/source IDs. Evaluate the same private mapping with the
        # real QML module and deliberately filtered source rows.
        filtered=harness.expression('PublicSettingsRows.canonicalize("settings.integrations",[{target:"motogp",title:"MotoGP"}],{})')
        assert filtered[0]['id']=='integration.motogp'
        busy=harness.expression('PublicSettingsRows.canonicalize("settings.racing",[{title:"Stagione"}],{racingKind:"f1",racing:{detailLoading:true}})')
        assert busy[0]['id']=='racing.f1.season' and not busy[0]['enabled']
        for value in contexts:
            assert value.metaObject().indexOfProperty('controller')<0
            assert value.metaObject().indexOfProperty('model')<0
        assert not issues,issues
        assert not harness.messages,harness.messages
        assert not harness.transport,harness.transport
        return {'status':'passed','settingsSurfaces':len({value.contentId for value in contexts}),
            'checks':['canonicalConditionalIds','displayAdjustmentAndDisabledGuard','numericRangesAndChoices','moduleVisibility',
                'kindQualifiedRacingSetting','sourceCooldownFailure','draftMetadata','genericApplyAwaited','importExportAwaited',
                'advancedSimpleRoundTrip','notificationRolesAndReset','noPrivateHandles','noProviderEffectsFromAppearance'],
            'qmlWarnings':harness.messages,'scope':'Actual Main public broker, isolated settings/events/providers; board performance not verified'}
    finally:
        if harness is not None:harness.close()
        private.cleanup()


if __name__=='__main__':
    report=verify()
    if len(sys.argv)==2:Path(sys.argv[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))
