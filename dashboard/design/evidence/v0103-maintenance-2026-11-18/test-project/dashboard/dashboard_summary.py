"""Read-only dashboard projections. No I/O, polling, or provider mutation."""
from datetime import datetime
from math import isfinite
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('Europe/Rome')
ENVIRONMENT_CODES = {'va_temperature', 'temp_current', 'va_humidity', 'humidity_value', 'pir'}


def number(value):
    if isinstance(value, dict):
        value = value.get('value') if value.get('available', True) else None
    return value if type(value) in (int, float) and isfinite(value) else None


def display(value, unit=''):
    if isinstance(value, dict) and value.get('displayText'):
        return str(value['displayText'])
    n = number(value)
    return ('—' if n is None else f'{n:g}') + ((' ' + unit) if n is not None and unit else '')


def stamp(value, only_time=False):
    n = number(value)
    if n is None or n <= 0:
        return 'Orario non disponibile'
    try:
        return datetime.fromtimestamp(n, ZONE).strftime('%H:%M' if only_time else '%d/%m · %H:%M')
    except (ValueError, OverflowError, OSError):
        return 'Orario non disponibile'


def state(envelope):
    return {'active': 'Aggiornato', 'stale': 'Dato precedente', 'offline': 'Offline · precedente',
            'updating': 'Aggiornamento', 'error': 'Errore fonte', 'unavailable': 'Non disponibile'}.get(envelope.get('status'), 'Non disponibile')


def environment_devices(data):
    rows = data.get('devices') or []
    preferred = {row.get('id'): i for i, row in enumerate(data.get('favourites') or [])}
    return sorted([r for r in rows if any(m.get('code') in ENVIRONMENT_CODES and m.get('quality') == 'reported'
                                        for m in r.get('metrics') or [])],
                  key=lambda r: (preferred.get(r.get('id'), 999), str(r.get('id', ''))))


def build_summary(view_id, payload, model, now):
    """Select qualified information, then place it in a native landscape grid."""
    cards = []
    result = {'id': view_id, 'title': '', 'subtitle': '', 'cards': cards, 'detailTarget': '', 'detailRows': []}

    def card(identity, title, value, detail='', icon='info', previous=False, value_size=52, subtitle='', target=''):
        cards.append({'id': str(identity), 'title': str(title), 'value': str(value), 'detail': str(detail),
                      'subtitle': str(subtitle), 'icon': icon, 'previous': bool(previous), 'valueSize': value_size,
                      'targetId': str(target), 'unit': '', 'rect': {}})

    def finish(title, envelope, layout='hero'):
        result['title'] = title
        result['subtitle'] = ' · '.join(filter(None, [str(envelope.get('source', '')), state(envelope),
                                                     stamp(envelope.get('updatedAt')) if envelope.get('updatedAt') else '']))
        n = len(cards)
        if not n:
            card('missing', title, 'Dati non disponibili', 'Consulta Dati e aggiornamenti', value_size=34)
            n = 1
        if layout == 'grid' or n == 1:
            rects = ([(0, 0, 912, 504)] if n == 1 else [(0, 0, 448, 504), (464, 0, 448, 504)] if n == 2 else [(0, 0, 448, 504), (464, 0, 448, 244), (464, 260, 448, 244)] if n == 3 else [(i % 2 * 464, i // 2 * 260, 448, 244) for i in range(n)])
        else:
            rects = [(0, 0, 400, 504)]
            rest = n - 1
            rects += ([(416, 0, 496, 504)] if rest == 1 else
                      [(416, i * 260, 496, 244) for i in range(rest)] if rest == 2 else
                      [(416, 0, 496, 244), (416, 260, 240, 244), (672, 260, 240, 244)] if rest == 3 else
                      [(416 + i % 2 * 256, i // 2 * 260, 240, 244) for i in range(rest)])
        for c, (x, y, w, h) in zip(cards, rects):
            c['rect'] = {'x': x, 'y': y, 'width': w, 'height': h}
        result['detailRows'] = [{'id': c['id'], 'title': c['title'], 'value': c['value'],
                                 'detail': ' · '.join(filter(None, [c['subtitle'], c['detail'], 'Dato precedente' if c['previous'] else ''])),
                                 'targetId': c['targetId']} for c in cards]
        return result

    if view_id.startswith('sport-'):
        kind = view_id.removeprefix('sport-')
        envelope = payload.get('dashboardSport' if kind in ('sport', 'team') else 'dashboardRacing') or {}
        data = envelope.get('data') or {}
        previous = envelope.get('status') not in ('active', 'updating')
        result['detailTarget'] = kind
        if kind in ('sport', 'team'):
            favourite = data.get('favouriteTeamId') or data.get('favourite', '')
            rows = data.get('fixtures') or []
            team_view = kind == 'team'
            def fav(m):
                return bool(favourite and favourite in (m.get('homeTeamId'), m.get('awayTeamId')))
            if team_view:
                if not favourite:
                    card('choose-team', 'La mia squadra', 'Scegli una squadra', 'Apri per scegliere la preferita', 'football', value_size=36)
                    return finish('La mia squadra', envelope)
                rows = [m for m in rows if fav(m)]
            live = sorted([m for m in data.get('activeMatches') or rows
                           if m.get('status') in ('live', 'half_time') and m.get('fresh')
                           and number(m.get('kickoffUtc')) is not None
                           and -900 <= now - m['kickoffUtc'] <= 6 * 3600
                           and not previous and not data.get('fromCache') and (not team_view or fav(m))],
                          key=lambda m: (m.get('kickoffUtc') or 0, m.get('canonicalMatchId', '')))
            future = sorted([m for m in rows if number(m.get('kickoffUtc')) is not None and m['kickoffUtc'] > now and
                             m.get('status') not in ('cancelled', 'finished', 'postponed')],
                            key=lambda m: (m['kickoffUtc'], m.get('canonicalMatchId', '')))
            past = sorted([m for m in data.get('lastFinished') or rows if m.get('status') == 'finished' and (not team_view or fav(m))],
                          key=lambda m: (-(m.get('kickoffUtc') or 0), m.get('canonicalMatchId', '')))
            selected = (live or future or past or [None])[0]
            def match(m, title):
                scores = m.get('homeScore'), m.get('awayScore')
                scored = m.get('status') == 'finished' or m in live
                value = ' – '.join(display(s) for s in scores) if scored else stamp(m.get('kickoffUtc'), True)
                teams = (m.get('homeTeam') or '') + ' – ' + (m.get('awayTeam') or '')
                card(m.get('canonicalMatchId', title), title, value,
                     (('Diretta verificata' if m in live and m.get('isLive') else
                       'In corso secondo la fonte' if m in live else 'Risultato concluso' if scored else 'In programma') +
                      (' · ' + str(m['minute']) if m.get('minute') else '') +
                      ' · ' + stamp(m.get('kickoffUtc'))), 'football', previous, 68, teams, m.get('canonicalMatchId', ''))
            if selected:
                result['eventId'] = selected.get('canonicalMatchId', '')
                result['mode'] = 'live' if live else 'scheduled' if future else 'results'
                match(selected, ('In diretta' if selected.get('isLive') else 'In corso') if live else 'Prossima partita' if future else 'Ultimo risultato')
                for extra in live[1:3]:
                    match(extra, 'In diretta' if extra.get('isLive') else 'In corso')
                secondary = next((m for m in future + past if m.get('canonicalMatchId') != selected.get('canonicalMatchId')), None)
                if secondary and len(cards) < 3:
                    match(secondary, 'Prossima partita' if secondary in future else 'Ultimo risultato')
            standing = next((r for r in data.get('standings') or [] if favourite and r.get('teamId') == favourite), None) if team_view else next(iter(data.get('standings') or []), None)
            if standing:
                card('standing', standing.get('teamName') or standing.get('team') or ('La mia squadra' if team_view else 'Leader Serie A'), display(standing.get('position')) + 'ª',
                     display(standing.get('points')) + ' punti · ' + str(data.get('season', '')), 'trophy', previous)
            elif data.get('competitionName'):
                card('competition', 'Competizione', data['competitionName'], 'Stagione ' + str(data.get('season', '')), 'trophy', previous, 32)
            return finish('La mia squadra' if team_view else 'Serie A', envelope)
        sessions = [(e, s) for e in data.get('events') or [] for s in e.get('sessions') or [] if number(s.get('start')) is not None]
        timing = data.get('live') or {}
        timing_session = next(((e, s) for e, s in sessions if e.get('id') == timing.get('eventId') and s.get('id') == timing.get('sessionId')), None)
        live = timing_session if timing.get('active') and timing.get('rows') and not previous and not data.get('fromCache') else None
        completed_timing = timing_session if (timing_session and timing.get('rows') and
            timing.get('status') in ('Finished', 'Finalised', 'Ended') and
            0 <= now - timing_session[1]['start'] <= 86400 and not previous and not data.get('fromCache')) else None
        future = sorted([(e, s) for e, s in sessions if s['start'] > now and s.get('state') not in ('cancelled', 'finished')],
                        key=lambda pair: (pair[1]['start'], pair[1].get('id', '')))
        past = sorted([(e, s) for e, s in sessions if s.get('results')], key=lambda pair: (-pair[1]['start'], pair[1].get('id', '')))
        recent = sorted([(e, s) for e, s in sessions if 0 <= now - s['start'] <= 86400 and s.get('state') != 'cancelled'
                         and (s.get('results') or s.get('state') == 'finished' or (e, s) == completed_timing or now - s['start'] >= 7200)],
                        key=lambda pair: -pair[1]['start'])
        latest = recent[0] if recent else None
        selected = live or latest or (future + past or [None])[0]
        if selected:
            e, s = selected
            timing_rows = timing.get('rows') if selected == live or selected == completed_timing and not s.get('results') else []
            result['mode'] = 'timing' if timing_rows else 'results' if s.get('results') else 'scheduled' if selected in future else 'pending'
            result['eventId'] = e['id']
            result['sessionId'] = s['id']
            qualified = bool(live and timing.get('isLive') and data.get('liveVerified'))
            label = ('In diretta' if qualified else 'In corso') if live else 'Terminata' if timing_rows or s.get('results') else stamp(s['start'], True) if selected in future else 'In attesa'
            detail = ('Diretta verificata' if qualified else 'Timing aggiornato') if live else 'Sessione terminata · ultimi tempi' if timing_rows else 'Risultati disponibili' if s.get('results') else 'In programma' if selected in future else 'Orario trascorso · risultati in attesa'
            card(s['id'], s.get('name', 'Sessione'), label,
                 detail + ' · ' + stamp(s['start']), 'race-car' if kind == 'f1' else 'motorcycle', previous, 52, e.get('name', ''))
            leaders = timing_rows or s.get('results') or []
            if leaders:
                leader = leaders[0]
                card('session-leader', 'Leader sessione' if live else 'Primo classificato' if s.get('results') else 'Primo negli ultimi tempi', leader.get('name') or '—',
                     str(leader.get('value') or '—'), 'trophy', previous or bool(completed_timing and selected == completed_timing), 34, leader.get('team') or '')
            secondary = next((p for p in future + past if p[1]['id'] != s['id']), None)
            if secondary:
                ee, ss = secondary
                card(ss['id'], 'Prossima sessione' if secondary in future else 'Ultima sessione', ss.get('name', ''),
                     stamp(ss['start']), 'calendar', previous, 34, ee.get('name', ''))
            if not leaders:
                card('circuit', 'Circuito', e.get('circuit') or 'Non disponibile', 'Stagione ' + str(data.get('year', '')), 'flag', previous, 30)
        else:
            upcoming = sorted([e for e in data.get('events') or [] if number(e.get('start')) is not None and e['start'] > now], key=lambda e: (e['start'], e.get('id', '')))
            if upcoming:
                e = upcoming[0]
                result['eventId'] = e['id']
                card(e['id'], 'Prossimo GP', stamp(e['start'], True), 'Orari delle sessioni non disponibili · ' + stamp(e['start']),
                     'calendar', previous, 68, e.get('name', ''))
        standings = data.get('standings') or []
        if standings:
            r = standings[0]
            card('leader', 'Leader', r.get('name') or r.get('driverName') or 'Pilota',
                 display(r.get('points')) + ' punti', 'trophy', previous, 32)
        if result.get('mode') == 'timing':
            envelope = {**envelope, 'source': timing.get('source') or envelope.get('source'),
                        'updatedAt': timing.get('dataAt') or timing.get('fetchedAt') or envelope.get('updatedAt')}
        return finish('Formula 1' if kind == 'f1' else 'MotoGP', envelope)

    if view_id.startswith('casa-'):
        envelope = model.get('casa') or payload.get('casaState') or {}
        data = envelope.get('data') or {}
        rows = data.get('devices') or []
        result['detailTarget'] = 'casa.inventory'
        if view_id == 'casa-preferiti':
            for r in (data.get('favourites') or [])[:4]:
                card(r['id'], r['name'], r.get('primaryText') or '—',
                     r.get('availability', '') + ' · ' + r.get('secondaryText', ''),
                     {'casa.temperature': 'thermometer', 'casa.light': 'lightbulb', 'casa.plug': 'plug', 'casa.motion': 'motion'}.get(r.get('iconId'), 'connected-home'),
                     r.get('previous') or r.get('availabilityPrevious'), 48, target=r['id'])
            return finish('Preferiti', envelope, 'grid')
        if view_id == 'casa-ambiente':
            for r in environment_devices(data):
                for m in r.get('metrics') or []:
                    if m.get('code') not in ENVIRONMENT_CODES or m.get('quality') != 'reported':
                        continue
                    card(r['id'] + ':' + m['code'], r['name'], m.get('displayText') or display(m.get('value'), m.get('unit', '')),
                         m.get('label', '') + ' · ' + stamp(m.get('checkedAt')), 'humidity' if m.get('unit') == '%' else 'motion' if m.get('code') == 'pir' else 'thermometer',
                         r.get('previous') or m.get('previous') or m.get('stale'), 68 if not cards else 48, target=r['id'])
                    if len(cards) == 5:
                        break
                if len(cards) == 5:
                    break
            return finish('Ambiente', envelope)
        card('total', 'Catalogo Smart Life', str(len(rows)) if data.get('hasInventory') or rows else '—', 'Dispositivi riportati dal cloud', 'connected-home', envelope.get('status') != 'active', 86)
        current = [r for r in rows if not r.get('availabilityPrevious') and isinstance(r.get('online'), bool)]
        card('available', 'Disponibilità cloud', str(sum(r.get('online') is True for r in current)) if current else '—', 'Online secondo il cloud · non presenza LAN', 'network', not current, 58)
        card('favourites', 'Preferiti', str(len(data.get('favourites') or [])), 'Ordine scelto nelle impostazioni', 'star')
        return finish('Dispositivi', envelope)

    if view_id.startswith('rete-'):
        envelope = payload.get('networkState') or model.get('network') or {}
        data = envelope.get('data') or {}
        router = payload.get('dashboardRouter') or {}
        rows = router.get('rows') or []
        by_id = {r['id']: r for r in rows}
        result['detailTarget'] = 'network.router' if view_id != 'rete-dispositivi' else 'network.inventory'
        def metric(key, title, icon, size=52):
            r = by_id.get(key)
            card(key, title, r.get('value', '—') if r else '—', r.get('detail', '') if r else 'Non disponibile', icon, r.get('previous', True) if r else True, size)
            if key in ('wan:down', 'wan:up') and r:
                parts = r.get('value', '').rsplit(' ', 1)
                if len(parts) == 2 and parts[1] in ('bit/s', 'kbit/s', 'Mbit/s', 'Gbit/s'):
                    cards[-1]['value'], cards[-1]['unit'] = parts
        if view_id == 'rete-traffico':
            metric('wan:down', 'Download WAN', 'download', 68)
            metric('wan:up', 'Upload WAN', 'upload', 58)
            card('wan', 'Connessione WAN', (router.get('summary') or 'Non disponibile').replace(' · up', ' · Attiva').replace(' · down', ' · Non attiva'), 'Stato riportato dalla iliadbox', 'router', by_id.get('wan:down', {}).get('previous', True), 32)
            history = payload.get('dashboardHistory') or {}
            chart = history.get('chart') or {}
            if history.get('hasChart') and chart.get('series'):
                result['chart'] = chart
                card('history', 'Andamento WAN', '', chart.get('period', ''), 'history', chart.get('previous'), 30)
                cards.insert(1, cards.pop())
            return finish('Traffico', envelope)
        if view_id == 'rete-iliadbox':
            card('wan', 'Connessione WAN', (router.get('summary') or 'Non disponibile').replace(' · up', ' · Attiva').replace(' · down', ' · Non attiva'),
                 'Uptime · ' + by_id.get('uptime', {}).get('value', 'Non disponibile'), 'router', by_id.get('wan:down', {}).get('previous', True), 48)
            temperature = next((r for r in rows if '°C' in r.get('value', '') and r['id'] != 'metrics.refresh'), None)
            if temperature:
                card(temperature['id'], temperature['title'], temperature['value'], temperature['detail'], 'thermometer', temperature['previous'], 52)
            for key, title, icon in [('dashboardWifi', 'Wi-Fi', 'wifi'), ('dashboardPorts', 'Ethernet', 'ethernet')]:
                rr = [r for r in (payload.get(key) or {}).get('rows') or [] if r.get('targetId') and r['id'] != 'metrics.refresh']
                card(key, title, str(len(rr)) + (' radio' if key == 'dashboardWifi' else ' porte') if rr else '—',
                     'Catalogo riportato', icon, not rr or any(r.get('previous') for r in rr), 38)
            metric('firmware', 'Firmware', 'info', 30)
            return finish('iliadbox', envelope)
        records = data.get('devices') or []
        card('records', 'Inventario router', str(len(records)) if data.get('hasInventory') else '—', 'Record riportati · copertura parziale', 'network', envelope.get('status') != 'active', 86)
        current = [r for r in records if not r.get('previous')]
        card('reachable', 'Raggiungibili', str(sum(r.get('statusText') == 'Raggiungibile secondo box' for r in current)) if current else '—', 'Secondo box · non presenza assoluta', 'connected-home', not current, 58)
        for r in (data.get('favourites') or records)[:2]:
            card(r['id'], r['name'], r.get('primaryAddress') or '—', r.get('statusText', ''), 'network', r.get('previous'), 30, target=r['id'])
        return finish('Dispositivi', envelope)

    if view_id == 'oggi-giornata':
        envelope = model.get('weather') or {}
        data = envelope.get('data') or {}
        event = model.get('nextEvent') or {}
        day = next((d for d in data.get('forecast') or [] if d.get('date') == datetime.fromtimestamp(now, ZONE).date().isoformat()), None)
        previous = envelope.get('status') != 'active'
        if event.get('id') and event.get('title'):
            card('event', event['title'], stamp(event.get('startsAt', event.get('start')), True), event.get('whenText', '') or stamp(event.get('startsAt', event.get('start'))), 'calendar', False, 68)
        if day:
            card('today', 'Meteo del giorno', display(day.get('high'), '°C'), 'Min ' + display(day.get('low'), '°C') + ' · ' + day.get('description', ''), 'cloud', previous, 68)
            card('rain', 'Probabilità giornaliera', display(day.get('rainProbability'), '%'), 'Massimo giornaliero · modello meteo', 'rain', previous, 48)
        else:
            card('current', 'Meteo disponibile', display(data.get('temperature'), '°C'), data.get('description', '') + ' · ' + state(envelope), 'cloud', previous, 68)
        card('wind', 'Vento', display(data.get('windSpeed'), 'km/h'), str(data.get('windDirectionText', '')), 'wind', previous, 38)
        return finish('Giornata', envelope)
    return result
