"""Local aquarium lifecycle: no animation timer, provider polling or saved game."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import uuid
from PySide6.QtCore import QObject, Property, Signal, Slot
from aquarium_catalog import ROOT, load_catalog


class AquariumService(QObject):
    changed = Signal()
    _catalogLoaded = Signal(int, object, str)

    def __init__(self, parent=None, *, root=ROOT):
        super().__init__(parent)
        self._root = root
        self._executor = None
        self._closed = False
        self._loading = False
        self._epoch = 0
        self._catalog = None
        self._error = ''
        self._selected = self._exposed = self._overlay = self._urgent = self._theme = False
        self._motion = 'off'
        self._paused = False
        self._session = ''
        self._snapshot = {}
        self._catalogLoaded.connect(self._accept_catalog)
        self._publish()

    @Property('QVariantMap', notify=changed)
    def snapshot(self):
        return self._snapshot

    def _load(self):
        if self._closed or self._loading or self._catalog or self._error:
            return
        self._loading = True
        self._epoch += 1
        epoch = self._epoch
        self._executor = self._executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix='aquarium-assets')
        future = self._executor.submit(load_catalog, self._root)
        def complete(job):
            try:
                data, error = job.result(), ''
            except Exception as exc:
                data, error = None, str(exc)
            if not self._closed:
                self._catalogLoaded.emit(epoch, data, error)
        future.add_done_callback(complete)

    @Slot(int, object, str)
    def _accept_catalog(self, epoch, data, error):
        if self._closed or epoch != self._epoch:
            return
        self._loading = False
        self._catalog, self._error = data, error
        self._publish()

    @Slot(bool, bool, bool, bool, str, bool)
    def setLifecycle(self, selected, exposed, overlay, urgent, motion, theme):
        if self._closed:
            return
        if selected and not self._selected:
            self._session = uuid.uuid4().hex
            self._paused = False
            self._load()
        if urgent and selected and (not self._urgent or not self._selected):
            self._paused = True
        self._selected, self._exposed = selected, exposed
        self._overlay, self._urgent, self._theme = overlay, urgent, theme
        self._motion = motion if motion in ('normal', 'reduced', 'off') else 'off'
        self._publish()

    @Slot(result=bool)
    def pause(self):
        if self._closed or not self._selected or self._urgent:
            return False
        self._paused = True
        self._publish()
        return True

    @Slot(result=bool)
    def resume(self):
        if self._closed or not self._selected or self._urgent or self._motion != 'normal' or self._error:
            return False
        self._paused = False
        self._publish()
        return True

    @Slot(str, str)
    def reportAssetError(self, session, message):
        if not self._closed and session == self._session and message and self._error != message:
            self._error = str(message)
            self._publish()

    def _publish(self):
        reasons = []
        for reason, blocked in (('hidden', not self._selected), ('preparing', not self._exposed),
                                ('overlay', self._overlay), ('urgent', self._urgent),
                                ('theme', self._theme), ('assets', not self._catalog),
                                ('user', self._paused), ('reduced', self._motion == 'reduced'),
                                ('off', self._motion == 'off')):
            if blocked:
                reasons.append(reason)
        status = 'error' if self._error else 'ready' if self._catalog else 'loading' if self._loading else 'idle'
        effective = 'error' if self._error else 'static' if self._motion != 'normal' else 'suspended' if reasons else 'running'
        species = self._catalog['species'] if self._catalog else []
        instances = [{'id': 'fish-' + str(i), 'speciesId': species[min(1 if i >= 4 else 0, len(species)-1)]['id'],
                      'depth': i % 3, 'phase': (i * .173) % 1.,
                      'startX': .17 + (i % 3) * .31, 'startY': .22 + (i // 3) * .38}
                     for i in range(6)] if species else []
        value = dict(sessionId=self._session, configurationRevision=1,
                     assetRevision=self._catalog['assetRevision'] if self._catalog else '',
                     status=status, errorCode='assets' if self._error else '', errorText=self._error,
                     requestedPlayback='paused' if self._paused else 'playing', effectivePlayback=effective,
                     suspendReasons=reasons, environmentId='calm-v1', seed=20261025,
                     backgroundUrl=self._catalog['backgroundUrl'] if self._catalog else '',
                     species=species, instances=instances)
        if value != self._snapshot:
            self._snapshot = deepcopy(value)
            self.changed.emit()

    def close(self):
        self._closed = True
        self._epoch += 1
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
