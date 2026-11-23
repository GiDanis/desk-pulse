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
    causes={}
    descriptions=dict(incomplete_pass='Esercizio finito prima del sorpasso',race_rule='Manovra irregolare',
        track_limits='Fuori dai limiti',defense_lost='Posizione persa',stall='Nessun progresso',
        vehicle_contact='Contatto fra auto',road_boundary='Uscita dalla zona guidabile',time_limit='Tempo esaurito',
        collection_window='Finestra di raccolta conclusa')
    for item in rows+result.get('trafficResults',[]):
        cause=item.get('terminationCause')
        if item.get('reason') not in ('success','not_run') and cause:causes[cause]=causes.get(cause,0)+1
    for cause,count in sorted(causes.items()):
        details.append(dict(title=descriptions.get(cause,cause),value=str(count)+' prove',description='Esito osservato; distinto dal tempo sul giro.',id=''))
    for regression_phase in sorted({r['phase'] for r in proof.get('regressions',[])}):
        details.append(dict(title=LABELS.get(regression_phase,regression_phase),value='Campione conservato',description='Il candidato peggiora una prova già riuscita o la sicurezza.',id=''))
    if proof.get('evaluationVersion')=='flying-pace-and-race-1':
        from game_modes import lap_time
        value=f"{result['valid']} / 3 serie valide"
        if result.get('median') is not None:value+=' · giro '+lap_time(result['median'])
        for index,item in enumerate(rows):
            flying=item.get('lapTimes',[])[1:]
            details.append(dict(title='Serie '+str(index+1),value=lap_time(item.get('flyingMedian')),
                description='Lancio escluso · '+(' / '.join(lap_time(r['time']) for r in flying) if flying else 'Giri lanciati incompleti'),id=''))
        details.append(dict(title='Versione gara',value=proof.get('raceDecisionLabel','Da verificare'),
            description='Giro migliore e capacità nel traffico sono conservati separatamente.',id=''))
        return dict(title=name,value=value,description='Tre serie: lancio e due giri lanciati ciascuna. '+proof['decisionLabel']+'. '+proof.get('raceDecisionLabel',''),
            detailRows=details,goalMeters=distance,tested=tested,
            comparisonKey=(phase,distance,proof.get('scope'),proof.get('evaluationVersion'),proof.get('rewardVersion')))
    return dict(title=name,value=value,description=(proof.get('decisionLabel') or ('Verifica complessiva superata' if retained else 'Verifica complessiva non superata'))+f" · {result['total']-tested} non eseguiti",detailRows=details,goalMeters=distance,tested=tested,
                comparisonKey=(phase,distance,proof.get('scope'),proof.get('evaluationVersion'),proof.get('rewardVersion'),proof.get('stage'),proof.get('initialSpeedKmh')))
