"""Runtime bootstrap, normalization and private action broker for theme API 2.

QML renderers receive only an app-owned immutable context. This factory is a
private host input, not a public singleton and not a security sandbox for QML.
"""
from __future__ import annotations

from copy import deepcopy
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
import uuid

from PySide6.QtCore import QObject, Property, Signal, Slot, QPointF, QRectF, QMetaObject, Qt
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlEngine, QJSValue

from dashboard_summary import build_summary
from theme_api_contract import ContractError
from theme_contexts import (CONTRACT, PUBLIC_TYPES, complete_snapshot, complete_field, default_snapshot, snapshot_equal)

IMPORT_ROOT = Path(__file__).parent / 'qml'


def bootstrap_theme_api(engine):
    """Shared app/preview/test bootstrap; registration occurs in dependency order."""
    engine.addImportPath(str(IMPORT_ROOT))
    return {'uri': 'SmartPC.ThemeApi', 'major': 2, 'minor': CONTRACT.surfaces_document['module']['minor'],
            'apiFingerprint': CONTRACT.fingerprint, 'runtimeModuleVerified': True}


def _plain(value):
    if isinstance(value, QJSValue):
        value = value.toVariant()
    if isinstance(value, QColor):
        return value.name()
    if isinstance(value, QPointF):
        return {'x': value.x(), 'y': value.y()}
    if isinstance(value, QRectF):
        return {'x': value.x(), 'y': value.y(), 'width': value.width(), 'height': value.height()}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _mapping(value):
    # Provider dictionaries already contain Python data. Convert Qt values at
    # the selected field boundary instead of traversing every domain repeatedly.
    if isinstance(value, dict):
        return value
    value = _plain(value)
    return value if isinstance(value, dict) else {}


def _finite_number(value):
    from math import isfinite
    return type(value) in (float, int) and isfinite(value)


def timestamp(value, timezone='Europe/Rome'):
    if _finite_number(value):
        return value
    if isinstance(value, str) and value:
        try:
            from zoneinfo import ZoneInfo
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
            return parsed.timestamp()
        except (ValueError, OverflowError, OSError):
            pass
    return None


def numeric(value, unit='', display='', revision=''):
    if isinstance(value, dict):
        return complete_snapshot('NumericValue', value)
    return {'available': _finite_number(value), 'value': value if _finite_number(value) else None,
            'unit': unit, 'displayText': str(display) if display != '' else str(value) if value is not None else '',
            'sourceRevision': str(revision)}


def source_snapshot(envelope, source_id=''):
    envelope = _mapping(envelope)
    data = _mapping(envelope.get('data'))
    candidate = envelope.get('status', 'unavailable')
    status = candidate if candidate in CONTRACT.fields('SourceState')['status']['enum'] else 'unavailable'
    updated = envelope.get('updatedAt')
    checked = envelope.get('checkedAt')
    return complete_snapshot('SourceState', {
        'status': status, 'sourceId': str(envelope.get('sourceId', source_id)),
        'sourceLabel': str(envelope.get('source', envelope.get('sourceLabel', ''))),
        'updatedAt': updated if _finite_number(updated) and updated > 0 else None,
        'checkedAt': checked if _finite_number(checked) and checked > 0 else None,
        'hasData': bool(data) if 'hasData' not in envelope else bool(envelope['hasData']),
        'isStale': status in ('stale', 'offline', 'error') and bool(data),
        'error': str(envelope.get('error', '')), 'errorCode': str(envelope.get('errorCode', '')),
        'dataRevision': str(envelope.get('dataRevision', envelope.get('revision', '')))})


ALIASES = {
    'MatchData': {'id': 'canonicalMatchId', 'roundId': 'round', 'kickoffAt': 'kickoffUtc',
                  'statistics': 'stats', 'detailFetchedAt': 'detailFetchedAt'},
    'MatchEvent': {'kind': 'type', 'playerName': 'player', 'text': 'label'},
    'MatchStatistic': {'home': 'home', 'away': 'away'},
    'WeatherForecast': {'dayText': 'day', 'rainProbability': 'rain'},
    'NotificationEvent': {'sourceLabel': 'source', 'sourceId': 'source', 'body': 'detail',
                          'rank': 'notificationRank', 'weatherSeverity': 'weather_severity',
                          'issuedAt': 'issued_at', 'expiresAt': 'expires_at', 'bannerSize': 'banner_size'},
    'NextEventData': {'startsAt': 'start', 'whenText': 'when', 'category': 'type'},
    'SportData': {'matches': 'fixtures', 'liveVerified': 'activeLiveVerified'},
    'TeamData': {'identity': 'team'},
    'Standing': {'name': 'team', 'entityId': 'teamId'},
    'RacingLiveData': {'rows': 'timing', 'messages': 'raceControl'},
    'AccountWindow': {'label': 'name', 'windowDurationMinutes': 'durationMins', 'resetsAt': 'resetAt'},
    'Family': {'label': 'name'}, 'Tab': {'label': 'name'},
    'SettingRow': {'title': 'label', 'detail': 'description'},
    'InfoRow': {'title': 'label'},
    'DriverData': {'name': 'driverName', 'laps': 'lapTimes'},
    'RacingTiming': {'driverName': 'name'},
    'RacingEventData': {'roundId': 'round', 'startsAt': 'start', 'endsAt': 'end', 'info': 'infoRows', 'summary': 'summaryRows'},
    'RacingSessionData': {'startsAt': 'start', 'endsAt': 'end', 'status': 'state', 'info': 'infoRows'},
}


def normalize_dto(type_name, raw, *, identity='', source=None):
    """Normalize provider records without extracting measurements from UI text.

    Unknown provider keys stay private. Numeric strings are display text only;
    callers can supply actual normalized numbers without changing the API.
    """
    raw = _mapping(raw)
    values = default_snapshot(type_name)
    fields = CONTRACT.fields(type_name)
    for name, spec in fields.items():
        key = name if name in raw else ALIASES.get(type_name, {}).get(name, name)
        if key not in raw:
            continue
        value = _plain(raw[key])
        kind = spec['type']
        if value is None:
            if spec.get('nullable'):
                values[name] = None
            continue
        if kind in CONTRACT.types:
            if kind == 'NumericValue':
                values[name] = numeric(value)
            elif kind == 'ScalarValue':
                values[name] = complete_snapshot(kind, value) if isinstance(value, dict) else complete_snapshot(kind, {
                    'available': type(value) in (str, bool, int, float),
                    'value': value if type(value) in (str, bool, int, float) else None,
                    'displayText': str(value) if type(value) in (str, bool, int, float) else ''})
            elif isinstance(value, (dict, QObject)):
                values[name] = normalize_dto(kind, object_snapshot(kind, value) if isinstance(value, QObject) else value,
                                             source=source)
        elif kind in CONTRACT.models and isinstance(value, list):
            model = CONTRACT.models[kind]
            rows = []
            for i, row in enumerate(value):
                row = row if isinstance(row, dict) else {'id': str(row), 'name': str(row), 'label': str(row),
                                                         'text': str(row), 'enabled': True}
                row_identity = row.get(model['identityRole'], row.get('canonicalMatchId', row.get('teamId', row.get('providerId', ''))))
                # A stable domain ID is preferred. Fixed row indexes are used
                # only for provider records lacking any identifier (statistics,
                # lineups), scoped under their owning domain record.
                row_identity = str(row_identity) if row_identity not in (None, '') else f'{identity or type_name}:{name}:{i}'
                rows.append(normalize_dto(model['itemType'], row, identity=row_identity, source=source))
            values[name] = rows
        elif kind == 'array' and isinstance(value, list):
            values[name] = [str(v) for v in value] if spec.get('items') == 'string' else [normalize_dto(spec['items'], _plain(v)) if spec.get('items') in CONTRACT.types else deepcopy(_plain(v)) for v in value]
        elif kind == 'color':
            color = QColor(value)
            if color.isValid():
                values[name] = color.name()
        elif kind == 'string':
            if isinstance(value, (str, int, float)) and ('enum' not in spec or value in spec['enum']):
                values[name] = str(value)
        elif kind == 'bool':
            if type(value) is bool:
                values[name] = value
        elif kind in ('int', 'real'):
            if spec.get('unit') == 'epochSeconds':
                value = timestamp(value)
            if _finite_number(value) and (kind != 'int' or type(value) is int) and value >= spec.get('minimum', float('-inf')) and value <= spec.get('maximum', float('inf')):
                values[name] = value
        elif kind in ('legacyMap', 'scalar'):
            values[name] = deepcopy(value)
    identity_key = 'sourceId' if type_name == 'SourceState' else 'id'
    if identity and identity_key in fields:
        values[identity_key] = identity
    if 'source' in fields and fields['source']['type'] == 'SourceState' and source is not None:
        values['source'] = deepcopy(source)
    if type_name == 'MatchData':
        for side in ('home', 'away'):
            if not isinstance(raw.get(side), dict):
                values[side] = complete_snapshot('TeamIdentity', {
                    'id': str(raw.get(side + 'TeamId', '')), 'name': str(raw.get(side + 'Team', ''))})
        if isinstance(raw.get('rawStatus'), dict):
            reason = _mapping(raw['rawStatus'].get('reason'))
            values['rawStatus'] = str(reason.get('short', ''))
    if type_name == 'TeamData' and not isinstance(raw.get('identity', raw.get('team')), dict):
        values['identity'] = normalize_dto('TeamIdentity', raw)
    if type_name == 'Standing':
        if not values['id']:
            values['id'] = str(raw.get('teamId', raw.get('id', '')))
        if not values['entityId']:
            values['entityId'] = str(raw.get('teamId', raw.get('id', '')))
    if type_name == 'SportData':
        values['favouriteTeamId'] = str(raw.get('favouriteTeamId', raw.get('favourite', '')))
        if isinstance(raw.get('rounds'), list):
            values['rounds'] = [normalize_dto('Round', row if isinstance(row, dict) else {'id': str(row), 'label': str(row)}) for row in raw['rounds']]
        elif values['matches']:
            round_ids = sorted({row['roundId'] for row in values['matches'] if row['roundId']})
            values['rounds'] = [normalize_dto('Round', {'id': key, 'label': key}) for key in round_ids]
        if 'activeMatchIds' not in raw:
            values['activeMatchIds'] = [str(row.get('canonicalMatchId', row.get('id', ''))) for row in raw.get('activeMatches', []) if isinstance(row, dict) and row.get('canonicalMatchId', row.get('id'))]
    if type_name == 'AccountData':
        for i, window in enumerate(values['windows']):
            if not window['id']:
                window['id'] = str(raw.get('windows', [])[i].get('id', f'window:{i}'))
    if type_name == 'AccountCredits' and raw.get('balance') == '':
        # The backend uses an empty balance for an unavailable measurement.
        # A real zero balance remains available, including the string "0".
        values['balance'] = default_snapshot('ScalarValue')
    if type_name == 'AccountWindow' and 'windowDurationMinutes' not in raw and 'windowDurationMins' in raw:
        values['windowDurationMinutes'] = numeric(raw['windowDurationMins'])
    if type_name == 'Lineup':
        values['teamId'] = str(raw.get('teamId', raw.get('side', '')))
    if type_name == 'NotificationEvent' and isinstance(raw.get('source'), str):
        values['source'] = None
    return complete_snapshot(type_name, values)


def object_snapshot(type_name, obj):
    """Read a QML style facade once per input change, with canonical fields only."""
    if isinstance(obj, dict):
        return obj
    if not isinstance(obj, QObject):
        return {}
    result = {}
    meta = obj.metaObject()
    for name, spec in CONTRACT.fields(type_name).items():
        if meta.indexOfProperty(name) < 0:
            continue
        value = _plain(obj.property(name))
        if isinstance(value, QObject) and spec['type'] in CONTRACT.types:
            value = object_snapshot(spec['type'], value)
        result[name] = value
    return result


def weather_snapshot(envelope):
    envelope = _mapping(envelope)
    data = _mapping(envelope.get('data', envelope))
    result = normalize_dto('WeatherData', data, source=source_snapshot(envelope, 'weather'))
    numbers = _mapping(data.get('numeric'))
    aliases = {'feelsLike': 'feels_like', 'rainProbability': 'rain_probability',
               'windSpeed': 'wind', 'windDirection': 'wind_direction'}
    units = {'temperature': '°C', 'feelsLike': '°C', 'humidity': '%', 'precipitation': 'mm',
             'rainProbability': '%', 'windSpeed': 'km/h', 'windDirection': '°', 'gusts': 'km/h'}
    for key, unit in units.items():
        display = data.get(key, data.get(aliases.get(key, key), ''))
        value = numbers.get(key, data.get(key + 'Value'))
        if value is None and _finite_number(display):
            value = display
        result[key] = numeric(value, unit, display, result['source']['dataRevision'])
    result['forecast'] = []
    result['observationAt'] = timestamp(data.get('observationAt', data.get('weather_time')))
    for i, row in enumerate(data.get('forecast', [])):
        if not isinstance(row, dict):
            continue
        date = row.get('date')
        if not isinstance(date, str):
            # Legacy caches carry only day labels. Retain the label and expose
            # its synthetic identity without claiming an actual forecast date.
            # The provider sidecar is required for proper dated visualizations.
            continue
        entry = normalize_dto('WeatherForecast', row, identity=date)
        for key, value_key, display_key, unit in [('high', 'highValue', 'high', '°C'), ('low', 'lowValue', 'low', '°C'), ('rainProbability', 'rainProbabilityValue', 'rain', '%')]:
            entry[key] = numeric(row.get(value_key), unit, row.get(display_key, ''))
        result['forecast'].append(entry)
    return result


def _cached(cache, key, raw, build):
    if cache is None:
        return build()
    previous = cache.get(key)
    if previous is not None and snapshot_equal(previous[0], raw):
        return previous[1]
    result = build()
    cache[key] = (deepcopy(raw), result)
    return result


def _style_identity(cache, name, value):
    """Keep borrowed QObject wrappers stable for this context's lifetime.

    QML marshalling can otherwise recreate the Python wrapper on each call.
    A strong reference prevents both cache misses and reuse of a dead wrapper's
    Python id. Factory release/destruction drops the whole private cache.
    It does not take ownership of the QML QObject.
    """
    if cache is not None:
        cache['object-reference:' + name] = value
    return id(value)


def normalize_legacy(surface_id, payload, cache=None, *, validate=True):
    """Private adapter entry point; the legacy model/controller never escapes."""
    surface = CONTRACT.surfaces[surface_id]
    kind = surface['context']
    payload = _mapping(payload)
    model = _mapping(payload.get('model'))
    # Defaults belong to this private normalization cache. Replace top-level
    # fields below; completed public snapshots and context commits own copies.
    values = dict(_cached(cache, 'defaults', kind, lambda: default_snapshot(kind)))
    for name in values:
        if name in payload and name not in ('style', 'visualStyle'):
            spec = CONTRACT.fields(kind)[name]
            if spec['type'] in CONTRACT.types and payload[name] is not None:
                raw = _plain(payload[name])
                values[name] = _cached(cache, 'field:' + name, raw,
                    lambda s=spec, r=raw: normalize_dto(s['type'], r)) if not isinstance(raw, QObject) else normalize_dto(spec['type'], raw)
            elif spec['type'] in CONTRACT.models and isinstance(payload[name], list):
                item_type = CONTRACT.models[spec['type']]['itemType']
                identity_key = CONTRACT.models[spec['type']]['identityRole']
                raw = _plain(payload[name])
                def build_field(rows=raw, dto=item_type, role=identity_key, field=name):
                    return [normalize_dto(dto, row if isinstance(row, dict) else {'id':str(row),'name':str(row),'label':str(row),'enabled':True},
                        identity=str(row.get(role, row.get('canonicalMatchId', row.get('title', row.get('label', f'{surface_id}:{field}:{i}'))))) if isinstance(row, dict) else str(row))
                        for i, row in enumerate(rows)]
                values[name] = _cached(cache, 'field:' + name, raw, build_field)
            else:
                values[name] = _plain(payload[name])
    values['contentId'] = surface_id
    if 'contextVersion' in values:
        values['contextVersion'] = surface['contextVersion']
    style_input = payload.get('style')
    style_key = (_style_identity(cache, 'style', style_input) if isinstance(style_input, QObject) else None, payload.get('appearanceRevision', 0), payload.get('viewportWidth'),
                 payload.get('viewportHeight'), payload.get('mode'),
                 _mapping(payload.get('event')).get('category'), _mapping(payload.get('event')).get('severity'))
    values['style'] = _cached(cache, 'style', style_key if isinstance(style_input, QObject) else style_input,
        lambda: normalize_dto('ThemeStyle', object_snapshot('ThemeStyle', style_input)))
    if 'visualStyle' in values:
        visual_input = payload.get('visualStyle', style_input)
        values['visualStyle'] = _cached(cache, 'visualStyle', (_style_identity(cache, 'visualStyle', visual_input), *style_key[1:]) if isinstance(visual_input, QObject) else visual_input,
            lambda: normalize_dto('NotificationStyle', object_snapshot('NotificationStyle', visual_input)))
    if 'lifecycle' in values:
        active = bool(payload.get('active', False))
        values['lifecycle'] = complete_snapshot('SurfaceLifecycle', {
            'state': payload.get('lifecycleState', 'active' if active else 'preparing'),
            'active': active, 'interactive': bool(payload.get('interactive', False)),
            'preview': bool(payload.get('preview', False)), 'generation': int(payload.get('generation', 0))})
    width = max(0, int(payload.get('viewportWidth', 0)))
    height = max(0, int(payload.get('viewportHeight', 0)))
    if 'viewport' in values:
        values['viewport'] = complete_snapshot('Rect', {'width': width, 'height': height})
    if 'safeArea' in values and 'safeArea' not in payload:
        values['safeArea'] = complete_snapshot('Rect', {'width': width, 'height': height})
    if 'motionPolicy' in values:
        values['motionPolicy'] = complete_snapshot('MotionPolicy', {
            'mode': payload.get('motionMode', 'off'), 'suspended': bool(payload.get('suspended', not payload.get('active', False))),
            'urgent': bool(payload.get('urgent', False))})
    if 'clock' in values:
        values['clock'] = complete_snapshot('ClockState', {'epoch': payload.get('epoch', model.get('now', 0)),
            'timeText': str(payload.get('clockText', '')), 'dateText': str(payload.get('dateText', '')),
            'timezone': str(payload.get('timezone', 'Europe/Rome')), 'locale': str(payload.get('locale', 'it_IT')),
            'night': bool(payload.get('night', False))})
    if 'selection' in values:
        raw = _mapping(payload.get('selection'))
        selected = raw.get('selectedId', payload.get('selectedId', ''))
        if not selected:
            for key in (('teamId',) if surface_id.startswith('sport.team') else ('sportId',) if surface_id.startswith('sport.') else ('racingId',) if surface_id.startswith('racing.') else ()):
                selected = raw.get(key, '')
        selection_rows = values.get('rows', [])
        selected_index = next((i for i, row in enumerate(selection_rows) if row.get('id') == selected), -1)
        values['selection'] = normalize_dto('SelectionState', {**raw, 'selectedId': selected,
            'index': raw.get('index', selected_index), 'count': raw.get('count', len(selection_rows))})
    for name, dto in [('weather', 'WeatherData'), ('account', 'AccountData'), ('nextEvent', 'NextEventData'),
                       ('sport', 'SportData'), ('team', 'TeamData'), ('fantasy', 'FantasyData'), ('racing', 'RacingData'), ('network', 'NetworkData')]:
        if name not in values or name in payload:
            continue
        # NetworkContext projects data below. Sharing this cache key with the
        # full envelope makes each of the two passes evict the other's entry.
        if kind == 'NetworkContext' and name == 'network':
            continue
        raw = _mapping(model.get(name))
        if not raw:
            values[name] = None if CONTRACT.fields(kind)[name].get('nullable') else default_snapshot(dto)
            continue
        envelope = raw if 'data' in raw else {'data': raw, 'status': raw.get('status', 'unavailable')}
        data = _mapping(envelope.get('data'))
        if name == 'nextEvent' and 'data' not in raw:
            envelope = {'data': raw, 'status': 'pending', 'sourceId': str(raw.get('source', ''))}
        values[name] = _cached(cache, 'domain:' + name, envelope,
            lambda n=name, t=dto, e=envelope, d=data: weather_snapshot(e) if n == 'weather' else normalize_dto(t, d, source=source_snapshot(e, n)))
    if kind == 'NotificationContext':
        event = _mapping(payload.get('event'))
        values['eventData'] = normalize_dto('NotificationEvent', event) if event else None
        values['itemModel'] = [normalize_dto('NotificationEvent', row) for row in payload.get('items', [])]
        values['sourceMetadata'] = normalize_dto('SourceState', payload['sourceMetadata']) if isinstance(payload.get('sourceMetadata'), dict) else None
        if 'commands' not in payload:
            values['commands'] = [normalize_dto('Command', hint, identity=f'key:{hint.get("key", i+1)}')
                                  for i, hint in enumerate(payload.get('commandHints', [])) if isinstance(hint, dict)]
    if kind == 'CasaContext':
        envelope=_mapping(payload.get('casaState',model.get('casa')))
        data=_mapping(envelope.get('data'))
        values['casa']=_cached(cache,'domain:casa',data,lambda:normalize_dto('CasaData',data))
        values['source']=source_snapshot(envelope,'casa')
        selected=str(_mapping(payload.get('selection')).get('selectedId',''))
        device=next((row for row in data.get('devices',[]) if row.get('id')==selected),None)
        values['selectedDevice']=normalize_dto('CasaDevice',device) if device else None
    if kind == 'NetworkContext':
        values['overviewSection']=str(payload.get('networkOverviewSection','summary'))
        values['tools']=[normalize_dto('NetworkMetricRow',r) for r in payload.get('networkTools',[])]
        envelope=_mapping(payload.get('networkState',model.get('network')))
        data=_mapping(envelope.get('data'))
        values['network']=_cached(cache,'domain:network',data,lambda:normalize_dto('NetworkData',data))
        values['source']=source_snapshot(envelope,'network')
        selected=str(_mapping(payload.get('selection')).get('selectedId',''))
        device=next((row for row in data.get('devices',[]) if row.get('id')==selected),None)
        values['selectedDevice']=normalize_dto('NetworkDevice',device) if device else None
        values['deviceRows'] = [normalize_dto('NetworkDevice', row) for row in payload.get('networkDeviceRows', [])]
        values['detailRows'] = [normalize_dto('NetworkDetail', row) for row in payload.get('networkDetailRows', [])]
    if kind in ('NetworkRouterContext','NetworkWifiContext','NetworkPortsContext'):
        values['metrics']=normalize_dto('NetworkMetricsView',_mapping(payload.get('networkMetricsView')))
    if kind == 'SceneContext':
        actor = payload.get('actor', payload.get('actorState'))
        values['actor'] = normalize_dto('ActorSnapshot', object_snapshot('ActorSnapshot', actor))
        notification = _mapping(payload.get('notification', payload.get('notificationEvent')))
        values['notification'] = normalize_dto('NotificationEvent', notification) if notification else None
    if kind == 'SportListContext' and 'sport' in model:
        envelope = _mapping(model['sport'])
        data = _mapping(envelope.get('data', envelope))
        sport_source = source_snapshot(envelope, 'sport')
        values['source'] = sport_source
        # A standings route must not reconstruct every match in the season.
        # Cache each public model independently of keyboard selection/clock.
        for name, dto, records in (
            ('standings', 'Standing', data.get('standings', [])),
            ('matches', 'MatchData', payload.get('rows', data.get('fixtures', [])) if surface_id == 'sport.fixtures' else []),
            ('rounds', 'Round', data.get('rounds', []))):
            if name in payload:
                continue
            records = records if isinstance(records, list) else []
            source_key = sport_source if dto == 'MatchData' else None
            def build_rows(rows=records, item_type=dto):
                result = []
                for i, raw_row in enumerate(rows):
                    row = raw_row if isinstance(raw_row, dict) else {'id':str(raw_row), 'label':str(raw_row)}
                    identity = str(row.get('id') or row.get('canonicalMatchId') or row.get('teamId') or f'{surface_id}:{name}:{i}')
                    result.append(normalize_dto(item_type, row, identity=identity, source=sport_source))
                return result
            values[name] = _cached(cache, 'sport-list:' + name, (records, source_key), build_rows)
        if not values['rounds']:
            values['rounds'] = [normalize_dto('Round', {'id':key, 'label':key})
                               for key in sorted({str(row.get('round', '')) for row in data.get('fixtures', []) if row.get('round')})]
        if 'favouriteTeamId' not in payload:
            values['favouriteTeamId'] = str(data.get('favouriteTeamId', data.get('favourite', '')))
    if kind in ('RacingContext', 'DriverContext'):
        racing_envelope = _mapping(model.get('racing'))
        racing_data = _mapping(racing_envelope.get('data', racing_envelope))
        candidate_kind = payload.get('kind', racing_data.get('kind', 'f1'))
        values['kind'] = candidate_kind if candidate_kind in ('f1', 'motogp') else 'f1'
        values['source'] = source_snapshot(racing_envelope, values['kind'])
        if kind == 'RacingContext':
            for name, key, dto in [('event','racingEvent','RacingEventData'), ('session','racingSession','RacingSessionData')]:
                raw = _mapping(payload.get(name, payload.get(key)))
                values[name] = normalize_dto(dto, raw, source=values['source']) if raw else None
        else:
            raw = _mapping(payload.get('driver', payload.get('racingDriver')))
            values['driver'] = normalize_dto('DriverData', raw)
    if kind == 'MatchContext':
        envelope = _mapping(model.get('sport'))
        values['source'] = source_snapshot(envelope, 'sport')
        values['match'] = normalize_dto('MatchData', payload.get('match', payload.get('sportMatch')), source=values['source'])
        fantasy = _mapping(payload.get('fantasyState'))
        values['fantasy'] = normalize_dto('FantasyData', _mapping(fantasy.get('data', fantasy)), source=source_snapshot(fantasy, 'fantasy')) if fantasy else None
    if kind == 'TeamContext':
        envelope = _mapping(model.get('team'))
        data = _mapping(payload.get('teamData', envelope.get('data', envelope)))
        values['team'] = normalize_dto('TeamData', data, source=source_snapshot(envelope, 'team'))
    if kind == 'TeamPickerContext' and 'teams' not in payload:
        envelope = _mapping(model.get('sport'))
        data = _mapping(envelope.get('data', envelope))
        values['teams'] = [normalize_dto('TeamIdentity', row) for row in payload.get('teamPickerRows', data.get('teams', []))]
        values['savedTeamId'] = str(data.get('favourite', ''))
    if kind == 'ShellContext':
        for row in values['families']:
            row['available'] = True
            row['visible'] = True
        values['navigation'] = normalize_dto('NavigationSnapshot', payload.get('navigation', {
            'familyId': payload.get('currentFamilyId', payload.get('familyId', '')),
            'viewId': payload.get('currentViewId', ''), 'overlayId': payload.get('route', '')}))
    if kind == 'SummaryContext':
        rows = []
        def detail_row(identity, title, value, detail=''):
            rows.append(normalize_dto('DashboardCard', {'id':identity, 'title':title, 'value':value, 'detail':detail}))
        if payload.get('familyId') == 'account' and values.get('account'):
            account = values['account']
            for window in account['windows']:
                minutes = window['windowDurationMinutes']['value']
                duration = (f'{minutes / 1440:g} giorni' if minutes % 1440 == 0 else f'{minutes / 60:g} ore' if minutes % 60 == 0 else f'{minutes:g} min') if minutes is not None else 'Durata non disponibile'
                reset = 'Reset ' + datetime.fromtimestamp(window['resetsAt']).astimezone().strftime('%d/%m %H:%M') if window['resetsAt'] else 'Reset non disponibile'
                label = window['label'] if window['label'] == duration else window['label']+' · '+duration
                used = window['usedPercent']
                detail_row(window['id'], label, (used['displayText'].rstrip('%')+'%') if used['available'] else '—', reset+' · percentuale utilizzata')
            credits = account.get('credits')
            if credits:
                detail_row('credits', 'Crediti disponibili', 'Illimitati' if credits['unlimited'] else credits['balance']['displayText'] or '—')
            detail_row('resets', 'Reset disponibili', account['resetCredits']['displayText'] or '—')
            account_source = account.get('source') or {}
            qualification = ('Dato precedente · ' if account_source.get('isStale') or account_source.get('status') not in ('active',) else '') + account_source.get('sourceLabel', '')
            if account_source.get('updatedAt'):
                qualification += ' · ' + datetime.fromtimestamp(account_source['updatedAt']).astimezone().strftime('%d/%m %H:%M')
            for row in rows:
                row['detail'] = ' · '.join(filter(None, [row['detail'], qualification]))
        elif values.get('weather'):
            weather = values['weather']
            source = weather['source']
            qualification = ('Dato precedente · ' if source['isStale'] else '') + source['sourceLabel']
            if values.get('nextEvent') and values['nextEvent']['title']:
                detail_row('event', values['nextEvent']['title'], values['nextEvent']['whenText'])
            for key, label in [('temperature','Temperatura'),('feelsLike','Percepita'),('windSpeed','Vento'),('gusts','Raffiche'),('humidity','Umidità'),('precipitation','Precipitazioni'),('rainProbability','Probabilità del periodo')]:
                value = weather[key]
                detail_row(key, label, value['displayText'] or '—', qualification)
            for day in weather['forecast']:
                detail_row(day['id'], day['date'], day['low']['displayText']+' / '+day['high']['displayText'], day['description']+' · '+qualification)
        values['rows'] = rows
        index = max(0, min(len(rows)-1, int(_mapping(payload.get('selection')).get('index', 0))))
        values['selection'] = normalize_dto('SelectionState', {'selectedId':rows[index]['id'] if rows else '', 'index':index, 'count':len(rows)})
    if payload.get('dashboardId') and not payload.get('dashboardSummary') and 'dashboardSummary' in values:
        summary_model = model
        if payload['dashboardId'] == 'oggi-giornata' and values.get('weather'):
            summary_model = {**model, 'weather': {**_mapping(model.get('weather')), 'data': values['weather']}}
        summary = build_summary(str(payload['dashboardId']), payload, summary_model, float(payload.get('epoch', 0)))
        values['dashboardSummary'] = normalize_dto('DashboardSummary', summary)
    return complete_snapshot(kind, values) if validate else values


class PublicContextFactory(QObject):
    actionRequested = Signal(QObject, str, str, 'QVariantMap', str)
    actionCompleted = Signal(str, 'QVariantMap')
    diagnostic = Signal(str, str)

    def __init__(self, parent=None, dispatch=None, availability=None):
        super().__init__(parent)
        self._contexts = {}
        self._dispatch = dispatch
        self._availability = availability
        self._pending = {}
        self._pending_results = {}
        self._dispatching = set()
        self._history = OrderedDict()
        self._generation = 0
        self._request_counter = 0
        self._session = uuid.uuid4().hex[:12]
        self._normalization_cache = {}

    @Property(str, constant=True)
    def apiFingerprint(self):
        return CONTRACT.fingerprint

    @Slot(str, result='QStringList')
    def modelDomains(self, surface_id):
        """Private bridge projection; never narrows a renderer's public API."""
        surface = CONTRACT.surfaces.get(surface_id)
        if surface is None:
            return []
        kind = surface['context']
        fields = CONTRACT.fields(kind)
        names = [name for name in ('weather', 'account', 'nextEvent', 'sport', 'team', 'fantasy', 'racing','casa','network')
                 if name in fields]
        dependency = {'SportListContext': 'sport', 'MatchContext': 'sport',
                      'TeamPickerContext': 'sport', 'DriverContext': 'racing'}.get(kind)
        if dependency and dependency not in names:
            names.append(dependency)
        return names

    @Slot(QObject)
    def installForEngine(self, owner):
        context = QQmlEngine.contextForObject(owner)
        if context is not None and context.engine() is not None:
            bootstrap_theme_api(context.engine())

    @Slot(str, result=QObject)
    @Slot(str, QObject, result=QObject)
    def create(self, surface_id, parent=None):
        surface = CONTRACT.surfaces.get(surface_id)
        if surface is None:
            self.diagnostic.emit('api.surface.unknown', surface_id)
            return None
        self._generation += 1
        values = default_snapshot(surface['context'])
        values['contentId'] = surface_id
        if 'surfaceInstanceId' in values:
            values['surfaceInstanceId'] = f'{self._session}:{self._generation}'
        if 'contextVersion' in values:
            values['contextVersion'] = surface['contextVersion']
        return self._register_context(surface, values, parent, {})

    def _register_context(self, surface, values, parent, cache, *, validated=False):
        context = PUBLIC_TYPES[surface['context']](values, parent or self, validated=validated)
        context._broker = self
        context._instance_generation = self._generation
        identity = id(context)
        self._contexts[identity] = (context, self._generation)
        self._normalization_cache[identity] = cache
        context.destroyed.connect(lambda *_args, key=identity: self._forget(key))
        QQmlEngine.setObjectOwnership(context, QQmlEngine.CppOwnership)
        return context

    @Slot(str, 'QVariantMap', QObject, result=QObject)
    def createLegacy(self, surface_id, payload, parent=None):
        """Private host bridge: validate before constructing/publishing a tree."""
        surface = CONTRACT.surfaces.get(surface_id)
        if surface is None:
            self.diagnostic.emit('api.surface.unknown', surface_id)
            return None
        cache = {}
        try:
            values = normalize_legacy(surface_id, payload, cache, validate=False)
            generation = self._generation + 1
            if 'surfaceInstanceId' in values:
                values['surfaceInstanceId'] = f'{self._session}:{generation}'
            if 'lifecycle' in values:
                values['lifecycle']['generation'] = generation
            CONTRACT.validate_snapshot(surface['context'], values)
        except (ContractError, TypeError, ValueError, OverflowError) as error:
            self.diagnostic.emit(getattr(error, 'code', 'api.value.invalid'), str(error))
            return None
        self._generation = generation
        context = self._register_context(surface, values, parent, cache, validated=True)
        if 'lifecycle' in values:
            context._runtime_state = context.lifecycle._snapshot()
        else:
            context._runtime_state = {'state': 'exiting' if context.exiting else 'active' if context.active else 'preparing',
                'active': context.active, 'interactive': context.interactive, 'preview': context.preview,
                'generation': generation}
        cache['committed-fields'] = {name: (value, context._snapshots.get(name))
                                    for name, value in values.items()}
        return context

    def _forget(self, identity):
        self._contexts.pop(identity, None)
        self._normalization_cache.pop(identity, None)
        for request_id, entry in tuple(self._pending.items()):
            if entry[0] == identity:
                self._pending.pop(request_id, None)
                tracked = self._pending_results.pop(request_id, None)
                if tracked is not None:
                    tracked._update(self._result(request_id=request_id, error='api.action.generation'))
                    tracked.setParent(None)
                    QQmlEngine.setObjectOwnership(tracked, QQmlEngine.JavaScriptOwnership)
        for request_id, entry in tuple(self._history.items()):
            if entry[0][0] == identity:
                self._history.pop(request_id, None)

    @Slot(QObject)
    def release(self, context):
        if id(context) in self._contexts:
            context._runtime_state = {**context._runtime_state, 'state': 'disposed', 'active': False, 'interactive': False}
            values = context._snapshot()
            if 'lifecycle' in values:
                values['lifecycle'].update(state='disposed', active=False, interactive=False)
            else:
                values.update(active=False, interactive=False)
            context._update(values, validated=True)
            context._broker = None
            for request_id, entry in tuple(self._pending.items()):
                if entry[0] == id(context):
                    tracked = self._pending_results.get(request_id)
                    if tracked is not None:
                        tracked._update(self._result(request_id=request_id, error='api.action.generation'))
            self._forget(id(context))
            context.deleteLater()

    @Slot(QObject, 'QVariantMap', result=bool)
    def update(self, context, snapshot):
        if id(context) not in self._contexts:
            return False
        try:
            fields = CONTRACT.fields(context._type_name)
            if not isinstance(snapshot, dict) or set(snapshot) - set(fields):
                raise ContractError('api.value.unknown', context._type_name, 'Unknown context fields')
            merged = {**context._snapshots, **snapshot}
            # Identity belongs to the factory, not a renderer or host payload.
            if merged.get('contentId') != context.contentId or ('surfaceInstanceId' in merged and merged['surfaceInstanceId'] != context.surfaceInstanceId):
                raise ContractError('api.context.identity', context._type_name, 'Context identity cannot be replaced')
            # Unchanged owned fields were validated on their previous commit.
            # Complete/validate every new field before publishing any signal;
            # invalid nested rows or primitives retain the whole prior snapshot.
            changed = {name: complete_field(fields[name], value,
                                           context._type_name + '/' + name)
                       for name, value in snapshot.items()
                       if name not in context._snapshots or not snapshot_equal(context._snapshots[name], value)}
            merged = {**context._snapshots, **changed}
            definition = CONTRACT.contexts[context._type_name]
            for rule in definition.get('invariants', []):
                if all(type(merged.get(key)) is type(value) and merged[key] == value
                       for key, value in rule['when'].items()):
                    CONTRACT.require(all(merged.get(key) is not None for key in rule['notNull']),
                                     context._type_name, 'dato disponibile privo di valore',
                                     'api.value.availability')
            context._update(changed, validated=True)
            if 'lifecycle' in fields:
                context._runtime_state = context.lifecycle._snapshot()
            else:
                context._runtime_state = {'state': 'exiting' if context.exiting else 'active' if context.active else 'preparing',
                    'active': context.active, 'interactive': context.interactive, 'preview': context.preview,
                    'generation': context._instance_generation}
            return True
        except (ContractError, TypeError, ValueError) as error:
            self.diagnostic.emit(getattr(error, 'code', 'api.value.invalid'), str(error))
            return False

    @Slot(QObject, 'QVariantMap', result=bool)
    def updateLegacy(self, context, payload):
        if id(context) not in self._contexts:
            return False
        try:
            cache = self._normalization_cache[id(context)]
            snapshot = normalize_legacy(context.contentId, payload, cache, validate=False)
            if 'surfaceInstanceId' in snapshot:
                snapshot['surfaceInstanceId'] = context.surfaceInstanceId
            if 'lifecycle' in snapshot:
                snapshot['lifecycle']['generation'] = context._instance_generation
            # Reuse only private normalized values already committed/validated
            # by this factory. A direct public update replaces the owned field
            # and invalidates the shortcut. New values take the normal atomic
            # validation path; no provider/caller dictionaries are trusted.
            committed = cache.get('committed-fields', {})
            delta = {name: value for name, value in snapshot.items()
                     if name not in committed or committed[name][0] is not value
                     or committed[name][1] is not context._snapshots.get(name)}
            accepted = self.update(context, delta)
            if accepted:
                cache['committed-fields'] = {name: (value, context._snapshots.get(name))
                                             for name, value in snapshot.items()}
            return accepted
        except (ContractError, TypeError, ValueError, OverflowError) as error:
            self.diagnostic.emit(getattr(error, 'code', 'api.value.invalid'), str(error))
            return False

    def _result(self, accepted=False, request_id='', status='rejected', error=''):
        return {'accepted': accepted, 'requestId': request_id, 'status': status, 'errorCode': error}

    def _request(self, context, action_id, target_id, arguments):
        entry = self._contexts.get(id(context))
        if entry is None or entry[1] != context._instance_generation:
            return self._result(error='api.action.generation')
        lifecycle = context._runtime_state
        if lifecycle['state'] != 'active' or not lifecycle['active'] or not lifecycle['interactive'] or lifecycle['preview']:
            return self._result(error='api.action.lifecycle')
        try:
            CONTRACT.validate_request(context.contentId, action_id, target_id, arguments)
        except ContractError as error:
            return self._result(error=error.code)
        if self._availability is not None:
            available = self._availability(context.contentId, action_id, target_id, deepcopy(arguments))
            if available is not True:
                return self._result(error=str(available) if isinstance(available, str) else 'api.action.unavailable')
        declared = context._snapshot().get('actions', [])
        if declared and isinstance(declared[0], dict):
            allowed = next((row for row in declared if row['id'] == action_id), None)
            if allowed is None or not allowed['enabled']:
                return self._result(error='api.action.disabled')
        if len(self._pending) >= 128:
            return self._result(error='api.action.busy')
        request_id = arguments.get('requestId')
        signature = (id(context), context._instance_generation, action_id, target_id,
                     {key: value for key, value in arguments.items() if key != 'requestId'})
        if request_id and request_id in self._history:
            previous = self._history[request_id]
            return deepcopy(previous[1]) if previous[0] == signature else self._result(error='api.action.duplicate')
        if request_id and request_id in self._pending:
            return self._result(error='api.action.duplicate')
        self._request_counter += 1
        request_id = request_id or f'{self._session}:{self._request_counter}'
        clean = {key: deepcopy(value) for key, value in arguments.items() if key != 'requestId'}
        if self._dispatch is not None:
            try:
                response = self._dispatch(context.contentId, action_id, target_id, clean, request_id)
            except Exception:
                return self._result(request_id=request_id, status='failed', error='api.action.dispatch')
            if isinstance(response, dict):
                result = {**self._result(request_id=request_id), **response, 'requestId': request_id}
                CONTRACT.validate_snapshot('ActionResult', result)
                self._remember(request_id, signature, result)
                return result
            result = self._result(bool(response), request_id, 'completed' if response else 'rejected', '' if response else 'api.action.unavailable')
            self._remember(request_id, signature, result)
            return result
        # A queued action is accepted only if the private router is connected.
        if self.receivers('2actionRequested(QObject*,QString,QString,QVariantMap,QString)') == 0:
            return self._result(error='api.action.noRouter')
        self._pending[request_id] = (id(context), context._instance_generation, None)
        self._history[request_id] = (signature, self._result(True, request_id, 'pending'))
        self._dispatching.add(request_id)
        try:
            self.actionRequested.emit(context, action_id, target_id, clean, request_id)
        finally:
            self._dispatching.discard(request_id)
        entry = self._pending.get(request_id)
        if entry is not None and entry[2] is not None:
            self._pending.pop(request_id)
            return entry[2]
        return self._result(True, request_id, 'pending')

    def _remember(self, request_id, signature, result):
        self._history[request_id] = (signature, deepcopy(result))
        self._history.move_to_end(request_id)
        while len(self._history) > 256:
            key = next((key for key in self._history if key not in self._pending), None)
            if key is None:
                break
            self._history.pop(key)

    def _track_result(self, obj):
        if obj.requestId in self._pending and obj.status == 'pending':
            obj.setParent(self)
            QQmlEngine.setObjectOwnership(obj, QQmlEngine.CppOwnership)
            self._pending_results[obj.requestId] = obj

    def _flush_adapter(self, context):
        adapter = context.parent()
        if adapter is not None and adapter.metaObject().indexOfMethod('flushRefresh()') >= 0:
            QMetaObject.invokeMethod(adapter, 'flushRefresh', Qt.ConnectionType.DirectConnection)

    @Slot(QObject, str, bool, str, result=bool)
    def completeAction(self, context, request_id, success, error=''):
        entry = self._pending.get(request_id)
        if entry is None or entry[:2] != (id(context), context._instance_generation) or id(context) not in self._contexts:
            return False
        self._flush_adapter(context)
        result = self._result(bool(success), request_id, 'completed' if success else 'failed', error if not success else '')
        if request_id in self._dispatching:
            self._pending[request_id] = (*entry[:2], result)
        else:
            self._pending.pop(request_id, None)
        tracked = self._pending_results.pop(request_id, None)
        if tracked is not None:
            tracked._update(result)
            tracked.setParent(None)
            QQmlEngine.setObjectOwnership(tracked, QQmlEngine.JavaScriptOwnership)
        history = self._history.get(request_id)
        if history is not None:
            self._remember(request_id, history[0], result)
        self.actionCompleted.emit(request_id, result)
        return True


def runtime_typeinfo():
    """Generate actual metaobjects, with validated QObject pointer narrowing.

    Python-defined DTO pointer converters are unavailable in PySide. Nested
    QObject* properties are narrowed to their guaranteed canonical instances
    for tooling; their real backing type remains QObject*. Primitive properties
    and slot signatures are checked against the actual Qt metaobjects.
    """
    import json
    quote = json.dumps
    minors = range(CONTRACT.surfaces_document['module']['minor'] + 1)
    lines = ['import QtQuick.tooling 1.2', '', '// Generated from runtime metaobjects; QObject pointers narrowed by validated canonical DTO contract.', 'Module {']
    for name, cls in PUBLIC_TYPES.items():
        meta = cls.staticMetaObject
        lines += ['    Component {', '        name: ' + quote(name),
                  '        prototype: ' + quote('QAbstractListModel' if name in CONTRACT.models else 'QObject' if meta.superClass().className() == 'ReadOnlySnapshot' else meta.superClass().className()),
                  '        exports: [' + ', '.join(quote('SmartPC.ThemeApi/' + name + ' 2.' + str(minor)) for minor in minors) + ']',
                  '        exportMetaObjectRevisions: [' + ', '.join(str(512 + minor) for minor in minors) + ']', '        isCreatable: false']
        offset = meta.superClass().propertyOffset() if name in CONTRACT.models else meta.propertyOffset()
        for i in range(offset, meta.propertyCount()):
            prop = meta.property(i)
            native = prop.typeName()
            spec = CONTRACT.fields(name).get(prop.name()) if name not in CONTRACT.models else None
            if native == 'QObject*' and spec and spec['type'] in PUBLIC_TYPES:
                native = spec['type'] + '*'
            pointer = native.endswith('*')
            lines += ['        Property {', '            name: ' + quote(prop.name()),
                      '            type: ' + quote(native[:-1] if pointer else native),
                      '            isReadonly: ' + str(not prop.isWritable()).lower()]
            if pointer:
                lines.append('            isPointer: true')
            lines.append('        }')
        offset = meta.superClass().methodOffset() if name in CONTRACT.models else meta.methodOffset()
        for i in range(offset, meta.methodCount()):
            method = meta.method(i)
            if method.methodType().name not in ('Slot', 'Signal'):
                continue
            signal = method.methodType().name == 'Signal'
            lines += ['        Signal {' if signal else '        Method {', '            name: ' + quote(bytes(method.name()).decode())]
            if not signal and method.typeName() != 'void':
                native = method.typeName()
                if native == 'QObject*' and bytes(method.name()).decode() in ('requestAction', 'request'):
                    native = 'ActionResult*'
                lines.append('            type: ' + quote(native.rstrip('*')))
                if native.endswith('*'):
                    lines.append('            isPointer: true')
            for j, parameter in enumerate(method.parameterTypes()):
                native = bytes(parameter).decode()
                lines += ['            Parameter {', '                name: ' + quote('arg' + str(j)),
                          '                type: ' + quote(native.rstrip('*'))]
                if native.endswith('*'):
                    lines.append('                isPointer: true')
                lines.append('            }')
            lines.append('        }')
        lines.append('    }')
    return '\n'.join([*lines, '}', ''])


if __name__ == '__main__':
    module = IMPORT_ROOT / 'SmartPC' / 'ThemeApi'
    module.mkdir(parents=True, exist_ok=True)
    (module / 'runtime.qmltypes').write_text(runtime_typeinfo(), encoding='utf-8')
