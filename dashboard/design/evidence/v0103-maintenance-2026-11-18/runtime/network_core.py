"""Normalized router observations and private transactional LAN history."""
from __future__ import annotations
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime
import ipaddress
import json
import math
import re
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.parse import quote

from iliadbox import NetworkError

INTERVAL = 300
MAX_HOSTS = 256
MAX_ADDRESSES = 32


def text(value, limit=160):
    return ''.join(c for c in value if c.isprintable())[:limit] if isinstance(value, str) else ''


def stamp(value):
    return datetime.fromtimestamp(value).strftime('%d/%m %H:%M') if value else 'Non disponibile'


def epoch(value, now):
    return float(value) if type(value) in (int, float) and 0 < value <= now + 5 else None


def empty(scope=''):
    return {'version': 1, 'scope': scope, 'checkedAt': 0, 'devices': [], 'coverage': '', 'interfaces': [], 'wan': '', 'local': {}, 'preferences': {'favourites': [], 'aliases': {}, 'polling': True}}


class NetworkStore:
    def __init__(self, directory, scope):
        if not re.fullmatch(r'[a-f0-9]{24}|demo', scope):
            raise NetworkError('storage', 'Identità archivio Rete non valida.')
        self.directory, self.scope = Path(directory), scope
        self.path = self.directory / (scope + '.sqlite3')

    @contextmanager
    def connection(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)
        conn = sqlite3.connect(self.path, timeout=1)
        self.path.chmod(0o600)
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS history (day TEXT PRIMARY KEY, first REAL, last REAL, cycles INTEGER, max_reachable INTEGER)')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def load(self):
        try:
            with self.connection() as conn:
                row = conn.execute('SELECT value FROM state WHERE id=1').fetchone()
                if row and len(row[0]) > 4 * 1024 * 1024:
                    raise ValueError('oversized snapshot')
                result = json.loads(row[0]) if row else empty(self.scope)
                if result.get('version') != 1 or result.get('scope') != self.scope or not isinstance(result.get('devices'), list):
                    raise ValueError('invalid snapshot')
                prefs = conn.execute('SELECT value FROM preferences WHERE id=1').fetchone()
                result['preferences'] = json.loads(prefs[0]) if prefs else empty()['preferences']
                prefs = result['preferences']
                if not isinstance(prefs, dict) or not isinstance(prefs.get('favourites'), list) or len(prefs['favourites']) > 4 or not all(isinstance(i, str) for i in prefs['favourites']) or not isinstance(prefs.get('aliases'), dict) or not all(isinstance(k, str) and isinstance(v, str) and len(v) <= 80 for k, v in prefs['aliases'].items()) or type(prefs.get('polling')) is not bool:
                    raise ValueError('invalid preferences')
                if len(result['devices']) > MAX_HOSTS or type(result.get('checkedAt')) not in (int, float) or not math.isfinite(result['checkedAt']) or result['checkedAt'] < 0:
                    raise ValueError('invalid cache')
                for d in result['devices']:
                    if not isinstance(d, dict) or not all(k in d for k in ['id','hostId','interface','name','mac','localMac','vendor','kind','addresses','nameSources','reachable','active','present','collectedAt','lastSeen','lastActivity','firstActivity','connection','connectionAt']):
                        raise ValueError('invalid cached host')
                    if any(not isinstance(d[k], str) or len(d[k])>256 for k in ['id','hostId','interface','name','mac','vendor','kind','connection']):
                        raise ValueError('invalid cached text')
                    if any(type(d[k]) is not bool for k in ['localMac','reachable','active','present']):
                        raise ValueError('invalid cached state')
                    if any(d[k] is not None and (type(d[k]) not in (int,float) or not math.isfinite(d[k]) or not 0<=d[k]<=4102444800) for k in ['collectedAt','lastSeen','lastActivity','firstActivity','connectionAt','firstObserved','lastObserved'] if k in d):
                        raise ValueError('invalid cached timestamp')
                    if not isinstance(d['addresses'],list) or len(d['addresses'])>MAX_ADDRESSES or not isinstance(d['nameSources'],list) or not all(isinstance(n,str) for n in d['nameSources']):
                        raise ValueError('invalid cached endpoints')
                    for addr in d['addresses']:
                        if not isinstance(addr,dict) or set(addr)!=set(['address','family','reachable','lastSeen']) or addr['family'] not in ('ipv4','ipv6') or type(addr['reachable']) is not bool:
                            raise ValueError('invalid cached address')
                        ipaddress.ip_address(addr['address'])
                        if addr['lastSeen'] is not None and (type(addr['lastSeen']) not in (int,float) or not math.isfinite(addr['lastSeen']) or not 0<addr['lastSeen']<=4102444800):
                            raise ValueError('invalid cached address timestamp')
                if not isinstance(result.get('coverage'),str) or not isinstance(result.get('wan'),str) or not isinstance(result.get('local'),dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in result['local'].items()):
                    raise ValueError('invalid cached metadata')
                return result
        except (OSError, sqlite3.Error, ValueError, TypeError):
            raise NetworkError('storage', 'Archivio Rete non leggibile; dati non confermati.') from None

    def commit(self, snapshot=None, preferences=None):
        try:
            with self.connection() as conn:
                if snapshot is not None:
                    conn.execute('INSERT OR REPLACE INTO state VALUES(1,?)', (json.dumps({k: v for k, v in snapshot.items() if k != 'preferences'}, allow_nan=False),))
                    now = snapshot['checkedAt']
                    day = datetime.fromtimestamp(now).strftime('%Y-%m-%d')
                    count = sum(d['reachable'] for d in snapshot['devices'] if d['present'])
                    conn.execute('INSERT INTO history VALUES(?,?,?,1,?) ON CONFLICT(day) DO UPDATE SET last=excluded.last, cycles=cycles+1, max_reachable=max(max_reachable,excluded.max_reachable)', (day, now, now, count))
                    conn.execute("DELETE FROM history WHERE day < date(?,'-30 days')", (day,))
                if preferences is not None:
                    conn.execute('INSERT OR REPLACE INTO preferences VALUES(1,?)', (json.dumps(preferences, allow_nan=False),))
        except (OSError, sqlite3.Error, ValueError):
            raise NetworkError('storage', 'Archivio Rete non scrivibile; salvataggio non confermato.') from None


def local_info():
    try:
        route = subprocess.run(['ip', '-j', 'route'], capture_output=True, timeout=1, check=True)
        routes = json.loads(route.stdout)
        default = next((r for r in routes if r.get('dst') == 'default'), {})
        dev = default.get('dev', '')
        if not dev:
            return {'state': 'unavailable', 'interface': '', 'gateway': '', 'address': ''}
        carrier = Path('/sys/class/net') / dev / 'carrier'
        if carrier.exists() and carrier.read_text().strip() == '0':
            return {'state':'offline','interface':text(dev,32),'gateway':'','address':''}
        addresses=json.loads(subprocess.run(['ip','-j','address','show','dev',dev],capture_output=True,timeout=1,check=True).stdout)
        address=next((a.get('local','') for row in addresses for a in row.get('addr_info',[]) if a.get('scope')=='global' and a.get('family')=='inet'),default.get('prefsrc',''))
        return {'state': 'configured', 'interface': text(dev, 32), 'gateway': text(default.get('gateway')), 'address': text(address)}
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return {'state': 'unavailable', 'interface': '', 'gateway': '', 'address': ''}


def normalize_host(row, interface, scope, now):
    if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or len(row['id']) > 256:
        raise NetworkError('invalid', 'Identificatore host non valido; snapshot precedente conservato.')
    if type(row.get('reachable')) is not bool or type(row.get('active')) is not bool:
        raise NetworkError('invalid', 'Stato host incompleto; snapshot precedente conservato.')
    identity = scope + ':' + interface + ':' + row['id']
    import hashlib
    identity = hashlib.sha256(identity.encode()).hexdigest()[:32]
    l2 = row.get('l2ident', {})
    if not isinstance(l2, dict) or not isinstance(row.get('l3connectivities', []), list):
        raise NetworkError('invalid', 'Indirizzi host non validi; snapshot precedente conservato.')
    addresses = []
    for a in row.get('l3connectivities', [])[:MAX_ADDRESSES]:
        if not isinstance(a, dict):
            raise NetworkError('invalid', 'Connettività host non valida.')
        try:
            address = ipaddress.ip_address(a.get('addr', ''))
        except ValueError:
            continue
        family = 'ipv4' if address.version == 4 else 'ipv6'
        if a.get('af') != family:
            continue
        addresses.append({'address': str(address), 'family': family, 'reachable': a.get('reachable') is True, 'lastSeen': epoch(a.get('last_time_reachable'), now)})
    addresses.sort(key=lambda a: (not a['reachable'], a['family'] != 'ipv4', a['address']))
    mac = text(l2.get('id'), 48).upper()
    local_mac = False
    try:
        local_mac = bool(int(mac[:2], 16) & 2)
    except ValueError:
        pass
    if not isinstance(row.get('names', []),list) or len(row.get('names',[]))>32:
        raise NetworkError('invalid','Fonti del nome host non valide.')
    sources = sorted({text(n.get('source'), 32) for n in row.get('names', []) if isinstance(n, dict) and n.get('source')})
    return {'id': identity, 'hostId': row['id'], 'interface': interface, 'name': text(row.get('primary_name')) or text(row.get('default_name')) or (addresses[0]['address'] if addresses else 'Identità senza nome'), 'mac': mac, 'localMac': local_mac, 'vendor': '' if local_mac else text(row.get('vendor_name')), 'kind': text(row.get('host_type'), 48), 'addresses': addresses, 'nameSources': sources, 'reachable': row['reachable'], 'active': row['active'], 'present': True, 'collectedAt': now, 'lastSeen': epoch(row.get('last_time_reachable'), now), 'lastActivity': epoch(row.get('last_activity'), now), 'firstActivity': epoch(row.get('first_activity'), now), 'connection': '', 'connectionAt': None}


def acquire(client, previous, now, local=None):
    client.deadline = time.monotonic() + 20
    try:
        client.open()
        interfaces = client.get('/lan/browser/interfaces/')
        if not isinstance(interfaces, list) or not 1 <= len(interfaces) <= 8:
            raise NetworkError('invalid', 'Elenco interfacce iliadbox non valido.')
        fresh, reports, problems = [], [], []
        succeeded = set()
        for interface in interfaces:
            if not isinstance(interface, dict) or not isinstance(interface.get('name'), str) or not interface['name'] or len(interface['name']) > 32:
                raise NetworkError('invalid', 'Interfaccia inventario non valida.')
            name = interface['name']
            if name in {r['name'] for r in reports}:
                raise NetworkError('invalid', 'Interfaccia duplicata.')
            hosts = client.get('/lan/browser/' + quote(name, safe='') + '/')
            count=interface.get('host_count')
            if count is not None and (type(count) is not int or not 0<=count<=100000):
                raise NetworkError('invalid','Contatore interfaccia non valido.')
            report = {'name': name, 'reportedCount': interface.get('host_count'), 'count': None, 'available': False}
            reports.append(report)
            if hosts is None:
                problems.append(name + ': inventario non disponibile')
                continue
            if not isinstance(hosts, list) or len(hosts) > MAX_HOSTS or len(fresh) + len(hosts) > MAX_HOSTS:
                raise NetworkError('invalid', 'Inventario fuori limite o incompleto.')
            batch = [normalize_host(h, name, client.scope, now) for h in hosts]
            if len({d['id'] for d in batch}) != len(batch):
                raise NetworkError('invalid', 'Inventario con identità duplicate.')
            fresh.extend(batch)
            succeeded.add(name)
            report.update(count=len(batch), available=True)
            if report['reportedCount'] != len(batch):
                problems.append(name + ': ' + str(len(batch)) + ' record / ' + str(report['reportedCount']) + ' contatore box')
        if not succeeded:
            raise NetworkError('api', 'Nessun inventario iliadbox disponibile.')
        # Optional enrichments fail independently; their previous values never
        # become current associations for a newly collected host.
        def optional(path, default):
            try:
                return client.get(path)
            except NetworkError as e:
                if e.kind in ('auth', 'identity', 'tls', 'cancelled'):
                    raise
                problems.append('Collegamento parziale: ' + path.split('/')[1])
                return default
        by_host = {(d['interface'], d['hostId']): d for d in fresh}
        by_mac = {}
        for d in fresh:
            if d['mac']:
                by_mac.setdefault(d['mac'], []).append(d)
        aps = optional('/wifi/ap/', [])
        if isinstance(aps, list):
            for ap in aps[:8]:
                if not isinstance(ap, dict) or type(ap.get('id')) not in (str, int):
                    continue
                aid = ap['id']
                stations = optional('/wifi/ap/' + quote(str(aid), safe='') + '/stations/', [])
                if not isinstance(stations, list):
                    continue
                config=ap.get('config')
                band = text(config.get('band'),16) if isinstance(config,dict) else ''
                band = {'2d4g': '2,4 GHz', '5g': '5 GHz', '6g': '6 GHz'}.get(band, band)
                for station in stations[:MAX_HOSTS]:
                    if not isinstance(station, dict) or station.get('state') not in ('associated', 'authenticated'):
                        continue
                    h = station.get('host', {})
                    if not isinstance(h, dict):
                        continue
                    d = by_host.get((h.get('interface', 'pub'), h.get('id')))
                    if d and text(station.get('mac')).upper() == d['mac']:
                        d['connection'] = 'Wi-Fi ' + band + ' · AP ' + str(aid)
                        d['connectionAt'] = now
        ports = optional('/switch/status/', [])
        if isinstance(ports, list):
            for port in ports[:16]:
                if not isinstance(port, dict) or port.get('link') != 'up':
                    continue
                entries=port.get('mac_list',[])
                if not isinstance(entries,list):
                    continue
                for entry in entries[:MAX_HOSTS]:
                    if not isinstance(entry, dict):
                        continue
                    matches = by_mac.get(text(entry.get('mac')).upper(), [])
                    if len(matches) == 1:
                        d = matches[0]
                        if d['connection']:
                            d['connection'] += ' · visto anche da porta ' + str(port.get('id', ''))
                        else:
                            d['connection'] = 'Visto da porta ' + str(port.get('id', '')) + ' · ' + text(str(port.get('speed', ''))) + ' Mbit/s'
                        d['connectionAt'] = now
        wan = optional('/connection/', {})
        wan_text = ''
        if isinstance(wan, dict) and wan.get('state') in ('up', 'down', 'going_up', 'going_down'):
            wan_text = 'Internet secondo box: ' + {'up': 'disponibile', 'down': 'non disponibile', 'going_up': 'avvio', 'going_down': 'interruzione'}[wan['state']]
            if wan.get('media') == 'ftth':
                wan_text += ' · FTTH'
        previous_ids={d['id']:d for d in previous['devices']}
        for d in fresh:
            old=previous_ids.get(d['id'],{})
            d['firstObserved']=old.get('firstObserved',now)
            d['lastObserved']=now
        present = {d['id'] for d in fresh}
        for old in previous['devices']:
            if old['id'] not in present and (old['id'] in previous['preferences']['favourites'] or now - old['collectedAt'] < 30 * 86400):
                row = deepcopy(old)
                row['present'] = False
                fresh.append(row)
        if len(fresh) > MAX_HOSTS:
            fresh.sort(key=lambda d: (d['id'] not in previous['preferences']['favourites'], not d['present'], -d['collectedAt']))
            fresh = fresh[:MAX_HOSTS]
            problems.append('Storico limitato a 256 identità')
        result = empty(client.scope)
        result.update(checkedAt=now, devices=fresh, preferences=deepcopy(previous['preferences']), interfaces=reports, coverage=' · '.join(problems) or 'Inventario router', wan=wan_text, local=local or {})
        return result
    finally:
        client.close()


def display(snapshot, status, now):
    current = status == 'active' and 0 <= now - snapshot['checkedAt'] < INTERVAL + 5
    prefs = snapshot['preferences']
    devices = []
    def detail(identity, section, title, value, note=''):
        return {'id': identity, 'section': section, 'title': title, 'value': str(value or 'Non disponibile'), 'detail': note}
    for saved in snapshot['devices']:
        d = deepcopy(saved)
        fresh = current and d['present'] and d['collectedAt'] == snapshot['checkedAt']
        d['favourite'] = d['id'] in prefs['favourites']
        d['originalName'] = d['name']
        d['name'] = prefs['aliases'].get(d['id']) or d['name']
        d['previous'] = not fresh
        d['primaryAddress'] = d['addresses'][0]['address'] if d['addresses'] else 'Indirizzo non disponibile'
        d['statusText'] = 'Raggiungibile secondo box' if fresh and d['reachable'] else 'Non raggiungibile secondo box' if fresh else 'Dati salvati · presenza non verificata'
        d['connectionText'] = d['connection'] or 'Collegamento non verificato'
        if d['connection'] and not fresh:
            d['connectionText'] += ' · precedente'
        note = 'Fonte iliadbox · ' + stamp(d['collectedAt']) + (' · dato salvato' if not fresh else '')
        details = [detail('name', 'identity', 'Nome riportato', d['originalName'], note), detail('alias', 'identity', 'Alias dashboard', prefs['aliases'].get(d['id']), 'Separato dal nome sul router'), detail('type', 'identity', 'Tipo secondo box', d['kind'], note), detail('mac', 'identity', 'MAC', d['mac'], 'MAC locale: produttore non determinabile' if d['localMac'] else note), detail('vendor', 'identity', 'Produttore probabile', d['vendor'], note), detail('sources', 'identity', 'Fonti del nome', ', '.join(d['nameSources']), note), detail('link', 'link', 'Collegamento', d['connectionText'], note), detail('scope', 'link', 'Interfaccia inventario', d['interface'], 'Una porta può avere più host a valle'), detail('seen', 'observations', 'Ultimo riscontro box', stamp(d['lastSeen']), 'Timestamp del router, non del refresh'), detail('activity', 'observations', 'Ultima attività box', stamp(d['lastActivity']), note), detail('first', 'observations', 'Prima attività box', stamp(d['firstActivity']), 'Non coincide con la prima osservazione dashboard'), detail('read', 'observations', 'Lettura inventario', stamp(d['collectedAt']), note)]
        details += [detail('first-dashboard','observations','Prima lettura dashboard',stamp(d.get('firstObserved')), 'Archivio locale · identità non equiparata a una persona')]
        details += [detail('address:' + a['address'], 'addresses', a['family'].upper(), a['address'], ('Raggiungibile secondo box' if a['reachable'] and fresh else 'Riscontro precedente / non corrente') + ' · ' + stamp(a['lastSeen'])) for a in d['addresses']]
        d['details'] = details
        # Whitelist the public device; never forward raw responses or host IDs.
        devices.append({k: d[k] for k in ('id', 'name', 'originalName', 'kind', 'mac', 'vendor', 'interface', 'primaryAddress', 'connectionText', 'statusText', 'previous', 'favourite', 'lastSeen', 'collectedAt', 'details')})
    devices.sort(key=lambda d: (d['previous'], d['name'].casefold(), d['id']))
    by_id = {d['id']: d for d in devices}
    favourites = [by_id[i] for i in prefs['favourites'] if i in by_id]
    count = sum(d['reachable'] for d in snapshot['devices'] if current and d['present'] and d['collectedAt'] == snapshot['checkedAt'])
    return {'devices': devices, 'favourites': favourites, 'knownCount': len(devices), 'reachableText': str(count) if current else '—', 'countCurrent': current, 'coverage': snapshot['coverage'], 'wanText': snapshot['wan'] + ('' if current else ' · precedente') if snapshot['wan'] else 'Internet non verificato', 'localText': 'LAN board: ' + snapshot['local'].get('interface', 'non verificata') + (' · ' + snapshot['local'].get('address', '') if snapshot['local'].get('address') else ''), 'polling': prefs['polling'], 'readOnly': True}


def demo_snapshot(now):
    result = empty('demo')
    result['checkedAt'] = now
    result['coverage'] = 'Demo · dati simulati'
    result['wan'] = 'Internet secondo box: disponibile · FTTH (demo)'
    result['local'] = {'interface': 'wlan0', 'address': '192.0.2.20'}
    for i, name in enumerate(['Computer studio', 'Telefono', 'Stampante', 'Hub Casa', 'Televisore', 'Portatile']):
        row = {'id': str(i), 'primary_name': name, 'reachable': i < 4, 'active': i < 4, 'host_type': 'workstation', 'l2ident': {'id': '02:00:00:00:00:' + str(i).zfill(2)}, 'l3connectivities': [{'addr': '192.0.2.' + str(30 + i), 'af': 'ipv4', 'reachable': i < 4, 'last_time_reachable': now - i * 60}], 'last_time_reachable': now - i * 60}
        d = normalize_host(row, 'pub', 'demo', now)
        d['connection'] = 'Wi-Fi 5 GHz · AP 1' if i < 3 else 'Visto da porta 2 · 100 Mbit/s'
        d['connectionAt'] = now
        result['devices'].append(d)
    result['preferences']['favourites'] = [d['id'] for d in result['devices'][:4]]
    return result
