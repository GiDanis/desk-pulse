"""Theme selection journal, revision leases and external recovery primitives.

Only visual configuration is written here. Provider preferences and the event
store are deliberately outside this manager's authority. GUI frame success and
process health are separate acknowledgments owned by the application.
"""
from __future__ import annotations
from copy import deepcopy
import os
import math
from pathlib import Path
import shutil
import time
import uuid
from theme_bundle import (BundleManager, atomic_json, manager_lock, read_json,
                          require, revision_key, sync_directory)
from theme_core import ThemeError


BASE = {'kind': 'base', 'id': 'base'}


def selection(identity):
    if identity is None or identity == BASE:
        return deepcopy(BASE)
    revision_key(identity)
    return {key: identity[key] for key in ('id', 'version', 'digest')}


def selection_key(identity):
    return 'base' if identity == BASE else revision_key(identity)


def process_token(pid):
    try:
        # Start time disambiguates a reused PID; comm may contain spaces.
        return Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return ''


class LifecycleManager:
    def __init__(self, data_root, app_root=None):
        self.root = Path(data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'theme-activation.json'
        self.health_path = self.root / 'theme-gui-health.json'
        self.leases_root = self.root / 'theme-leases'
        self.leases_root.mkdir(exist_ok=True)
        self.bundle_manager = BundleManager(self.root, **({'app_root': app_root} if app_root else {}))

    def _default(self):
        return {'journalVersion': 1, 'active': deepcopy(BASE), 'previous': deepcopy(BASE), 'pending': None,
                'generation': 0, 'adaptations': {'global': {}, 'perRevision': {}}, 'failureCounts': {},
                'lastRecovery': None}

    def read(self):
        if not self.path.exists():
            return self._default()
        state = read_json(self.path)
        require(isinstance(state, dict) and state.get('journalVersion') == 1
                and set(state) == set(self._default()), 'activation', 'journal non valido')
        selection(state['active'])
        selection(state['previous'])
        require(type(state['generation']) is int and state['generation'] >= 0, 'activation.generation', 'generazione non valida')
        pending = state['pending']
        if pending is not None:
            require(isinstance(pending, dict) and set(pending) == {'ticket', 'candidate', 'previous', 'overrides', 'phase', 'startedAt'}
                    and pending['phase'] in ('preparing', 'ready'), 'activation.pending', 'transazione non valida')
            selection(pending['candidate'])
            selection(pending['previous'])
            require(isinstance(pending['ticket'],str) and len(pending['ticket']) == 32
                    and all(c in '0123456789abcdef' for c in pending['ticket'])
                    and isinstance(pending['overrides'],dict)
                    and type(pending['startedAt']) in (int,float) and math.isfinite(pending['startedAt']),
                    'activation.pending', 'dati transazione non validi')
        adaptations = state['adaptations']
        require(isinstance(adaptations,dict) and set(adaptations) == {'global','perRevision'}
                and isinstance(adaptations['global'],dict) and isinstance(adaptations['perRevision'],dict)
                and all(isinstance(key,str) and isinstance(value,dict) for key,value in adaptations['perRevision'].items()),
                'activation.adaptations', 'adattamenti non validi')
        require(isinstance(state['failureCounts'],dict)
                and all(isinstance(key,str) and type(value) is int and value >= 0 for key,value in state['failureCounts'].items()),
                'activation.failureCounts', 'conteggi non validi')
        last = state['lastRecovery']
        require(last is None or isinstance(last,dict) and set(last) == {'failed','selected','reason'}
                and isinstance(last['failed'],dict) and isinstance(last['reason'],str),
                'activation.lastRecovery', 'recupero non valido')
        if last is not None:
            selection(last['selected'])
        return state

    def _available(self, candidate):
        candidate = selection(candidate)
        if candidate == BASE:
            return candidate
        revision = self.bundle_manager.verify_revision(candidate)
        require(not (self.root / 'theme-quarantine' / (candidate['digest'] + '.json')).exists(), 'activation', 'revisione in quarantena')
        require(revision.get('preflight', {}).get('status') == 'passed', 'activation', 'preflight runtime richiesto prima di applicare')
        return candidate

    def begin(self, candidate, overrides=None):
        """Durably mark candidate before invoking any of its QML."""
        candidate = self._available(candidate)
        require(overrides is None or isinstance(overrides, dict), 'overrides', 'oggetto richiesto')
        with manager_lock(self.root):
            state = self.read()
            require(state['pending'] is None, 'activation', 'un solo candidato consentito')
            state['generation'] += 1
            ticket = uuid.uuid4().hex
            state['pending'] = {'ticket': ticket, 'candidate': candidate, 'previous': deepcopy(state['active']),
                                'overrides': deepcopy(overrides or {}), 'phase': 'preparing', 'startedAt': time.time()}
            atomic_json(self.path, state)
            return {'ticket': ticket, 'generation': state['generation'], 'candidate': candidate,
                    'previous': deepcopy(state['active'])}

    def mark_ready(self, ticket):
        """All mandatory contexts/resources ready; does not commit selection."""
        with manager_lock(self.root):
            state = self.read()
            require(state['pending'] is not None and state['pending']['ticket'] == ticket, 'activation.ticket', 'candidato superato')
            state['pending']['phase'] = 'ready'
            atomic_json(self.path, state)

    def commit(self, ticket, frame_ack):
        require(isinstance(frame_ack, dict) and frame_ack.get('coherent') is True and frame_ack.get('presented') is True,
                'activation.frame', 'ack del frame coerente presentato richiesto')
        with manager_lock(self.root):
            state = self.read()
            pending = state['pending']
            require(pending is not None and pending['ticket'] == ticket, 'activation.ticket', 'candidato superato')
            require(pending['phase'] == 'ready', 'activation', 'risorse e contesti non pronti')
            require(frame_ack.get('key') == selection_key(pending['candidate']), 'activation.frame', 'frame di altra revisione')
            # Validate again before the canonical record is changed.
            candidate = self._available(pending['candidate'])
            state['previous'] = pending['previous']
            state['active'] = candidate
            state['adaptations']['perRevision'][selection_key(candidate)] = pending['overrides']
            state['pending'] = None
            state['lastRecovery'] = None
            atomic_json(self.path, state)
            return deepcopy(state)

    def cancel(self, ticket):
        with manager_lock(self.root):
            state = self.read()
            if state['pending'] is None:
                return deepcopy(state)
            require(state['pending']['ticket'] == ticket, 'activation.ticket', 'candidato superato')
            state['pending'] = None
            state['generation'] += 1
            atomic_json(self.path, state)
            return deepcopy(state)

    def recover(self, reason='avvio interrotto', *, failed_active=False):
        """Called outside broken QML; quarantine without executing the bundle."""
        with manager_lock(self.root):
            try:
                state = self.read()
            except (OSError, ThemeError, ValueError) as error:
                # A damaged visual journal is recoverable without reading provider
                # settings or executing a selected bundle. Preserve it for diagnosis.
                if self.path.exists():
                    quarantined = self.root / 'theme-quarantine' / ('journal-' + uuid.uuid4().hex + '.json')
                    os.replace(self.path, quarantined)
                    sync_directory(quarantined.parent)
                state = self._default()
                state['lastRecovery'] = {'failed': {'kind': 'corruptJournal'}, 'selected': deepcopy(BASE), 'reason': str(error)[:500]}
                atomic_json(self.path, state)
                return {'recovered': True, 'selection': deepcopy(BASE), 'failed': {'kind': 'corruptJournal'}, 'reason': str(error)[:500]}
            pending = state['pending']
            if pending is None and not failed_active:
                return {'recovered': False, 'selection': deepcopy(state['active'])}
            failed = pending['candidate'] if pending else state['active']
            fallback = pending['previous'] if pending else state['previous']
            if fallback == failed:
                fallback = BASE
            try:
                fallback = self._available(fallback)
            except (OSError, ThemeError):
                fallback = BASE
            if failed != BASE:
                key = selection_key(failed)
                state['failureCounts'][key] = state['failureCounts'].get(key, 0) + 1
                # Do not move leased files; a marker excludes future selection.
                atomic_json(self.root / 'theme-quarantine' / (failed['digest'] + '.json'),
                            {'revision': failed, 'reason': str(reason)[:500], 'failures': state['failureCounts'][key]})
            state['active'] = deepcopy(fallback)
            state['previous'] = deepcopy(BASE)
            state['pending'] = None
            state['generation'] += 1
            state['lastRecovery'] = {'failed': failed, 'selected': fallback, 'reason': str(reason)[:500]}
            atomic_json(self.path, state)
            return {'recovered': True, 'selection': deepcopy(fallback), 'failed': failed, 'reason': str(reason)[:500]}

    def set_global_adjustments(self, values):
        require(isinstance(values, dict) and not set(values) - {'paletteMode', 'textScale', 'motionMode'}, 'adjustments', 'adattamenti globali non validi')
        if 'paletteMode' in values:
            require(values['paletteMode'] in ('auto', 'day', 'night'), 'paletteMode', 'modalità non valida')
        if 'motionMode' in values:
            require(values['motionMode'] in ('normal', 'reduced', 'off'), 'motionMode', 'modalità non valida')
        if 'textScale' in values:
            require(type(values['textScale']) in (int, float) and 0.75 <= values['textScale'] <= 1.5, 'textScale', 'scala non valida')
        with manager_lock(self.root):
            state = self.read()
            state['adaptations']['global'].update(deepcopy(values))
            atomic_json(self.path, state)
            return deepcopy(state['adaptations'])

    def migrate_overrides(self, source, destination, *, token_descriptors):
        """Explicit update migration retains only compatible token values."""
        from theme_core import HEX
        source_key, destination_key = selection_key(selection(source)), selection_key(selection(destination))
        with manager_lock(self.root):
            state = self.read()
            old = state['adaptations']['perRevision'].get(source_key, {})
            accepted, dropped = {}, []
            for name, value in old.get('tokens', {}).items():
                descriptor = token_descriptors.get(name)
                valid = False
                if descriptor:
                    kind = descriptor.get('type')
                    valid = type(value) is bool if kind == 'bool' else type(value) is int if kind == 'int' else type(value) in (int, float) and math.isfinite(value) if kind == 'real' else isinstance(value, str) and bool(HEX.fullmatch(value)) if kind == 'color' else isinstance(value, str) if kind == 'string' else False
                    if valid and 'minimum' in descriptor:
                        valid = value >= descriptor['minimum']
                    if valid and 'maximum' in descriptor:
                        valid = value <= descriptor['maximum']
                    if valid and 'enum' in descriptor:
                        valid = value in descriptor['enum']
                if valid:
                    accepted[name] = deepcopy(value)
                else:
                    dropped.append(name)
            migrated = {'tokens': accepted} if accepted else {}
            state['adaptations']['perRevision'][destination_key] = migrated
            atomic_json(self.path, state)
            return {'overrides': migrated, 'dropped': dropped}

    def acquire(self, identity, owner='host'):
        identity = selection(identity)
        if identity == BASE:
            return ''
        token = uuid.uuid4().hex
        with manager_lock(self.root):
            # Verification and protection are one operation relative to GC.
            # No collector may delete this revision between these two steps.
            self.bundle_manager.verify_revision(identity)
            atomic_json(self.leases_root / (token + '.json'), {'leaseVersion': 1, 'revision': identity,
                        'owner': str(owner)[:80], 'pid': os.getpid(), 'processStart': process_token(os.getpid())})
        return token

    def release(self, token):
        require(isinstance(token, str) and (not token or len(token) == 32 and all(c in '0123456789abcdef' for c in token)), 'lease', 'lease non valida')
        if not token:
            return
        with manager_lock(self.root):
            path = self.leases_root / (token + '.json')
            path.unlink(missing_ok=True)
            sync_directory(self.leases_root)

    def protected_revisions(self, *, clear_dead=False):
        state = self.read()
        identities = [state['active'], state['previous']]
        if state['pending']:
            identities.extend((state['pending']['candidate'], state['pending']['previous']))
        for path in self.leases_root.glob('*.json'):
            try:
                lease = read_json(path)
                current = process_token(lease['pid'])
                if current and current == lease['processStart']:
                    identities.append(lease['revision'])
                elif clear_dead:
                    path.unlink()
            except (OSError, KeyError, ThemeError):
                # Malformed lease is not permission to remove any resource.
                raise ThemeError('lease', 'lease danneggiata; cleanup sospeso')
        return {selection_key(selection(identity)) for identity in identities if identity != BASE}

    def remove(self, identity):
        identity = selection(identity)
        require(identity != BASE, 'remove', 'Base non rimovibile')
        with manager_lock(self.root):
            require(selection_key(identity) not in self.protected_revisions(clear_dead=True), 'remove', 'revisione attiva/precedente/candidata o in uso')
            revision = self.bundle_manager.verify_revision(identity)
            shutil.rmtree(revision['path'])
            sync_directory(Path(revision['path']).parent)
            return {'removed': identity}

    def gc(self, *, keep_per_theme=2):
        require(type(keep_per_theme) is int and keep_per_theme >= 1, 'gc', 'retention non valida')
        with manager_lock(self.root):
            protected = self.protected_revisions(clear_dead=True)
            revisions = self.bundle_manager.list_revisions(include_quarantined=True)
            counts, removed = {}, []
            for revision in reversed(revisions):
                counts[revision['id']] = counts.get(revision['id'], 0) + 1
                if counts[revision['id']] <= keep_per_theme or revision['key'] in protected:
                    continue
                shutil.rmtree(revision['path'])
                sync_directory(Path(revision['path']).parent)
                removed.append(selection(revision))
            return {'removed': removed, 'protected': sorted(protected)}

    def heartbeat(self, *, ready=True, generation=None):
        """Invoke from a discrete GUI timer, never from a worker/render thread."""
        state = self.read()
        record = {'healthVersion': 1, 'pid': os.getpid(), 'processStart': process_token(os.getpid()),
                  'time': time.time(), 'ready': bool(ready), 'generation': state['generation'] if generation is None else generation,
                  'selection': state['active'], 'pending': state['pending']['candidate'] if state['pending'] else None}
        atomic_json(self.health_path, record)
        return record
