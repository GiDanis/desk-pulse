"""Measured track records, separated by physical configuration and run type."""
import math
from game_catalog import configuration_hash
from game_driving_memory import physical_context


def category(config):
    context=physical_context(config)
    result={k:v for k,v in context.items() if k not in ('observation','contextHash')}
    result.update({k:config[k] for k in ('decisionHz','substeps','roadRules') if k in config})
    return configuration_hash(result),result


def measured_records(payload,session,mode):
    if mode not in ('gara','prova','campione') or not payload.get('configuration'):return []
    config=payload['configuration'];key,context=category(config)
    people={p['id']:p for p in payload.get('participants',[])};output=[]
    for result in payload.get('results',[]):
        identity=result.get('id',result.get('driver'));person=people.get(identity)
        if not person or result.get('telemetryVersion')!=1:continue
        def finite(value):return type(value) in (int,float) and math.isfinite(value)
        speed=result.get('maxSpeed')
        if not finite(speed) or speed<0:continue
        laps=[lap for lap in result.get('lapTimes',[]) if lap.get('clean') is True and finite(lap.get('time')) and lap['time']>0]
        best=min(laps,key=lambda x:x['time']) if laps else None
        origin={'session':session,'mode':mode,'policy':person['policy'],'driver':identity,'name':person['name'],'created':payload.get('recordedAt','')}
        output.append({'category':key,'driver':identity,'trackId':config['track']['id'],
            'configuration':context,'bestLap':dict(value=best['time'],lap=best['lap'],standingStart=best['standingStart'],**origin) if best else None,
            'maxSpeed':dict(value=speed,**origin)})
    return output


def merge(previous,current):
    output={**current}
    for field,better in (('bestLap',lambda a,b:a<b),('maxSpeed',lambda a,b:a>b)):
        old=previous.get(field);new=current.get(field)
        if old and (not new or not better(new['value'],old['value'])):output[field]=old
    return output


def summary(records):
    laps=[r['bestLap'] for r in records if r.get('bestLap')];speeds=[r['maxSpeed'] for r in records if r.get('maxSpeed')]
    return {'bestLap':min(laps,key=lambda r:r['value']) if laps else None,
            'maxSpeed':max(speeds,key=lambda r:r['value']) if speeds else None}
