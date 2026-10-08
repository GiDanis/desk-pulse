"""Canonical read-only DTOs and contexts for SmartPC.ThemeApi 2.0.

The classes are generated from the same checked-in contracts used by the SDK.
Internal Python writers are deliberately not Qt slots. Object/model identity
survives updates; primitive properties notify only when their value changes.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import MappingProxyType

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlEngine, qmlRegisterUncreatableType

from theme_api_contract import ThemeApiContract
from theme_models import ThemeListModel

class _RuntimeContract(ThemeApiContract):
    """Validated schema compiled once; runtime consumers cannot mutate fields."""
    def __init__(self):
        self._compiled_fields = {}
        super().__init__()
        for name in (*self.types, *self.contexts):
            fields = super().fields(name)
            self._compiled_fields[name] = MappingProxyType({key: MappingProxyType({
                field: tuple(value) if isinstance(value, list) else value
                for field, value in spec.items()}) for key, spec in fields.items()})

    def fields(self, name, seen=()):
        compiled = self._compiled_fields.get(name)
        return compiled if compiled is not None else super().fields(name, seen)


CONTRACT = _RuntimeContract()
_DEFAULT_SNAPSHOTS = {}
PUBLIC_TYPES = {}
PRIMITIVE_TYPES = {'string': str, 'int': int, 'real': float, 'bool': bool,
                   'color': QColor, 'scalar': 'QVariant', 'legacyMap': 'QVariantMap',
                   'array': 'QVariantList'}


def snapshot_equal(left, right):
    """Type-exact equality without recursive calls for large provider snapshots.

    Python's native container equality equates False/0 and int/float. Preserve
    that distinction while avoiding a Python function/generator for every leaf.
    """
    pending = [(left, right)]
    while pending:
        a, b = pending.pop()
        kind = type(a)
        if kind is not type(b):
            return False
        if a is b:
            continue
        if kind is dict:
            if a.keys() != b.keys():
                return False
            for key, value in a.items():
                pending.append((value, b[key]))
        elif kind in (list, tuple):
            if len(a) != len(b):
                return False
            pending.extend(zip(a, b))
        elif a != b:
            return False
    return True


def default_value(spec):
    if 'const' in spec:
        return deepcopy(spec['const'])
    if spec.get('nullable'):
        return None
    kind = spec['type']
    if kind in CONTRACT.models or kind == 'array':
        return []
    if kind == 'legacyMap':
        return {}
    if 'enum' in spec:
        # Avoid a fabricated live/active state merely because it is the first
        # enum member in a schema. These defaults describe missing input.
        choices = spec['enum']
        for preferred in ('unavailable', 'idle', 'preparing', 'off', 'unknown'):
            if preferred in choices:
                return preferred
        return deepcopy(choices[0])
    if kind in ('int', 'real'):
        return spec.get('minimum', 0) if spec.get('minimum', 0) < 0 else max(spec.get('minimum', 0), 0)
    if kind == 'bool':
        return False
    if kind == 'color':
        return '#000000'
    if kind == 'string':
        return '1970-01-01' if spec.get('format') == 'date' else ''
    if kind == 'scalar':
        return ''
    return default_snapshot(kind)


def default_snapshot(type_name):
    if type_name not in _DEFAULT_SNAPSHOTS:
        _DEFAULT_SNAPSHOTS[type_name] = {name: default_value(spec)
                                        for name, spec in CONTRACT.fields(type_name).items()}
    # Writers receive an independent owned snapshot, never the shared template.
    return deepcopy(_DEFAULT_SNAPSHOTS[type_name])


def complete_snapshot(type_name, values):
    """Complete a *canonical* partial DTO; do not rename/parse domain data."""
    result = _complete_snapshot(type_name, values)
    # Validate the whole completed tree at the boundary, including every nested
    # row, duplicate identity and numeric availability invariant, exactly once.
    CONTRACT.validate_snapshot(type_name, result)
    return result


def _complete_snapshot(type_name, values):
    fields = CONTRACT.fields(type_name)
    if not isinstance(values, dict) or set(values) - set(fields):
        CONTRACT.validate_snapshot(type_name, values)
    result = {}
    for name, spec in fields.items():
        value = values[name] if name in values else default_value(spec)
        kind = spec['type']
        if value is not None and kind in CONTRACT.types:
            value = _complete_snapshot(kind, value)
        elif kind in CONTRACT.models and isinstance(value, list):
            value = [_complete_snapshot(CONTRACT.models[kind]['itemType'], row) for row in value]
        else:
            value = deepcopy(value)
        result[name] = value
    return result


def complete_field(spec, value, path):
    """Own and validate a changed field, including its complete nested tree."""
    kind = spec['type']
    if value is not None and kind in CONTRACT.types:
        result = _complete_snapshot(kind, value)
    elif kind in CONTRACT.models and isinstance(value, list):
        result = [_complete_snapshot(CONTRACT.models[kind]['itemType'], row) for row in value]
    else:
        result = deepcopy(value)
    CONTRACT._value(spec, result, path)
    return result


class ReadOnlySnapshot(QObject):
    _type_name = ''
    _fields = {}

    def __init__(self, values=None, parent=None, *, validated=False):
        super().__init__(parent)
        self._values = {}
        self._snapshots = {}
        self._broker = None
        self._instance_generation = 0
        self._runtime_state = {'state': 'preparing', 'active': False,
                               'interactive': False, 'preview': False, 'generation': 0}
        self._update(default_snapshot(self._type_name) if values is None else values,
                     validated=validated)

    def _snapshot(self):
        return deepcopy(self._snapshots)

    def _update(self, values, validated=False):
        if not validated:
            CONTRACT.validate_snapshot(self._type_name, values)
        changed = []
        for name, spec in self._fields.items():
            if name not in values:
                continue
            value = values[name]
            if name in self._snapshots and snapshot_equal(self._snapshots[name], value):
                continue
            self._snapshots[name] = deepcopy(value)
            previous = self._values.get(name)
            kind = spec['type']
            nested = kind in PUBLIC_TYPES
            if nested and value is not None:
                if isinstance(previous, PUBLIC_TYPES[kind]):
                    nested_changed = previous._replace(value, validated=True) if kind in CONTRACT.models else previous._update(value, validated=True)
                    if nested_changed:
                        changed.append(name)
                        # The QObject identity is stable, but its public value changed.
                        # Re-evaluate QML projections, including equal-count swaps.
                        getattr(self, name + 'Changed').emit()
                    continue
                replacement = PUBLIC_TYPES[kind](value, self, validated=True)
            else:
                replacement = QColor(value) if kind == 'color' else deepcopy(value)
                if name in self._values and type(previous) is type(replacement) and previous == replacement:
                    continue
            self._values[name] = replacement
            if isinstance(previous, QObject):
                previous.deleteLater()
            changed.append(name)
            getattr(self, name + 'Changed').emit()
        return changed


def _request(self, action_id, target_id='', arguments=None):
    if self._broker is None:
        result = {'accepted': False, 'requestId': '', 'status': 'rejected', 'errorCode': 'api.action.detached'}
    else:
        result = self._broker._request(self, action_id, target_id, arguments or {})
    # A persistent surface must not accumulate one child per key/action.
    # QML owns completed results; the broker retains pending results only until
    # completion/revocation. Python callers retain the wrapper normally.
    obj = PUBLIC_TYPES['ActionResult'](result)
    QQmlEngine.setObjectOwnership(obj, QQmlEngine.JavaScriptOwnership)
    if self._broker is not None:
        self._broker._track_result(obj)
    return obj


def _notification_request(self, action_id, target_id='', arguments=None):
    return _request(self, action_id, target_id, arguments).accepted


def _settle_motion(self):
    self.settleMotionRequested.emit()


def _format_stamp(self, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        return ''
    try:
        return datetime.fromtimestamp(value).strftime('%d/%m · %H:%M')
    except (OverflowError, OSError, ValueError):
        return ''


def _build_types():
    pending = {**CONTRACT.types, **CONTRACT.models, **CONTRACT.contexts}
    while pending:
        ready = []
        for name, definition in pending.items():
            dependencies = [definition['itemType']] if name in CONTRACT.models else [spec['type'] for spec in definition['fields'].values()]
            if definition.get('extends'):
                dependencies.append(definition['extends'])
            if not set(dependencies) & set(pending):
                ready.append(name)
        if not ready:
            raise RuntimeError('Cyclic public API object dependency: ' + ', '.join(pending))
        for name in ready:
            definition = pending.pop(name)
            if name in CONTRACT.models:
                attributes = {'__module__': __name__, '_type_name': name,
                              '_item_type': definition['itemType'], '_identity_role': definition['identityRole'],
                              '_fields': CONTRACT.fields(definition['itemType'])}
                cls = type(name, (ThemeListModel,), attributes)
            else:
                fields = CONTRACT.fields(name)
                base = PUBLIC_TYPES.get(definition.get('extends'), ReadOnlySnapshot)
                attributes = {'__module__': __name__, '_type_name': name, '_fields': fields}
                for field, spec in definition['fields'].items():
                    attributes[field + 'Changed'] = Signal()
                    kind = spec['type']
                    # PySide cannot marshal Python-defined pointer typedefs in
                    # Property getters (despite accepting their QMetaType).
                    # The backing pointer is QObject*, its actual instance is
                    # the registered canonical class; tooling narrows that
                    # pointer using the validated schema. Primitive properties
                    # retain their native QColor/int/double/QString types.
                    native = 'QVariant' if spec.get('nullable') and kind in PRIMITIVE_TYPES else PRIMITIVE_TYPES.get(kind, QObject)
                    getter = lambda self, key=field: self._values.get(key)
                    attributes[field] = Property(native, getter, notify=attributes[field + 'Changed'])
                if name in CONTRACT.contexts:
                    for method in definition.get('methods', {}):
                        if method == 'requestAction':
                            implementation = _notification_request if name == 'NotificationContext' else _request
                            result = bool if name == 'NotificationContext' else QObject
                            wrapper = lambda self, a, t, p, fn=implementation: fn(self, a, t, p)
                            attributes[method] = Slot(str, str, 'QVariantMap', result=result, name=method)(wrapper)
                        elif method == 'request':
                            wrapper = lambda self, a, t, p: _request(self, a, t, p)
                            attributes[method] = Slot(str, str, 'QVariantMap', result=QObject, name=method)(wrapper)
                        elif method == 'settleMotion':
                            attributes[method] = Slot(name=method)(_settle_motion)
                        elif method == 'formatStamp':
                            attributes[method] = Slot('QVariant', result=str, name=method)(_format_stamp)
                    for signal, spec in definition.get('signals', {}).items():
                        attributes[signal] = Signal(*[PRIMITIVE_TYPES[t] for t in spec['parameters']])
                cls = type(name, (base,), attributes)
            PUBLIC_TYPES[name] = cls
            globals()[name] = cls
            # Register in dependency order before a parent metaobject declares
            # a property of this exact pointer type. Passing a Python QObject
            # subclass directly to Property would erase it to QObject*.
            qmlRegisterUncreatableType(cls, 'SmartPC.ThemeApi', 2, 0, name,
                                       'Owned by SmartPC; obtain this object from the renderer context')
            qmlRegisterUncreatableType(cls, 'SmartPC.ThemeApi', 2, 1, name,
                                       'Owned by SmartPC; obtain this object from the renderer context')
            qmlRegisterUncreatableType(cls, 'SmartPC.ThemeApi', 2, 2, name,
                                       'Owned by SmartPC; obtain this object from the renderer context')


_build_types()
