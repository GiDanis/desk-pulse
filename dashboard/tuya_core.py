"""Read-only Tuya Cloud probe: signed GETs, account discovery, normalized cache.

No Home Assistant, daemon or third-party packages. No raw responses/tokens are
persisted. Network work must run in a worker when integrated into the Qt app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINTS = frozenset({
    'https://openapi.tuyaeu.com', 'https://openapi-weaz.tuyaeu.com',
    'https://openapi.tuyaus.com', 'https://openapi-ueaz.tuyaus.com',
    'https://openapi.tuyacn.com', 'https://openapi.tuyain.com',
    'https://openapi-sg.iotbing.com',
})
MAX_RESPONSE = 2 * 1024 * 1024
MAX_DEVICES = 500
ID = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
CODE = re.compile(r'[A-Za-z0-9_]{1,100}\Z')


class TuyaError(Exception):
    """An intentionally sanitized diagnostic, safe for CLI and QML."""

    def __init__(self, kind: str, message: str, code: str = ''):
        super().__init__(message)
        self.kind, self.code = kind, code


@dataclass(frozen=True)
class CloudConfig:
    endpoint: str
    access_id: str = field(repr=False)
    access_secret: str = field(repr=False)
    uid: str = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.endpoint, str) or self.endpoint not in ENDPOINTS:
            raise TuyaError('config', 'Endpoint Tuya non supportato: scegliere il data center del progetto.')
        for name in ('access_id', 'access_secret', 'uid'):
            value = getattr(self, name)
            if not isinstance(value, str) or not ID.fullmatch(value):
                raise TuyaError('config', 'Configurazione incompleta o non valida: ' + name)


def load_config(path: Path) -> CloudConfig:
    try:
        # Secrets should never be world/group-readable, or redirected by symlinks.
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'r') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise TuyaError('config', 'Il file delle credenziali deve essere regolare e avere permessi 600.')
            if info.st_size > 16384:
                raise TuyaError('config', 'File di configurazione troppo grande.')
            value = json.load(stream)
        if not isinstance(value, dict):
            raise ValueError
        return CloudConfig(**{key: value.get(key, '') for key in ('endpoint', 'access_id', 'access_secret', 'uid')})
    except (OSError, ValueError, TypeError):
        raise TuyaError('config', 'Configurazione assente o JSON non valido; usare --init-config.') from None


def signature(client_id: str, secret: str, path: str, timestamp: str,
              *, token: str = '', nonce: str = '', signed_headers: str = '') -> str:
    """Tuya cloud signature, including the empty GET body SHA256."""
    canonical = 'GET\n' + hashlib.sha256(b'').hexdigest() + '\n' + signed_headers + '\n' + path
    message = client_id + token + timestamp + nonce + canonical
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest().upper()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(url: str, headers: dict, timeout: float) -> dict:
    try:
        with build_opener(_NoRedirect()).open(Request(url, headers=headers, method='GET'), timeout=timeout) as response:
            body = response.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            raise TuyaError('invalid', 'Risposta Tuya troppo grande.')
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except HTTPError as error:
        kind = 'auth' if error.code in (401, 403) else 'quota' if error.code == 429 else 'http'
        error.close()
        raise TuyaError(kind, f'Tuya HTTP {error.code}; verificare accesso, servizi e quota.', str(error.code)) from None
    except (URLError, TimeoutError, OSError, HTTPException):
        raise TuyaError('offline', 'Cloud Tuya non raggiungibile; ultimo dato da verificare.') from None
    except (ValueError, UnicodeError):
        raise TuyaError('invalid', 'Risposta Tuya non valida.') from None


class CloudClient:
    def __init__(self, config: CloudConfig, *, transport: Callable = http_get,
                 clock: Callable = time.time, monotonic: Callable = time.monotonic):
        self.config, self.transport = config, transport
        self.clock, self.monotonic = clock, monotonic
        self._access_token = self._refresh_token = ''
        self._expires = 0.0
        self.request_count = 0
        # Bind cache to this project/account without persisting their identifiers.
        self.scope = hashlib.sha256('\n'.join((config.endpoint, config.access_id, config.uid)).encode()).hexdigest()

    def _call(self, path: str, params: dict | None = None, *, token: str = ''):
        if params:
            path += '?' + urlencode(sorted(params.items()))
        timestamp = str(int(self.clock() * 1000))
        headers = {
            'client_id': self.config.access_id, 't': timestamp,
            'sign_method': 'HMAC-SHA256', 'Accept': 'application/json',
            'User-Agent': 'SmartPC-Casa/0.7',
            'sign': signature(self.config.access_id, self.config.access_secret, path, timestamp, token=token),
        }
        if token:
            headers['access_token'] = token
        self.request_count += 1
        payload = self.transport(self.config.endpoint + path, headers, 12)
        if not isinstance(payload, dict):
            raise TuyaError('invalid', 'Risposta Tuya non valida.')
        if payload.get('success') is not True:
            raw_code = str(payload.get('code', ''))
            code = raw_code if re.fullmatch(r'[0-9]{1,12}', raw_code) else 'unknown'
            kind = 'token' if code in ('1010', '1011') else 'api'
            # Never echo provider msg, body, URL, secrets or headers.
            if code == '28841107':
                raise TuyaError('api', 'Tuya API 28841107: data center sospeso; abilitarlo nella console del progetto.', code)
            raise TuyaError(kind, f'Tuya API {code}; controllare autorizzazione, data center e servizi.', code)
        if 'result' not in payload:
            raise TuyaError('invalid', 'Risposta Tuya priva del risultato.')
        return payload['result']

    def _authenticate(self, *, fresh=False):
        if not fresh and self._access_token and self.monotonic() < self._expires:
            return
        result = None
        if self._refresh_token and not fresh:
            try:
                result = self._call('/v1.0/token/' + self._refresh_token)
            except TuyaError as error:
                if error.kind != 'token':
                    raise
        if result is None:
            result = self._call('/v1.0/token', {'grant_type': 1})
        if not isinstance(result, dict):
            raise TuyaError('invalid', 'Token Tuya non valido.')
        access, refresh = result.get('access_token'), result.get('refresh_token')
        expiry = result.get('expire_time', result.get('expire'))
        if (not isinstance(access, str) or not ID.fullmatch(access)
                or not isinstance(refresh, str) or not ID.fullmatch(refresh)
                or not _finite(expiry) or expiry <= 0):
            raise TuyaError('invalid', 'Token Tuya incompleto.')
        self._access_token, self._refresh_token = access, refresh
        self._expires = self.monotonic() + max(1, expiry - min(60, expiry / 2))

    def _get(self, path: str, params: dict | None = None):
        self._authenticate()
        try:
            return self._call(path, params, token=self._access_token)
        except TuyaError as error:
            if error.kind != 'token' and error.code != '401':
                raise
            self._authenticate(fresh=True)
            return self._call(path, params, token=self._access_token)

    def inventory(self) -> list[dict]:
        """Only the linked UID, full cursor pagination; never accept half a list."""
        devices, seen, cursors = [], set(), set()
        cursor = ''
        for _ in range(20):
            params = {'source_type': 'tuyaUser', 'source_id': self.config.uid, 'page_size': 100}
            if cursor:
                params['last_row_key'] = cursor
            result = self._get('/v1.3/iot-03/devices', params)
            if (not isinstance(result, dict) or not isinstance(result.get('list'), list)
                    or type(result.get('has_more')) is not bool):
                raise TuyaError('invalid', 'Elenco Tuya incompleto: cache precedente conservata.')
            for row in result['list']:
                normalized = normalize_device(row)
                if normalized['id'] in seen:
                    raise TuyaError('invalid', 'Elenco Tuya con identità duplicate: ripetere la lettura.')
                seen.add(normalized['id'])
                devices.append(normalized)
                if len(devices) > MAX_DEVICES:
                    raise TuyaError('invalid', 'Troppi dispositivi per la prova SmartPC.')
            if not result['has_more']:
                total = result.get('total')
                if total is not None and (type(total) is not int or total != len(devices)):
                    raise TuyaError('invalid', 'Elenco Tuya cambiato durante la lettura: ripetere.')
                return devices
            cursor = result.get('last_row_key')
            if not isinstance(cursor, str) or not cursor or len(cursor) > 1024 or cursor in cursors:
                raise TuyaError('invalid', 'Paginazione Tuya non valida: cache precedente conservata.')
            cursors.add(cursor)
        raise TuyaError('invalid', 'Paginazione Tuya oltre il limite della prova.')

    def device_data(self, device_id: str) -> list[dict]:
        if not isinstance(device_id, str) or not ID.fullmatch(device_id):
            raise TuyaError('config', 'Identificativo dispositivo non valido.')
        specification = self._get(f'/v1.2/iot-03/devices/{device_id}/specification')
        status = self._get(f'/v1.0/iot-03/devices/{device_id}/status')
        return normalize_status(status, specification)


def _text(value, limit=120):
    return ''.join(c for c in value if c.isprintable())[:limit] if isinstance(value, str) else ''


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def normalize_device(row: dict) -> dict:
    if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not ID.fullmatch(row['id']):
        raise TuyaError('invalid', 'Identità dispositivo assente o non valida.')
    return {
        'id': row['id'], 'name': _text(row.get('name')) or 'Dispositivo senza nome',
        'category': _text(row.get('category'), 40), 'model': _text(row.get('model')),
        'productId': _text(row.get('product_id')),
        'online': row.get('online') if type(row.get('online')) is bool else None,
        'gatewayId': _text(row.get('gateway_id')), 'subDevice': row.get('sub') is True,
    }


def normalize_status(status, specification):
    if (not isinstance(status, list) or not isinstance(specification, dict)
            or not isinstance(specification.get('status'), list)):
        raise TuyaError('invalid', 'Stato o specifiche Tuya non validi.')
    specs = {}
    for item in specification['status']:
        if not isinstance(item, dict) or not isinstance(item.get('code'), str) or not CODE.fullmatch(item['code']):
            raise TuyaError('invalid', 'Specifiche Tuya incomplete.')
        if item['code'] in specs:
            raise TuyaError('invalid', 'Specifiche Tuya duplicate.')
        specs[item['code']] = item
    rows, seen = [], set()
    for item in status:
        if (not isinstance(item, dict) or not isinstance(item.get('code'), str)
                or not CODE.fullmatch(item['code']) or item['code'] in seen):
            raise TuyaError('invalid', 'Stati Tuya incompleti o duplicati.')
        code = item['code']; seen.add(code)
        spec = specs.get(code, {})
        try:
            values = json.loads(spec.get('values', '{}')) if isinstance(spec.get('values', '{}'), str) else spec['values']
            if not isinstance(values, dict):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            values = {}
        raw = item.get('value')
        kind = str(spec.get('type', '')).lower()
        value, unit, quality = None, '', 'unverified'
        if kind in ('boolean', 'bool') and type(raw) is bool:
            value, quality = raw, 'reported'
        elif kind in ('integer', 'value') and _finite(raw):
            scale = values.get('scale')
            if type(scale) is int and 0 <= scale <= 9:
                value, unit, quality = raw / 10 ** scale, _text(values.get('unit'), 24), 'reported'
        elif kind in ('enum', 'string') and isinstance(raw, str):
            allowed = values.get('range')
            if kind == 'string' or isinstance(allowed, list) and raw in allowed:
                value, quality = _text(raw), 'reported'
        rows.append({'code': code, 'type': kind, 'value': value, 'unit': unit, 'quality': quality})
    return rows


def inventory_changes(previous: dict | None, current: list[dict]) -> dict:
    old = {d['id']: d for d in (previous or {}).get('devices', [])}
    new = {d['id']: d for d in current}
    return {
        'added': sorted(new.keys() - old.keys()), 'removed': sorted(old.keys() - new.keys()),
        'renamed': sorted(key for key in new.keys() & old.keys() if new[key]['name'] != old[key]['name']),
        'replaced': sorted(key for key in new.keys() & old.keys()
                           if (new[key]['productId'], new[key]['model']) != (old[key]['productId'], old[key]['model'])),
    }


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_inventory(path: Path, scope: str) -> dict | None:
    try:
        if path.stat().st_size > MAX_RESPONSE:
            return None
        value = json.loads(path.read_text())
        if (not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1
                or value.get('scope') != scope
                or not isinstance(value.get('devices'), list) or len(value['devices']) > MAX_DEVICES
                or not _finite(value.get('checkedAt')) or value['checkedAt'] <= 0):
            return None
        # Rebuild an allowlisted schema even if a cache was externally edited.
        devices = []
        for row in value['devices']:
            if not isinstance(row, dict):
                return None
            row = {**row, 'product_id': row.get('productId'), 'gateway_id': row.get('gatewayId'), 'sub': row.get('subDevice')}
            devices.append(normalize_device(row))
        if len({d['id'] for d in devices}) != len(devices):
            return None
        return {'version': 1, 'scope': scope, 'checkedAt': value['checkedAt'], 'devices': devices}
    except (OSError, ValueError, TypeError, TuyaError):
        return None


def synchronize(client: CloudClient, path: Path) -> tuple[dict, dict]:
    previous = read_inventory(path, client.scope)
    devices = client.inventory()  # No write until every page has passed validation.
    checked_at = client.clock()
    if not _finite(checked_at) or checked_at <= 0:
        raise TuyaError('invalid', 'Ora di acquisizione non valida.')
    snapshot = {'version': 1, 'scope': client.scope, 'checkedAt': checked_at, 'devices': devices}
    changes = inventory_changes(previous, devices)
    atomic_json(path, snapshot)
    return snapshot, changes
