"""Bounded, gap-preserving normalized RRD series; no GUI or network I/O."""
import math
import statistics
from iliadbox import NetworkError

MAX_POINTS = 10000
PUBLIC_POINTS = 180


def number(value, *, negative=False):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e30 or (not negative and value < 0):
        return None
    return value


def history(raw, fields, now):
    if not isinstance(raw, dict) or not isinstance(raw.get('data'), list) or len(raw['data']) > MAX_POINTS:
        raise NetworkError('invalid', 'Storico Rete non valido o oltre limite.')
    start, end = number(raw.get('date_start')), number(raw.get('date_end'))
    if start is None or end is None or not 0 < start <= end <= now + 5:
        raise NetworkError('invalid', 'Finestra storica non valida.')
    by_time = {}
    for row in raw['data']:
        if not isinstance(row, dict):
            raise NetworkError('invalid', 'Campione storico non valido.')
        t = number(row.get('time'))
        if t is None or not start <= t <= end:
            raise NetworkError('invalid', 'Timestamp storico non valido.')
        by_time[t] = row
    ordered = sorted(by_time.items())
    resolution = statistics.median([b[0]-a[0] for a,b in zip(ordered,ordered[1:])]) if len(ordered)>1 else 0
    series = []
    for key, label, unit, scale in fields:
        source = []
        gaps = 0
        previous = None
        for t,row in ordered:
            value = number(row.get(key), negative=unit == 'dBm')
            if value is not None:
                value *= scale
            broken = previous is None or (resolution > 0 and t-previous > resolution*2.5)
            if value is None:
                gaps += 1
            source.append({'id':str(t),'time':t,'value':value,'breakBefore':broken})
            previous = t
        # Min/max buckets retain spikes. A missing point between retained points
        # becomes a break, even when the null itself is reduced away.
        indexes = set(range(len(source))) if len(source)<=PUBLIC_POINTS else {0,len(source)-1}
        if len(source)>PUBLIC_POINTS:
            for bucket in range(89):
                lo=int(bucket*len(source)/89);hi=int((bucket+1)*len(source)/89)
                valid=[i for i in range(lo,hi) if source[i]['value'] is not None]
                if valid:
                    indexes.update((min(valid,key=lambda i:source[i]['value']),max(valid,key=lambda i:source[i]['value'])))
                elif lo<hi:indexes.add(lo)
        points=[];last=-1
        for i in sorted(indexes):
            point=dict(source[i])
            point['breakBefore']=point['breakBefore'] or any(p['value'] is None or p['breakBefore'] for p in source[last+1:i])
            points.append(point);last=i
        valid=[p['value'] for p in source if p['value'] is not None]
        series.append({'id':key,'label':label,'unit':unit,'points':points,'minimum':min(valid) if valid else None,'maximum':max(valid) if valid else None,'gaps':gaps})
    return {'start':start,'end':end,'resolution':resolution,'series':series,'rawPoints':len(ordered)}


def counter_rate(before, after, dt, same_epoch=True):
    if not same_epoch or type(before) is not int or type(after) is not int or not 0 < dt <= 90 or before < 0 or after < before:
        return None
    # Subtraction is integer exact before conversion (including >2**53).
    return (after-before)*8/dt
