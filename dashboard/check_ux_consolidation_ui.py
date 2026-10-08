"""0.8.3 real keypad routes, settings identities and preference migration; offline."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from theme_fixture_support import LegacyHarness, isolate_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='base:day:off')
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args()
    private, base = isolate_process()
    h = None
    results = []
    try:
        from PySide6.QtCore import QSettings
        from state import DashboardState
        theme, variant, motion = args.profile.split(':')
        h = LegacyHarness(base, {'theme': theme, 'variant': variant, 'motion': motion})

        def press(key):
            h.expression('activateKey(' + str(key) + ')')
            h.wait_ready()
            h.pump(35)

        def capture(name):
            if args.capture_dir:
                args.capture_dir.mkdir(parents=True, exist_ok=True)
                image = h.window.grabWindow()
                assert image.width() == 960 and image.height() == 640
                assert image.save(str(args.capture_dir / (name + '.png')))

        assert [x['id'] for x in h.value('families')] == ['oggi', 'meteo', 'account', 'sports', 'casa', 'network']
        assert [x['id'] for x in h.value('sportDisciplines')] == ['sport', 'f1', 'motogp']
        press(1)
        for _ in range(3):
            press(6)
        assert h.value('familyId') == 'sports'
        assert h.expression('navigationSnapshot().familyId') == 'sports'
        capture('sport-index')
        h.reset_effects()
        press(8)
        press(5)
        assert h.value('familyId') == 'f1'
        press(6)
        saved_view = h.expression('racingView')
        assert h.expression('navigationSnapshot().familyId') == 'sports'
        h.root.setProperty('racingIndex', 2)
        selected_event=h.expression('racingRows[2].id')
        h.root.setProperty('racingFocusedId', selected_event)
        press(7)
        assert h.value('familyId') == 'sports' and h.value('sportHubSelectedId') == 'f1'
        press(8)
        press(5)
        assert h.value('familyId') == 'motogp' and h.value('racingIndex') == 0
        press(7)
        press(2)
        press(5)
        assert h.value('familyId') == 'f1' and h.expression('racingView') == saved_view
        assert h.value('racingFocusedId') == selected_event
        assert not any(h.effects.values()) and not h.transport, (h.effects, h.transport)
        results.append('single-sport-carousel-keypad-back-and-independent-branch-memory-without-provider-io')
        press(5)
        h.root.setProperty('racingIndex',2)
        selected_event=h.expression('racingRows[2].id')
        press(7);press(7)
        assert h.value('familyId')=='sports'
        press(5);press(5)
        assert h.expression('racingRows[racingIndex].id')==selected_event
        press(7)
        results.append('discipline-list-selection-restored-after-index-round-trip')
        press(7)
        h.state.toggleModuleVisibility('f1')
        h.wait_ready()
        assert 'f1' not in [x['id'] for x in h.value('sportDisciplines')]
        assert h.expression('openSportDiscipline("f1")') is False
        legacy = {k: v for k, v in h.state.moduleVisibility.items() if k != 'sports'}
        h.state.toggleModuleVisibility('sports')
        h.wait_ready()
        assert h.value('familyId') == 'oggi'
        assert 'sports' not in [x['id'] for x in h.value('families')]
        assert {k: v for k, v in h.state.moduleVisibility.items() if k != 'sports'} == legacy
        h.state.toggleModuleVisibility('sports')
        h.state.toggleModuleVisibility('f1')
        h.wait_ready()
        results.append('macro-visibility-preserves-hidden-disciplines-and-rejects-hidden-routes')
        # Six settings categories, all new routes and stable identities on moved controls.
        press(9)
        h.root.setProperty('menuIndex', 1)
        press(5)
        assert h.value('settingsItems') == ['Schermo', 'Aspetto', 'Moduli e Home', 'Avvisi', 'Servizi collegati', 'Dati e aggiornamenti']
        capture('settings-index')
        h.root.setProperty('settingsIndex', 0)
        press(5)
        rows = h.expression('publicSurfacePayload("settings.display").rows')
        assert len(rows) == 9 and len({row['id'] for row in rows}) == 9
        text = next(row for row in rows if row['id'] == 'appearance.textScale')
        assert text['control'] == 'number' and text['actionId'] == 'settings.adjust'
        h.root.setProperty('systemIndex', 6)
        initial_scale = h.service.resolvedAppearance['tokens']['typography.textScale']
        press(4)
        assert h.service.editing and h.service.resolvedAppearance['tokens']['typography.textScale'] < initial_scale
        capture('display-text-preview')
        h.root.setProperty('systemIndex', 8)
        press(5)
        assert h.service.resolvedAppearance['tokens']['typography.textScale'] == initial_scale
        press(7)
        h.root.setProperty('settingsIndex', 1)
        press(5)
        rows = h.expression('publicSurfacePayload("settings.appearance").rows')
        assert not {'appearance.textScale', 'appearance.import', 'appearance.export'} & {row['id'] for row in rows}
        assert 'appearance.management' in {row['id'] for row in rows}
        h.root.setProperty('optionIndex', next(i for i, row in enumerate(rows) if row['id'] == 'appearance.management'))
        press(5)
        assert h.value('overlay') == 'themeManagement'
        rows = h.expression('publicSurfacePayload("settings.appearance.management").rows')
        assert [row['id'] for row in rows] == ['appearance.revision', 'appearance.import', 'appearance.export', 'appearance.reload']
        assert rows[1]['control'] == 'transfer' and rows[1]['actionId'] == 'appearance.import'
        press(7)
        assert h.expression('settingsPanel.rows[optionIndex].id') == 'appearance.management'
        press(7)
        h.root.setProperty('settingsIndex', 4)
        press(5)
        capture('connected-services')
        assert [row['id'] for row in h.expression('publicSurfacePayload("settings.services").rows')] == ['service.account', 'service.casa', 'service.network']
        h.root.setProperty('optionIndex', 1)
        press(5)
        assert h.value('overlay') == 'casaSettings'
        press(7)
        h.root.setProperty('optionIndex', 2)
        press(5)
        assert h.value('overlay') == 'networkSettings'
        press(1)
        results.append('six-settings-groups-display-preview-cancel-canonical-transfer-and-connected-services-routes')
        # A deleted match must not turn into a different selected match.
        h.root.setProperty('familyId', 'sport')
        h.root.setProperty('sportView', 'RISULTATI')
        press(5)
        press(5)
        assert h.value('overlay') == 'sportDetail'
        selected = h.value('sportMatchId')
        h.sport._snapshot['fixtures'] = [row for row in h.sport._snapshot['fixtures'] if row['canonicalMatchId'] != selected]
        h.sport.changed.emit()
        h.wait_ready()
        assert h.value('sportMatch') == {}, 'removed detail changed identity'
        results.append('removed-selected-record-becomes-unavailable-without-substitution')
        press(1)
        # Migration runs the real constructor for legacy visibility combinations.
        settings = QSettings('SmartPC', 'Dashboard')
        original = {key: settings.value(key) for key in settings.allKeys()}
        for flags in [(False, False, False), (False, True, False), (True, False, True)]:
            settings.remove('navigation')
            for key, flag in zip(('sport', 'f1', 'motogp'), flags):
                settings.setValue('moduleVisible/' + key, flag)
            settings.sync()
            with patch('state.ThemeService', return_value=h.service):
                migrated = DashboardState(h.weather, h.system, h.account, sport=h.sport, racing=h.racing)
            assert migrated.sportGroupVisible == any(flags)
            assert [migrated.moduleVisibility[key] for key in ('sport', 'f1', 'motogp')] == list(flags)
            assert int(settings.value('navigation/schemaVersion')) == 1
            migrated.toggleModuleVisibility('sports')
            settings.sync()
            assert [settings.value('moduleVisible/' + key, type=bool) for key in ('sport', 'f1', 'motogp')] == list(flags)
            migrated.deleteLater()
        settings.clear()
        for key, value in original.items():
            settings.setValue(key, value)
        settings.sync()
        results.append('legacy-migration-all-hidden-only-f1-mixed-preserves-provider-keys-for-rollback')
        assert not h.messages, h.messages
        assert h.window.activeFocusItem().objectName() == 'inputOwner'
        print(json.dumps({'status': 'passed', 'profile': args.profile, 'checks': results, 'qmlWarnings': h.messages, 'physicalUsability': 'pending on 3.5 inch display at 50-60 cm'}, ensure_ascii=False))
    finally:
        if h:
            h.close()
        private.cleanup()


if __name__ == '__main__':
    main()
