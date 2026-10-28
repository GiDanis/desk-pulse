"""Read-only explanation of technical tests, distinct from timed qualifying laps."""
from game_academy import LABELS

def exercise(proof):
    result=proof['candidate'];phase=proof['phase'];rows=result.get('results',[])
    distance=next((r.get('goalMeters') for r in rows if r.get('goalMeters') is not None),None)
    name=LABELS.get(phase,phase)+(' · '+str(round(distance))+' m' if distance is not None else '')
    name=proof.get('stageLabel') or name
    tested=result.get('tested',sum(r.get('reason')!='not_run' for r in rows) if rows else result['total'])
    value=f"{result['valid']} su {tested} riusciti"
    if result.get('median') is not None:value+=f" · tipico {result['median']:.2f} s"
    retained=result.get('retained',False)
    details=[]
    for skill,r in result.get('skills',{}).items():
        done=r.get('tested',r['total']);unrun=r['total']-done
        details.append(dict(title=LABELS.get(skill,skill),value=f"{r['valid']} su {done} riusciti",description=f"{unrun} non eseguiti · {r['total']} previsti",id=''))
    return dict(title=name,value=value,description=('Verifica complessiva superata' if retained else 'Verifica complessiva non superata')+f" · {result['total']-tested} non eseguiti",detailRows=details,goalMeters=distance,tested=tested,
                comparisonKey=(phase,distance,proof.get('scope'),proof.get('evaluationVersion'),proof.get('rewardVersion'),proof.get('stage'),proof.get('initialSpeedKmh')))
