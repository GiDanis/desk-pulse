"""A6 external watchdog proofs against real Main/Qt GUI child processes.

All stores/settings/provider sentinels are private. Supervisor restart is invoked
by this test's parent, not systemd. Offscreen frames are not EGLFS/optical proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent


def gui_child(mode, data_root, proof_path):
    # No private child store is substituted: this is the actual supervised root.
    for key, name in [('XDG_CONFIG_HOME', 'config'), ('XDG_CACHE_HOME', 'cache'),
                      ('XDG_STATE_HOME', 'state')]:
        os.environ[key] = str(data_root / name)
        (data_root / name).mkdir(exist_ok=True)
    os.environ['SMARTPC_THEME_STORE'] = str(data_root / 'themes')
    os.environ['SMARTPC_SPORT_OFFLINE'] = '1'
    os.environ['SMARTPC_RACING_OFFLINE'] = '1'
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['QT_QUICK_BACKEND'] = 'software'
    from unittest.mock import patch
    from PySide6.QtCore import QObject, QTimer, QUrl, QCoreApplication, QEvent, QThreadPool, qInstallMessageHandler, qVersion
    from PySide6.QtGui import QGuiApplication, QWindow
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    import shiboken6
    from account import AccountService
    from events import EventService
    from state import DashboardState
    from system_info import SystemInfo
    from weather import WeatherService
    from theme_api import bootstrap_theme_api
    from theme_bundle import atomic_json
    from theme_test_support import as_value

    app = QGuiApplication([])
    app.setOrganizationName('SmartPC'); app.setApplicationName('SmartPC')
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    proof = {'mode': mode, 'pid': os.getpid(), 'qt': qVersion(), 'backend': 'offscreen',
             'frames': 0, 'readyObserved': False, 'faultTriggered': False,
             'guiTicksAfterFault': 0, 'qmlWarnings': [], 'networkAttempts': 0}
    qInstallMessageHandler(lambda kind, context, message: proof['qmlWarnings'].append(message))
    def denied(*args, **kwargs):
        proof['networkAttempts'] += 1
        raise RuntimeError('Supervisor GUI fixture transport denied')
    if mode == 'startupBlock':
        atomic_json(proof_path, proof)
        time.sleep(30)
        return 99
    with patch('socket.socket.connect', side_effect=denied), patch('socket.getaddrinfo', side_effect=denied):
        events = EventService(path=':memory:', auto_refresh=False)
        state = DashboardState(WeatherService(auto_refresh=False), SystemInfo(),
                               AccountService(path=data_root / 'missing-account'), events, demo=True)
        state._brightness_mode = 'manual'; state._manual_brightness = 100
        service = state.appearance
        engine = QQmlApplicationEngine(); bootstrap_theme_api(engine)
        engine.setInitialProperties({'dashboardState': state})
        engine.load(QUrl.fromLocalFile(str(ROOT / 'Main.qml')))
        if not engine.rootObjects():
            atomic_json(proof_path, proof)
            return 91
        root = engine.rootObjects()[0]
        window = shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0], QQuickWindow)
        window.setVisibility(QWindow.Visibility.Windowed); window.resize(960, 640)
        window.frameSwapped.connect(lambda: proof.update(frames=proof['frames'] + 1))

        home = root.findChild(QObject, 'homeNow')
        timer = QTimer(); timer.setInterval(50)
        def tick():
            if proof['faultTriggered']:
                proof['guiTicksAfterFault'] += 1
                atomic_json(proof_path, proof)
                return
            try:
                health = json.loads(service.lifecycle.health_path.read_text())
            except (OSError, ValueError):
                return
            if (not service.needsFrameAcknowledgement and health.get('ready') is True
                    and health.get('pid') == os.getpid() and home.property('currentReady')):
                snapshot = service.resolvedAppearance
                proof.update(readyObserved=True, selection=snapshot.get('bundleRevision'),
                             healthReady=True, focus=window.activeFocusItem().objectName(),
                             rendererKey=home.property('loadedRendererKey'))
                atomic_json(proof_path, proof)
                if mode == 'observe':
                    return
                proof['faultTriggered'] = True
                atomic_json(proof_path, proof)
                if mode == 'cleanExit':
                    # Inject an unsolicited Qt exit, independently of the
                    # operator shutdown callbacks. Closing services from Qt
                    # aboutToQuit can itself fault on the Qt 6.8 fixture.
                    timer.stop()
                    QTimer.singleShot(100,lambda: app.exit(0))
                elif mode == 'crash':
                    os._exit(23)
                elif mode == 'heartbeatBlock':
                    time.sleep(30)  # Block the GUI owner, not a separate timer worker.
                elif mode == 'readinessLost':
                    item = as_value(home.property('currentItem'))
                    assert item.setProperty('readyForSupervisorProof', False)
                    proof['rendererReadyAfterFault'] = bool(home.property('currentReady'))
                    atomic_json(proof_path, proof)
        timer.timeout.connect(tick); timer.start()
        code = app.exec()
        timer.stop(); window.close()
        service.cancel(); events.close()
        QThreadPool.globalInstance().waitForDone(3000)
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.processEvents()
        atomic_json(proof_path, proof)
        return code


class SupervisorGuiTests(unittest.TestCase):
    records = []

    @classmethod
    def setUpClass(cls):
        from theme_bundle import BundleManager
        from theme_runtime import preflight
        cls.private = tempfile.TemporaryDirectory(prefix='smartpc-supervisor-gui-')
        cls.base = Path(cls.private.name)
        cls.template = cls.base / 'verified-store'
        project = cls.base / 'project'; shutil.copytree(ROOT / 'examples/bundles/studio-ambient', project)
        home = project / 'qml/Home.qml'
        source = home.read_text().replace('readonly property bool ready:',
            'property bool readyForSupervisorProof: true\n    readonly property bool ready: readyForSupervisorProof &&')
        home.write_text(source)
        manager = BundleManager(cls.template)
        cls.revisions = []
        for version in ('1.0.0', '1.0.1'):
            for name in ('bundle.json', 'theme.json'):
                path = project / name; value = json.loads(path.read_text()); value['version'] = version
                path.write_text(json.dumps(value))
            cls.revisions.append(manager.import_bundle(project, preflight=preflight, require_preflight=True))

    @classmethod
    def tearDownClass(cls):
        cls.private.cleanup()

    def setUp(self):
        from theme_lifecycle import LifecycleManager
        self.data = self.base / self._testMethodName
        shutil.copytree(self.template, self.data)
        self.lifecycle = LifecycleManager(self.data)
        self.previous, self.failed = self.revisions
        for revision in self.revisions:
            ticket = self.lifecycle.begin(revision)['ticket']; self.lifecycle.mark_ready(ticket)
            self.lifecycle.commit(ticket, {'key': revision['key'], 'coherent': True, 'presented': True})
        (self.data / 'provider-preferences.json').write_text('{"favourite":"fixture-team","threshold":77}')
        db = sqlite3.connect(self.data / 'provider-events.sqlite3')
        db.execute('CREATE TABLE flags(id TEXT PRIMARY KEY, seen INTEGER, notified INTEGER)')
        db.execute('INSERT INTO flags VALUES("fixture-event",1,1)'); db.commit(); db.close()
        self.before = self.provider_hashes()

    def provider_hashes(self):
        return {name: hashlib.sha256((self.data / name).read_bytes()).hexdigest()
                for name in ('provider-preferences.json', 'provider-events.sqlite3')}

    def launch(self, mode):
        proof = self.data / (mode + '-proof.json')
        command = [sys.executable, str(ROOT / 'theme_supervisor.py'), '--data-root', str(self.data),
                   '--startup-timeout', '8', '--heartbeat-timeout', '1.5', '--',
                   sys.executable, str(Path(__file__).resolve()), '--gui-child', mode,
                   '--data-root', str(self.data), '--child-proof', str(proof)]
        environment=dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
        if mode == 'observe':
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment)
            deadline=time.monotonic()+15
            try:
                while time.monotonic()<deadline and process.poll() is None:
                    if proof.exists() and json.loads(proof.read_text()).get('readyObserved'):break
                    time.sleep(.05)
                process.send_signal(signal.SIGTERM)
                stdout,stderr=process.communicate(timeout=8)
                result=subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
            finally:
                if process.poll() is None:process.kill();process.wait()
        else:
            result = subprocess.run(command, capture_output=True, text=True, timeout=25,env=environment)
        details = json.loads(proof.read_text()) if proof.exists() else {}
        return result, details

    def verify_fault(self, mode, expected_reason):
        from theme_lifecycle import selection
        result, proof = self.launch(mode)
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertIn(expected_reason, result.stderr)
        if mode != 'startupBlock':
            self.assertTrue(proof['readyObserved'], proof)
            self.assertGreater(proof['frames'], 0)
            self.assertEqual(proof['selection']['digest'], self.failed['digest'])
            self.assertEqual(proof['qmlWarnings'], [])
        self.assertFalse(Path('/proc/' + str(proof['pid'])).exists(), 'failed GUI survived supervisor termination')
        journal = self.lifecycle.read()
        self.assertEqual(journal['active'], selection(self.previous))
        self.assertIsNone(journal['pending'])
        self.assertTrue((self.data / 'theme-quarantine' / (self.failed['digest'] + '.json')).is_file())
        restarted, restart_proof = self.launch('observe')
        self.assertEqual(restarted.returncode, 0, restarted.stderr)
        self.assertTrue(restart_proof['readyObserved'])
        self.assertEqual(restart_proof['selection']['digest'], self.previous['digest'])
        self.assertEqual(restart_proof['qmlWarnings'], [])
        self.assertEqual(self.provider_hashes(), self.before)
        record = {'case': mode, 'status': 'passed', 'failureExitCode': result.returncode,
                  'failure': proof, 'supervisor': result.stderr.strip(), 'restart': restart_proof,
                  'quarantine': True, 'providerHashesPreserved': True}
        if mode == 'readinessLost':
            # Capture the failed child record before restart separately below.
            self.assertGreater(proof['guiTicksAfterFault'], 1)
            self.assertFalse(proof['rendererReadyAfterFault'])
        self.records.append(record)

    def test_actual_gui_crash_rolls_back_previous_and_restarts(self):
        self.verify_fault('crash', 'codice 23')

    def test_actual_gui_startup_block_rolls_back_previous_and_restarts(self):
        self.verify_fault('startupBlock', 'startup/readiness timeout')

    def test_actual_gui_thread_hang_rolls_back_previous_and_restarts(self):
        self.verify_fault('heartbeatBlock', 'heartbeat')

    def test_actual_gui_readiness_loss_with_live_event_loop_rolls_back(self):
        self.verify_fault('readinessLost', 'heartbeat')

    def test_unexpected_clean_gui_exit_rolls_back_instead_of_boot_loop(self):
        self.verify_fault('cleanExit', 'codice 0')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui-child', choices=['observe', 'cleanExit', 'crash', 'startupBlock',
                                              'heartbeatBlock', 'readinessLost'])
    parser.add_argument('--data-root', type=Path); parser.add_argument('--child-proof', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.gui_child:
        return gui_child(args.gui_child, args.data_root, args.child_proof)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SupervisorGuiTests))
    report = {'status': 'passed' if result.wasSuccessful() else 'failed', 'testsRun': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'cases': SupervisorGuiTests.records,
              'scope': 'Actual Main/Qt offscreen children and external Linux watchdog; verified theme revisions seeded before launch; restart launched by test parent, not systemd; provider sentinels isolated; no EGLFS/optical/performance proof.'}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'testsRun': report['testsRun'], 'failures': report['failures'], 'errors': report['errors']}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
