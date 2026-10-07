"""Qt LAN service: single worker, five-minute polling, private SQLite cache."""
from __future__ import annotations
from copy import deepcopy
import os
import logging
from pathlib import Path
import sqlite3
import threading
import time
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, Signal, Slot
from iliadbox import IliadboxClient, NetworkError, load_config
from module_state import module_state
from network_core import NetworkStore, INTERVAL, acquire, demo_snapshot, display, empty, local_info, text


class _Signals(QObject):
    done = Signal(object, object)


class _Job(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = _Signals()

    def run(self):
        result, error = None, None
        try:
            result = self.operation()
        except NetworkError as failure:
            error = failure
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, AttributeError):
            error = NetworkError('invalid', 'Acquisizione o archivio Rete non valido; dati precedenti conservati.')
        self.signals.done.emit(result, error)


class NetworkService(QObject):
    changed = Signal()
    refreshFinished = Signal(bool, str)

    def __init__(self, *, auto_refresh=True, config_path=None, state_dir=None, transport=None, clock=time.time, monotonic=time.monotonic, demo=False):
        super().__init__()
        self.clock, self.monotonic = clock, monotonic
        self.config_path = Path(config_path) if config_path else Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'smartpc/iliadbox/app.json'
        self.state_dir = Path(state_dir) if state_dir else Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'smartpc/network'
        self.transport, self._demo = transport, demo
        self._stop = threading.Event()
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._busy = self._closed = self._halted = False
        self._worker = self.client = self.store = None
        self._snapshot = demo_snapshot(clock()) if demo else empty()
        self._status, self._error = ('active' if demo else 'unavailable'), ''
        self._last_attempt = -float('inf')
        self._next = float('inf')
        self._errors = 0
        self._operation = ''
        self._timer = QTimer(self)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self._tick)
        if not demo:
            # Initialization precedes QML loading. User reloads run in the worker.
            try:
                self._configure()
            except NetworkError as e:
                self._error = str(e)
                logging.getLogger(__name__).warning('Rete locale [%s]: %s',e.kind,e)
            if auto_refresh:
                self._timer.start()
                if self.client and self._snapshot['preferences']['polling']:
                    QTimer.singleShot(0, self.refresh)

    def _configure(self):
        client = IliadboxClient(load_config(self.config_path), transport=self.transport, cancelled=self._stop.is_set)
        store = NetworkStore(self.state_dir, client.scope)
        snapshot = store.load()
        self.client, self.store, self._snapshot = client, store, snapshot
        self._status = 'stale' if snapshot['checkedAt'] else 'unavailable'
        self._halted = False
        self._next = self.monotonic()

    def _start(self, operation, callback):
        if self._busy or self._closed:
            return False
        self._busy, self._operation = True, operation
        job = _Job(callback)
        job.signals.done.connect(self._finished)
        self._worker = job
        self.changed.emit()
        self._pool.start(job)
        return True

    @Slot(result=bool)
    def refresh(self):
        if self._demo or self._closed or not self.client or self._busy or self.monotonic() - self._last_attempt < 30:
            return False
        self._last_attempt = self.monotonic()
        client, previous, store = self.client, deepcopy(self._snapshot), self.store
        self._status, self._error = 'updating', ''
        def collect():
            local = local_info()
            if local['state'] == 'offline':
                raise NetworkError('offline', 'Link LAN della board assente; dati salvati.')
            result = acquire(client, previous, self.clock(), local)
            if self._stop.is_set():
                raise NetworkError('cancelled', 'Acquisizione Rete interrotta.')
            store.commit(snapshot=result)
            return result
        return self._start('refresh', collect)

    @Slot(object, object)
    def _finished(self, result, error):
        operation = self._operation
        self._busy, self._worker = False, None
        if self._closed:
            return
        ok = error is None
        if ok:
            if operation == 'reload':
                client, store, snapshot = result
                self.client, self.store, self._snapshot = client, store, snapshot
                self._status = 'stale' if snapshot['checkedAt'] else 'unavailable'
                self._halted = False
                self._last_attempt = -float('inf')
                self._next = self.monotonic()
            else:
                self._snapshot = result
                if operation == 'refresh':
                    self._status = 'active'
                    self._halted = False
                    self._errors = 0
                self._next = self.monotonic() + INTERVAL
            self._error = ''
        else:
            if operation == 'reload':
                self.client = None
            self._error = str(error)
            logging.getLogger(__name__).warning('Rete locale [%s]: %s',error.kind,error)
            self._status = 'offline' if error.kind == 'offline' else 'error'
            self._errors += 1
            self._halted = error.kind in ('auth', 'identity', 'tls', 'config', 'storage')
            self._next = self.monotonic() + min(1800, INTERVAL * 2 ** min(3, self._errors - 1))
        self.changed.emit()
        self.refreshFinished.emit(ok, self._error)

    def _tick(self):
        if self._closed or self._demo:
            return
        age = self.clock() - self._snapshot['checkedAt']
        if self._status == 'active' and (age >= INTERVAL or age < -5):
            self._status = 'stale'
            self.changed.emit()
        if not self._busy and self.client and not self._halted and self._snapshot['preferences']['polling'] and self.monotonic() >= self._next:
            self.refresh()

    @Slot(result=bool)
    def reloadConfig(self):
        if self._demo:
            return False
        def reload():
            client = IliadboxClient(load_config(self.config_path), transport=self.transport, cancelled=self._stop.is_set)
            store = NetworkStore(self.state_dir, client.scope)
            return client, store, store.load()
        return self._start('reload', reload)

    def _preference(self, change):
        if self._busy or self._closed or not (self.store or self._demo):
            return False
        result = deepcopy(self._snapshot)
        if not change(result['preferences']):
            return False
        if self._demo:
            self._snapshot = result
            self.changed.emit()
            return True
        def save():
            self.store.commit(preferences=result['preferences'])
            return result
        return self._start('preference', save)

    @Slot(str, result=bool)
    def toggleFavourite(self, identity):
        if not any(d['id'] == identity for d in self._snapshot['devices']):
            return False
        def change(p):
            if identity in p['favourites']:
                p['favourites'].remove(identity)
            elif len(p['favourites']) < 4:
                p['favourites'].append(identity)
            else:
                return False
            return True
        return self._preference(change)

    @Slot(str, int, result=bool)
    def moveFavourite(self, identity, direction):
        def change(p):
            if direction not in (-1, 1) or identity not in p['favourites']:
                return False
            index = p['favourites'].index(identity)
            target = index + direction
            if not 0 <= target < len(p['favourites']):
                return False
            p['favourites'][index], p['favourites'][target] = p['favourites'][target], p['favourites'][index]
            return True
        return self._preference(change)

    @Slot(str, str, result=bool)
    def setAlias(self, identity, alias):
        if not any(d['id'] == identity for d in self._snapshot['devices']) or not isinstance(alias, str) or len(alias) > 80:
            return False
        def change(p):
            value = text(alias, 80).strip()
            if value:
                p['aliases'][identity] = value
            else:
                p['aliases'].pop(identity, None)
            return True
        return self._preference(change)

    @Slot(result=bool)
    def togglePolling(self):
        def change(p):
            p['polling'] = not p['polling']
            return True
        return self._preference(change)

    @Property('QVariantMap', notify=changed)
    def moduleState(self):
        data = display(self._snapshot, self._status, self.clock())
        data['polling']=data['polling'] and not self._halted
        data.update(configured=self.client is not None or self._demo, hasInventory=bool(self._snapshot['checkedAt']), busy=self._busy, feedback=self._error, modeText='Demo · dati simulati' if self._demo else 'Autorizzazione da verificare · aggiornamenti sospesi' if self._halted else 'Lettura automatica ogni 5 minuti' if data['polling'] else 'Raccolta sospesa · aggiornamento manuale disponibile')
        return module_state(status=self._status, source='iliadbox' + (' (demo)' if self._demo else ''), updated_at=self._snapshot['checkedAt'], data=data, error=self._error)

    @Slot(bool)
    def setVisible(self, visible):
        # Visibility doesn't change freshness or secretly suspend polling.
        pass

    def close(self):
        self._closed = True
        self._timer.stop()
        self._stop.set()
        self._pool.waitForDone(6500)
