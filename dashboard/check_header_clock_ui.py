"""Real Main: persistent header time and uniform software dimming, offline.

Runs with private preferences/providers on both PC/offscreen and board/EGLFS.
Pixel comparisons prove that the actual header follows the dimming layer.
"""
from pathlib import Path
import argparse
import json
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', choices=('base', 'functional', 'apple'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from theme_fixture_support import isolate_process, LegacyHarness, ROOT
    private, base = isolate_process()
    from PySide6.QtCore import QObject, QDate, QTime, QDateTime
    if args.theme == 'apple':
        from theme_bundle import BundleManager, validate_project
        from PySide6.QtCore import qVersion
        bundle = ROOT.parent / 'theme-projects/apple-calm/bundle'
        cache = json.loads((bundle.parent / 'evidence/preflight-cache.json').read_text())
        assert cache['digest'] == validate_project(bundle)['digest']
        assert cache['result']['status'] == 'passed' and cache['result']['qt'] == qVersion()
        BundleManager(base).import_bundle(bundle, preflight=lambda *_: cache['result'], require_preflight=True)
    h = LegacyHarness(base, dict(theme='base' if args.theme == 'apple' else args.theme,
                                variant='day', motion='off', game=True))
    rows = []
    try:
        if args.theme == 'apple':
            assert h.service.selectDraft('studio.applecalm'), h.service.lastError
            h.wait_ready()
        from theme_test_support import wait_save
        deadline = time.monotonic() + 5
        while not h.service.readyToApply and time.monotonic() < deadline:
            h.pump(20)
        assert h.service.apply(), h.service.lastError
        wait_save(h.app, h.service)
        dim = h.root.findChild(QObject, 'dimmingLayer')
        assert dim is not None
        assert all(item.z() < dim.property('z') for item in h.window.contentItem().childItems() if item != dim)

        def clock():
            if args.theme == 'apple':
                assert h.service.activeThemeId == 'studio.applecalm', (h.service.activeThemeId, h.service.lastError)
                # PageHost publishes the presented route with Qt.callLater;
                # the old page remains until that route has been presented.
                h.pump(40)
            found = [item for item in h.root.findChildren(QObject, 'headerClock') if item.property('visible')]
            if args.theme == 'apple' and h.value('activeContentId') in ('home.now', 'home.clock') and not h.value('overlay'):
                assert not found, 'The Apple Calm Home clock is duplicated in the header'
                found = [item for item in h.root.findChildren(QObject, 'dominantClock') if item.property('visible')]
            assert len(found) == 1, ([item.objectName() for item in found], h.value('activeContentId'), h.value('overlay'))
            assert found[0].property('text') == h.expression('timeText()')
            assert found[0].property('truncated') is False
            return found[0]

        def stamp(day, hour, minute):
            h.root.setProperty('now', QDateTime(QDate(2026, 10, day), QTime(hour, minute)))
            h.pump(50)

        for family in [row['id'] for row in h.value('families')] + ['sport', 'f1', 'motogp']:
            h.root.setProperty('familyId', family)
            h.wait_ready()
            count = h.expression('currentFamily.views.length')
            for view in range(count):
                if view:
                    h.expression('navigateView(1)')
                    h.wait_ready()
                item = clock()
                rows.append(dict(family=family, view=h.expression('viewName()'), time=item.property('text')))
        h.root.setProperty('familyId', 'oggi')
        h.wait_ready()
        stamp(22, 23, 59)
        assert clock().property('text') == '23:59'
        stamp(23, 0, 0)
        assert clock().property('text') == '00:00'

        # Compact external overlays reserve the same header.
        if args.theme == 'apple':
            for route in ('menu', 'settings', 'info', 'alerts'):
                h.expression('pushOverlay(' + json.dumps(route) + ')')
                h.wait_ready()
                clock()
                h.expression('activateKey(1)')
                h.wait_ready()
            h.state._quiet_enabled = True
            h.state._quiet_start, h.state._quiet_end = 0, 60
            h.state.settingsChanged.emit()
            h.pump(60)
            assert h.value('quietActive')
            statuses = [item for item in h.root.findChildren(QObject, 'headerStatus') if item.property('visible')]
            assert statuses, (h.service.activeThemeId, h.service.lastError,
                              [(item.property('text'), item.property('visible')) for item in h.root.findChildren(QObject, 'headerStatus')])
            status = statuses[0]
            assert status.property('text') == 'Quiete' and not status.property('truncated')
            clock()
            h.events.set_demo_scenario('prossimo')
            h.pump(120)
            badge = h.root.findChild(QObject, 'unreadAlertsBadge')
            if badge.property('visible'):
                assert badge.x() + badge.width() <= 796
            h.window.grabWindow().save(str(args.output / 'quiet-header.png'))
            h.state._quiet_enabled = False
            h.state.settingsChanged.emit()
        # Compare actual submitted pixels at two unchanged canvas positions.
        h.events.set_demo_scenario('nessuno')
        h.pump(60)
        brightness = []
        h.service.beginEdit()
        for variant in ('day', 'night'):
            assert h.service.setSection('paletteMode', variant)
            h.wait_ready()
            assert h.value('night') == (variant == 'night')
            h.state._manual_brightness = 100
            h.state.settingsChanged.emit()
            h.pump(80)
            bright = h.window.grabWindow()
            assert not bright.isNull()
            bright.save(str(args.output / (variant + '-100.png')))
            for percent in (50, 20):
                h.state._manual_brightness = percent
                h.state.settingsChanged.emit()
                h.pump(80)
                image = h.window.grabWindow()
                assert abs(dim.property('opacity') - (1 - percent / 100)) < .001
                samples = []
                for x, y in ((10, 30), (10, 300)):
                    original = bright.pixelColor(x, y).getRgb()[:3]
                    actual = image.pixelColor(x, y).getRgb()[:3]
                    assert max(original) > 0
                    assert all(abs(a - b * percent / 100) <= 2 for a, b in zip(actual, original)), (variant, percent, x, y, original, actual)
                    samples.append(dict(position=[x, y], bright=original, dimmed=actual))
                clock()
                image.save(str(args.output / (variant + '-' + str(percent) + '.png')))
                brightness.append(dict(variant=variant, percent=percent, samples=samples))
        # The solar palette is separate from the saved hours for dimming.
        h.state._brightness_mode = 'auto'
        h.state._day_brightness, h.state._night_brightness = 100, 35
        h.state.settingsChanged.emit()
        assert h.service.setSection('paletteMode', 'auto')
        h.wait_ready()

        def display(day, hour, minute, night, percent):
            stamp(day, hour, minute)
            h.wait_ready()
            assert h.value('night') == night, (day, hour, minute, night)
            assert h.value('brightnessPercent') == percent, (day, hour, minute, percent)
            assert abs(dim.property('opacity') - (1 - percent / 100)) < .001

        display(23, 12, 0, False, 100)
        display(23, 20, 59, True, 100)
        display(23, 21, 0, True, 35)
        display(24, 0, 0, True, 35)
        h.state._day_start_hour = 10
        h.state.settingsChanged.emit()
        display(24, 6, 0, True, 35)
        display(24, 9, 0, False, 100)

        from datetime import date
        from math import ceil
        from solar_time import daylight_bounds
        from weather import LATITUDE, LONGITUDE
        for day in (date(2026, 6, 21), date(2026, 10, 25), date(2026, 12, 21)):
            sunrise, sunset = daylight_bounds(day, LATITUDE, LONGITUDE)
            for boundary, night in ((sunrise, False), (sunset, True)):
                transition_minute = ceil(boundary / 60)
                for offset, expected in ((-1, not night), (0, night)):
                    h.root.setProperty('now', QDateTime.fromSecsSinceEpoch((transition_minute + offset) * 60))
                    h.pump(50)
                    h.wait_ready()
                    assert h.value('night') == expected, (day, night, offset)

        assert h.service.setSection('paletteMode', 'day')
        h.wait_ready()
        display(24, 23, 0, False, 100)
        assert h.service.setSection('paletteMode', 'night')
        h.wait_ready()
        display(24, 12, 0, True, 100)
        clock()
        assert not h.messages, h.messages
        report = dict(status='passed', theme=args.theme, window=[h.window.width(), h.window.height()],
                      navigation=rows, midnight=True, automaticBrightness=True, dimming=brightness,
                      allRootLayersDimmed=True, qmlWarnings=h.messages)
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(status='passed', theme=args.theme, views=len(rows))), flush=True)
    finally:
        h.close()
        private.cleanup()


if __name__ == '__main__':
    main()
