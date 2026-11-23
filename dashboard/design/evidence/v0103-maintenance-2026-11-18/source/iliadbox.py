"""Bounded local HTTPS Freebox/iliadbox client; no administrative password."""
from __future__ import annotations

import hashlib
import hmac
import http.client
import ipaddress
import json
import re
import socket
import ssl
import stat
import time
from pathlib import Path

CA_FILE = Path(__file__).with_name('resources') / 'iliadbox-ca.pem'
MAX_BODY = 4 * 1024 * 1024


class NetworkError(Exception):
    def __init__(self, kind, message, code=""):
        self.code = code
        super().__init__(message)
        self.kind = kind


def load_config(path):
    try:
        p = Path(path)
        if stat.S_IMODE(p.stat().st_mode) & 0o077 or p.stat().st_size > 16384:
            raise NetworkError('config', 'Credenziale Rete non privata o non valida.')
        data = json.loads(p.read_text())
        address = ipaddress.ip_address(data['router'])
        if not address.is_private or address.is_loopback or address.is_multicast:
            raise ValueError('non local router')
        for field in ('app_id', 'app_token', 'router_uid', 'api_domain'):
            if not isinstance(data[field], str) or not 1 <= len(data[field]) <= 512:
                raise ValueError(field)
        if not re.fullmatch(r'[A-Za-z0-9.-]+', data['api_domain']):
            raise ValueError('invalid hostname')
        return {k: data[k] for k in ('router', 'app_id', 'app_token', 'router_uid', 'api_domain')}
    except (OSError, KeyError, ValueError, TypeError):
        raise NetworkError('config', 'Configura la credenziale privata iliadbox e rileggi Rete.') from None


class LocalHTTPS(http.client.HTTPSConnection):
    def __init__(self, config, context, timeout):
        super().__init__(config['api_domain'], timeout=timeout, context=context)
        self.router = config['router']

    def connect(self):
        raw = socket.create_connection((self.router, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


class IliadboxClient:
    def __init__(self, config, *, transport=None, cancelled=lambda: False):
        self.config = config
        self.scope = hashlib.sha256(config['router_uid'].encode()).hexdigest()[:24]
        self.cancelled = cancelled
        self.transport = transport or self._https
        self.token = None
        self.base = None
        self.permissions = {}
        self.requests = 0
        self._renewals = 0
        self.deadline = float('inf')
        self.context = ssl.create_default_context(cafile=str(CA_FILE))
        # Legacy vendor CA lacks AKI under Python >=3.13's strict profile.
        # Keep chain signatures, expiry and hostname verification enabled.
        self.context.verify_flags &= ~ssl.VERIFY_X509_STRICT
        assert self.context.check_hostname and self.context.verify_mode == ssl.CERT_REQUIRED

    def _https(self, method, path, body, token, timeout):
        conn = LocalHTTPS(self.config, self.context, timeout)
        headers = {'Accept': 'application/json'}
        if token:
            headers['X-Fbx-App-Auth'] = token
        if body is not None:
            headers['Content-Type'] = 'application/json'
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, headers)
            response = conn.getresponse()
            chunks=[]
            size=0
            deadline=min(self.deadline,time.monotonic()+5)
            while True:
                if self.cancelled() or time.monotonic()>=deadline:
                    raise NetworkError('cancelled','Lettura Rete interrotta o scaduta.')
                if conn.sock:
                    conn.sock.settimeout(min(timeout,max(0.01,deadline-time.monotonic())))
                chunk=response.read1(min(65536,MAX_BODY+1-size))
                if not chunk:
                    break
                chunks.append(chunk);size+=len(chunk)
                if size>MAX_BODY:
                    raise NetworkError('invalid','Risposta Rete oltre il limite previsto.')
            raw=b''.join(chunks)
            if len(raw) > MAX_BODY:
                raise NetworkError('invalid', 'Risposta Rete oltre il limite previsto.')
            return json.loads(raw)
        except ssl.SSLError:
            raise NetworkError('tls', 'Certificato iliadbox non verificato; accesso sospeso.') from None
        except (OSError, http.client.HTTPException):
            raise NetworkError('transport', 'iliadbox non raggiungibile; dati precedenti conservati.') from None
        except (ValueError, UnicodeError):
            raise NetworkError('invalid', 'Risposta iliadbox non valida.') from None
        finally:
            conn.close()

    def request(self, method, path, body=None, *, authenticated=True, cleanup=False):
        if not cleanup and (self.cancelled() or time.monotonic() >= self.deadline):
            raise NetworkError('cancelled', 'Acquisizione Rete interrotta o scaduta.')
        self.requests += 1
        data = self.transport(method, path, body, self.token if authenticated else None, 2.5)
        if not isinstance(data, dict) or type(data.get('success')) is not bool:
            raise NetworkError('invalid', 'Envelope iliadbox non valido.')
        if not data['success']:
            code = data.get('error_code')
            kind = 'auth' if code in ('auth_required', 'invalid_token', 'pending_token', 'insufficient_rights', 'apps_denied') else 'api'
            raise NetworkError(kind, 'Autorizzazione iliadbox assente o revocata.' if kind == 'auth' else 'Lettura iliadbox non disponibile.', code if code in ('auth_required','invalid_token','pending_token','insufficient_rights','apps_denied') else '')
        return data.get('result')

    def open(self, *, renewal=False):
        if not renewal:self._renewals=0
        meta = self.transport('GET', '/api_version', None, None, 2.5)
        self.requests += 1
        if not isinstance(meta, dict) or meta.get('uid') != self.config['router_uid']:
            raise NetworkError('identity', 'Identità del router diversa; autorizzazione da verificare.')
        version = str(meta.get('api_version', '')).split('.')[0]
        base = meta.get('api_base_url')
        if not version.isdigit() or not 1 <= int(version) <= 99 or not isinstance(base, str) or not re.fullmatch(r'/[a-zA-Z0-9_/]+/', base):
            raise NetworkError('invalid', 'Versione API iliadbox non valida.')
        self.base = base.rstrip('/') + '/v' + version
        challenge = self.request('GET', self.base + '/login/', authenticated=False)
        if not isinstance(challenge, dict) or not isinstance(challenge.get('challenge'), str):
            raise NetworkError('invalid', 'Challenge iliadbox non valido.')
        password = hmac.new(self.config['app_token'].encode(), challenge['challenge'].encode(), hashlib.sha1).hexdigest()
        session = self.request('POST', self.base + '/login/session/', {'app_id': self.config['app_id'], 'password': password}, authenticated=False)
        if not isinstance(session, dict) or not isinstance(session.get('session_token'), str) or not session['session_token']:
            raise NetworkError('invalid', 'Sessione iliadbox non valida.')
        self.token = session['session_token']
        permissions=session.get('permissions',{})
        if not isinstance(permissions,dict):
            raise NetworkError('invalid','Permessi iliadbox non validi.')
        self.permissions = {k: v for k, v in permissions.items() if isinstance(k, str) and type(v) is bool}

    def get(self, path):
        try:
            return self.request('GET', self.base + path)
        except NetworkError as e:
            if e.code == 'insufficient_rights':
                raise NetworkError('permission', 'Permesso assente per questa fonte.', e.code) from None
            if e.code != 'auth_required' or self._renewals>=1:
                raise
            self._renewals+=1
            self.close()
            self.open(renewal=True)
            try:
                return self.request('GET', self.base + path)
            except NetworkError as second:
                if second.code=='insufficient_rights':
                    raise NetworkError('permission','Permesso assente per questa fonte.',second.code) from None
                raise

    def close(self):
        if self.token:
            try:
                self.request('POST', self.base + '/login/logout/', cleanup=True)
            except NetworkError:
                pass  # Session is never persisted; it expires at the router.
            finally:
                self.token = None
