#!/usr/bin/env python3
"""A0 semantic residual proofs with real Main and provider normalization.

Private XDG/store/SQLite, denied network, fixed domain clocks. No kiosk access.
Supplementary cases never inflate the canonical corpus requirement count.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

from theme_fixture_support import CORPUS, LegacyHarness, isolate_process


def main():
    private, base = isolate_process()
    harness = None
    try:
        from PySide6.QtCore import QDate, QDateTime, QTime, QObject
        from weather import normalize_response, WeatherService
        harness = LegacyHarness(base, {'theme': 'base', 'variant': 'day', 'motion': 'off'})
        results = []
        # The actual future-event service determines visibility; no UI stub.
        harness.events.set_demo_scenario('nessuno'); harness.pump()
        assert not harness.value('hasEvent')
        harness.events.set_demo_scenario('prossimo'); harness.pump()
        assert harness.value('hasEvent') and harness.value('nextEvent')['title'] == 'Allerta prevista'
        flags = harness.event_flags(); deadline = harness.events._banner_until
        assert harness.service.setToken('shape.radiusRow', 6)
        harness.wait_ready()
        assert harness.value('hasEvent') and harness.event_flags() == flags and harness.events._banner_until == deadline
        harness.now += 1801; harness.events._tick(); harness.pump()
        assert not harness.value('hasEvent'), 'Evento iniziato rimasto nello spazio prossimo evento'
        harness.now += 1801; harness.events._tick(); harness.pump()
        assert not harness.value('hasEvent'), 'Evento scaduto riapparso come prossimo'
        results.append({'id': 'home.next-event-boundaries', 'status': 'passed', 'scope': 'None/future/started/expired in actual EventService; appearance swap preserves flags/deadline'})
        for year, month, day, hour, minute, expected_time, expected_date in [
            (2026, 10, 4, 23, 59, '23:59', 'DOMENICA 4 OTTOBRE 2026'),
            (2026, 10, 5, 0, 0, '00:00', 'LUNEDÌ 5 OTTOBRE 2026'),
            (2026, 12, 31, 23, 59, '23:59', 'GIOVEDÌ 31 DICEMBRE 2026'),
            (2027, 1, 1, 0, 0, '00:00', 'VENERDÌ 1 GENNAIO 2027')]:
            harness.root.setProperty('now', QDateTime(QDate(year, month, day), QTime(hour, minute))); harness.pump()
            assert harness.expression('timeText()') == expected_time
            assert harness.expression('dateText()') == expected_date.lower(), (harness.expression('dateText()'), expected_date.lower())
            results.append({'id': f'home.clock-{year}-{month}-{day}-{hour}-{minute}', 'status': 'passed', 'expectedTime': expected_time, 'expectedDate': expected_date.lower()})
        raw = json.loads((CORPUS / 'domains/weather-zero.json').read_text())['raw']
        weather = WeatherService(auto_refresh=False)
        last_complete = normalize_response(raw)
        weather._on_finished(last_complete, None)
        persisted = weather._cache_path.read_bytes()
        fetched_at = weather._fetched_at
        incomplete = deepcopy(raw); incomplete['daily']['temperature_2m_max'] = incomplete['daily']['temperature_2m_max'][:1]
        try:
            normalize_response(incomplete)
        except ValueError as error:
            weather._on_finished(None, str(error))
        else:
            raise AssertionError('Forecast incompleto accettato')
        assert weather._snapshot == last_complete and len(weather._snapshot['forecast']) == 3
        assert weather._fetched_at == fetched_at and weather._cache_path.read_bytes() == persisted
        assert weather._last_error and weather.moduleState['status'] != 'active'
        results.append({'id': 'weather.partial-retains-complete', 'status': 'passed', 'scope': 'Actual normalization rejects incomplete daily arrays; WeatherService retains complete snapshot/cache/fetchedAt and truthful error state'})
        # All protected space blocked: app-owned actor remains and is paused.
        assert harness.service.setSection('scene', {'enabled': True, 'renderer': 'builtin.actor'})
        harness.wait_ready(); harness.pump()
        host, actor = harness.actor()
        host.setProperty('occupiedRegions', [{'x': 0, 'y': 0, 'width': 960, 'height': 640}]); harness.pump()
        assert host.property('regionBlocked') and actor.property('paused')
        assert not host.property('visible') and harness.actor() == (host, actor)
        host.setProperty('occupiedRegions', []); harness.pump()
        assert not host.property('regionBlocked') and harness.actor() == (host, actor)
        results.append({'id': 'scene.full-protected-region', 'status': 'passed', 'scope': 'Actor identity survives full collision and unblock; blocked scene pauses and hides'})
        assert not harness.transport, 'Network access during isolated residual fixtures'
        assert not harness.messages, harness.messages
        print(json.dumps({'reportVersion': 1, 'status': 'passed', 'scenarios': results,
                          'isolation': {'privateXdg': True, 'privateStore': True, 'privateSQLite': True, 'networkDeniedPositiveControl': True},
                          'scope': 'Supplementary semantic residuals, not complete public-API binding or board performance acceptance.'}, ensure_ascii=False))
    finally:
        if harness: harness.close()
        private.cleanup()


if __name__ == '__main__':
    main()
