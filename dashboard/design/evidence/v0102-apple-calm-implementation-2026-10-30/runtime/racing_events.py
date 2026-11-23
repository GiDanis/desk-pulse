"""Conservative session transitions; baseline/reconnect never replays old flags."""
import hashlib
import json


class RacingEvents:
    def __init__(self, kind):
        self.kind = kind
        self.baseline = None
        self.notices = {}

    def update(self, live, now, messages=None):
        self.notices = {k: v for k, v in self.notices.items() if v['expiresAt'] > now}
        identity = (live.get('eventId'), live.get('sessionId'))
        current = dict(identity=identity, active=live.get('active') is True, status=live.get('status', live.get('rawStatus')),
                       at=live.get('fetchedAt', 0), messages=set())
        healthy = all(identity) and 0 <= now - current['at'] <= 90
        messages = messages if isinstance(messages, dict) else {}
        current['messages'] = set(messages)
        previous = self.baseline
        if healthy and previous and previous['identity'] == identity and 0 <= now - previous['at'] <= 90:
            if current['active'] and not previous['active']:
                self.add(identity, 'start', 'Sessione iniziata', live.get('name', ''), now)
            if previous['active'] and not current['active'] and current['status'] in ('Finished', 'Finalised', 'Ends', 'F'):
                self.add(identity, 'end', 'Sessione conclusa', live.get('name', ''), now)
            if current['active']:
                for key in sorted(current['messages'] - previous['messages']):
                    value = messages[key]
                    if not isinstance(value, dict):
                        continue
                    flag = value.get('Flag')
                    # Qualify only explicit Track flags. Investigation is not a penalty.
                    if value.get('Scope') == 'Track' and flag == 'RED':
                        self.add(identity, 'flag:' + str(key), 'Bandiera rossa', str(value.get('Message') or 'Sessione interrotta'), now)
                    elif value.get('Category') == 'SafetyCar' and value.get('Status') == 'DEPLOYED':
                        self.add(identity, 'flag:' + str(key), 'Safety Car / VSC', str(value.get('Message') or 'Direzione gara'), now)
        self.baseline = current if healthy else None
        return list(self.notices.values())

    def add(self, identity, key, title, detail, now):
        digest = hashlib.sha256(json.dumps([identity, key]).encode()).hexdigest()[:32]
        event_id = f'{self.kind}:{digest}'
        self.notices.setdefault(event_id, {'version': 1, 'id': event_id, 'source': 'sport_' + self.kind,
            'sourceLabel': 'F1 Timing' if self.kind == 'f1' else 'MotoGP PulseLive', 'category': 'sport',
            'priority': 2, 'bannerSize': 'large', 'title': f'{self.kind.upper()} · {title}'[:100],
            'detail': detail[:240] or 'Sessione identificata dalla fonte', 'issuedAt': now, 'startsAt': now,
            'expiresAt': now + 21600, 'bannerUntil': now + 180, 'revision': key[:100], 'showOnHome': False})
