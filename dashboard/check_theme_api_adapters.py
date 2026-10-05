"""Actual Main/provider adapter coverage, isolated and offline, all 44 surfaces.

This proves canonical normalization of the real private QML payloads, alongside
independent weather/score/account oracles. It does not replace the full variant
corpus, visual screenshots or physical-board performance gates.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

from theme_fixture_support import isolate_process, LegacyHarness


def verify():
    private, base = isolate_process()
    harness = None
    try:
        from theme_api import PublicContextFactory
        from theme_contexts import CONTRACT
        from PySide6.QtCore import QCoreApplication, QEvent
        harness = LegacyHarness(base, {'theme': 'base', 'variant': 'day', 'motion': 'off'})
        factory = PublicContextFactory()
        issues = []
        factory.diagnostic.connect(lambda code, message: issues.append({'code': code, 'message': message}))
        records = []
        actual_match = harness.seed['fixtures'][0]
        actual_id = actual_match['canonicalMatchId']
        harness.root.setProperty('sportMatchId', actual_id)
        for surface_id, surface in CONTRACT.surfaces.items():
            if surface_id.startswith('racing.'):
                harness.root.setProperty('familyId', 'f1')
                event = harness.value('racingData')['events'][0]
                harness.root.setProperty('racingEventId', event['id'])
                if event.get('sessions'):
                    harness.root.setProperty('racingSessionId', event['sessions'][0]['id'])
            else:
                harness.root.setProperty('familyId', 'sport' if surface_id.startswith('sport.') else 'oggi')
            harness.root.setProperty('overlay', surface.get('legacyRoute') or '')
            payload = harness.expression('publicSurfacePayload(' + json.dumps(surface_id) + ')')
            payload.update({'model': {key: harness.value(key) for key in ['weather', 'account', 'sport', 'racing', 'nextEvent']},
                            'epoch': harness.now, 'active': True, 'interactive': False,
                            'viewportWidth': 960, 'viewportHeight': 640})
            harness.reset_effects()
            navigation_before = {name: harness.value(name) for name in harness.KEPT}
            events_before = deepcopy(harness.state.eventsState)
            context = factory.create(surface_id)
            begin = time.perf_counter_ns()
            assert factory.updateLegacy(context, payload), (surface_id, issues)
            elapsed = (time.perf_counter_ns() - begin) / 1e6
            assert {name: harness.value(name) for name in harness.KEPT} == navigation_before
            assert harness.state.eventsState == events_before
            assert not any(harness.effects.values()), harness.effects
            assert not harness.transport, harness.transport
            checks = []
            if surface_id in ('home.now', 'home.day', 'weather.now', 'weather.forecast'):
                assert context.weather.temperature.available
                assert context.weather.temperature.value == 0
                assert context.weather.temperature.displayText == '0°'
                assert context.weather.forecast.count == 3
                checks.append('weatherZeroAndDatedForecast')
            if surface_id == 'account.usage':
                window = context.account.windows.get(0)
                assert window.usedPercent.available and window.usedPercent.value == 0
                assert window.windowDurationMinutes.value == 300
                assert window.resetsAt == harness.now + 3600
                checks.append('accountZeroDurationAndReset')
            if surface_id == 'sport.match.detail':
                assert context.match.id == actual_id
                for side in ('home', 'away'):
                    value = actual_match.get(side + 'Score')
                    dto = getattr(context.match, side + 'Score')
                    assert dto.available == (value is not None)
                    assert dto.value == value
                checks.append('actualMatchIdentityAndNullableScores')
            if surface_id in ('sport.overview', 'sport.fixtures'):
                matches = context.sport.matches if surface_id == 'sport.overview' else context.matches
                assert matches.count == len(harness.value('sportData')['fixtures'])
                assert matches.get(0).id == actual_id
                checks.append('actualFootballFixtureModel')
            if surface_id in ('racing.event.detail', 'racing.session.detail'):
                assert context.event.id == event['id']
                if surface_id == 'racing.session.detail' and event.get('sessions'):
                    assert context.session.id == event['sessions'][0]['id']
                checks.append('actualRacingEventSessionIdentity')
            if surface_id == 'shell.main':
                assert context.families.count == len(harness.value('families'))
                assert context.navigation.familyCount == context.families.count
                assert context.navigation.familyPosition == harness.value('family') + 1
                assert context.navigation.viewId == harness.value('activeContentId')
                assert context.navigation.viewCount > 0 and context.navigation.viewPosition > 0
                assert context.layout.header.height == 90
                assert context.layout.content.width == 872 and context.layout.content.height == 455
                assert context.layout.guide.y == 558
                assert context.uiStatus.urgent == bool(harness.value('urgentEvent').get('id'))
                assert context.uiStatus.night == harness.value('night')
                checks.append('actualShellNavigationLayoutAndStatus')
            if surface_id == 'overlay.commands':
                assert context.keyMap.count == 9
                assert [context.keyMap.get(index).key for index in range(9)] == list(range(1,10))
                assert context.keyMap.get(8).actionId == 'navigation.menu'
                assert all(context.keyMap.get(index).id and context.keyMap.get(index).enabled for index in range(9))
                checks.append('actualNineKeyCommandMap')
            records.append({'surface': surface_id, 'context': surface['context'], 'status': 'passed',
                            'independentSemanticChecks': checks, 'normalizeMsDevelopmentHost': elapsed})
            factory.release(context)
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        assert not issues, issues
        assert not harness.messages, harness.messages
        return {'status': 'passed', 'scope': 'Real Main private payload normalization; independent domain checks and no provider/event/navigation effects',
                'apiFingerprint': CONTRACT.fingerprint, 'surfaces': records, 'contexts': len(CONTRACT.contexts),
                'warnings': harness.messages, 'issues': issues, 'boardPerformanceVerified': False}
    finally:
        if harness is not None:
            harness.close()
        private.cleanup()


if __name__ == '__main__':
    report = verify()
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'surfaces': len(report['surfaces']), 'contexts': report['contexts'],
                      'warnings': report['warnings'], 'apiFingerprint': report['apiFingerprint']}))
