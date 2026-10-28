"""Read-only per-driver facts, including previous profiles and frozen results."""
from datetime import datetime
from game_catalog import TRACKS, qualified, reference_ready

from game_profiles import METHODS as PRESETS
METHODS={k:v[1] for k,v in PRESETS.items()}

def duration(value):
    value=max(0,int(value));h,rest=divmod(value,3600);m,s=divmod(rest,60)
    return f'{h} h {m:02} min' if h else f'{m} min {s:02} s'


def date(value):
    return datetime.fromisoformat(value).astimezone().strftime('%d/%m/%y %H:%M')


def row(title,value,description='',identity=''):
    return dict(id=identity,title=title,value=str(value),description=description)


def profile_rows(profile,prefix=''):
    method=profile['algorithm']
    output=[row(prefix+'Metodo',METHODS.get(method,method),'Traffico attivo' if profile['traffic'] else 'Guida solitaria')]
    output.append(row('Famiglia',PRESETS.get(method,('','','Sconosciuta',''))[2],'Regole del pilota fisse; nuovo metodo richiede un nuovo pilota.'))
    if method=='pure_pursuit':
        output.extend([row('Controllore','Riferimento geometrico','Controllore deterministico; versione indicata nel modello.'),
                       row('Stato','Sempre pronto','Nessuna rete neurale; linea di riferimento deterministica.'),
                       row('Partenza',f"Seed {profile['seed']}",'Nessun addestramento o aggiornamento dei pesi.')])
        return output
    if method=='imitation':
        output.extend([
            row('Rete ed Esperto',f"{profile['hidden']} neuroni · Pure Pursuit",'Rete neurale densa con apprendimento supervisionato su pilota esperto.'),
            row('Apprendimento online',f"LR {profile['learningRate']}",'Ottimizzatore Adam con discesa di gradiente in tempo reale.'),
            row('Budget del preset',f"Seed {profile['seed']} · {profile['episodeSeconds']} s",'Parametro di durata; il compito effettivo è registrato nella sessione.')])
        return output
    output.extend([
        row('Tentativi e rete',f"{profile['population']} · topologia variabile" if method=='neat' else f"{profile['population']} · {profile['hidden']} neuroni",'NEAT evolve nodi e connessioni.' if method=='neat' else 'Tentativi paralleli e neuroni dello strato interno.'),
        row('Budget del preset',f"Seed {profile['seed']} · {profile['episodeSeconds']} s",'Parametro di durata; il compito effettivo è registrato nella sessione.')])
    if method in ('ppo','ppo_smooth'):
        output.extend([row('Aggiornamento PPO',f"LR {profile['learningRate']} · γ {profile['gamma']}",'Passo di apprendimento e peso delle ricompense future.'),
                       row('Raccolta PPO',f"{profile['rollout']} passi · {profile['epochs']} epoche",'Esperienze raccolte e ripetizioni per aggiornamento.')])
        if method=='ppo_smooth':
            output.append(row('Esplorazione', 'PPO gaussiano con costo sterzo', 'Penalità moderata dei comandi bruschi; likelihood gaussiana esatta.'))
    else:output.append(row('Mutazione',profile['mutation'],'Intensità delle variazioni della rete.'))
    return output


def dossier(store,identity):
    driver=store.driver(identity)
    if not driver:return {}
    events=store.driver_events(identity,all_tracks=True)
    resets=[e for e in events if e['kind']=='reset']
    history=[];results=[];training=[];races=arrivals=wins=0
    for session in store.sessions(complete=False):
        p=session['payload'];mode=session['mode']
        if mode=='impara' and p.get('driver')==identity:
            training.append(session)
            stats=p.get('training');profile=p.get('profile') or {}
            summary=(duration(stats['seconds'])+' · '+str(stats['steps'])+' passi') if stats else 'Durata di sessione non registrata'
            history.append({**row('Allenamento · '+METHODS.get(profile.get('algorithm'),'Metodo precedente'),summary,
                                 date(session['created'])+' · '+p.get('configuration',{}).get('track',{}).get('name','Ovale')+' · '+{'interrupted':'interrotta','paused':'in pausa','running':'in corso','complete':'conclusa','failed':'errore'}[session['status']]),'created':session['created'], 'profile':profile,'id':'session:'+session['id'],'detailRows':[row('Durata e passi',summary,'Pause escluse; i dati assenti delle sessioni precedenti non vengono stimati.')]+profile_rows(profile) if profile else []})
        people=p.get('participants',[])
        person=next((x for x in people if x['id']==identity),None)
        if mode not in ('gara','prova','campione') or not person:continue
        if session['status']!='complete':
            value='Interrotta' if session['status'] in ('interrupted','paused') else 'Errore' if session['status']=='failed' else 'In corso'
        elif mode=='prova':
            tests=[r for r in p.get('results',[]) if r['driver']==identity]
            times=[r['time'] for r in tests if r.get('time') is not None]
            value=f'{len(times)}/{len(tests)} arrivi'+(f' · migliore {min(times):.2f} s' if times else '')
        else:
            result=next((r for r in p.get('results',[]) if r['id']==identity),{})
            value=f"P{result.get('position','—')} · {result.get('status','—')} · {result.get('lap',0)} giri"
        if mode=='gara' and session['status']=='complete':
            races+=1
            if result.get('status')=='arrivato':
                arrivals+=1;wins+=int(result.get('position')==1)
        previous=person.get('policy')!=driver['policy']
        description=date(session['created'])+' · '+p.get('configuration',{}).get('track',{}).get('name','Ovale')+' · '+METHODS.get(person['profile']['algorithm'],'—')+(' · modello precedente' if previous else ' · modello attuale')
        if mode!='prova' and session['status']=='complete' and result.get('finishTime') is not None:
            description+=f" · tempo {result['finishTime']:.2f} s"
        results.append({**row({'gara':'Gara','prova':'Prova standard','campione':'Campione'}[mode],value,description),'created':session['created'],'policy':person.get('policy')})
    for event in events:
        p=event['payload'];kind=event['kind']
        if kind=='profile':
            old=p['previous'];new=p['next'];value=METHODS[new['algorithm']]+(' · nuovo percorso' if p['newPath'] else ' · parametri aggiornati')
            changes=[f'{k}: {old[k]} → {v}' for k,v in new.items() if old[k]!=v]
            description='; '.join(changes) or 'Profilo invariato'
        elif kind=='reset':value='Apprendimento azzerato';description='Nome, impostazioni e risultati precedenti conservati'
        elif kind=='transfer':value='Pesi trasferiti';description='Inizializzazione da '+p['source']+'; qualifica da completare'
        else:
            proof=p['candidate'];value=f"{proof['valid']}/{proof['total']} prove valide"+(f" · {proof['median']:.2f} s" if proof['median'] is not None else '')
            description='Campione promosso' if p['promoted'] else 'Valutazione del candidato'
            results.append({**row('Valutazione',value,date(event['created'])+' · '+description),'created':event['created'],'id':'event:'+str(event['id']), 'detailRows':profile_rows(p['previous'],'Prima · ')+profile_rows(p['next'],'Dopo · ') if kind=='profile' else []})
        track_name=next((t['name'] for t in TRACKS if t['id']==event['track_id']),event['track_id'])
        history.append({**row({'profile':'Cambio parametri','reset':'Reset','evaluation':'Valutazione','transfer':'Trasferimento'}[kind],value,date(event['created'])+' · '+track_name+' · '+description),'created':event['created'],'id':'event:'+str(event['id']), 'detailRows':profile_rows(p['previous'],'Prima · ')+profile_rows(p['next'],'Dopo · ') if kind=='profile' else []})
    state=driver['curriculum'] or {};champion=state.get('champion') if qualified(driver,store.track_id) else None
    status='Riferimento pronto' if reference_ready(driver,store.track_id) else 'Campione verificato' if champion else 'Modello precedente' if driver['policy'] else 'Candidato in allenamento' if driver['candidate'] else 'Da allenare'
    total_seconds=store.total_seconds(identity)
    track_name=next(t['name'] for t in TRACKS if t['id']==store.track_id)
    summary=[row('Pilota',driver['name'],'Apri la rosa e scegli il pilota', 'driver'),
             row('Allenamento attuale',duration(driver['seconds']),f"{driver['steps']:,} passi · {track_name} · percorso attivo"),
             row('Storico complessivo',duration(total_seconds),f'{len(training)} sessioni registrate · {len(resets)} reset'),
             row('Modello da gara',status,METHODS[(driver['policy_profile'] or driver['profile'])['algorithm']]+(' · da qualificare' if not champion else '')),
             row('Gare concluse',f'{races} · {wins} vittorie',f'{arrivals} arrivi · risultati di tutti i modelli'),
             row('Creato',date(driver['created']),'Identità persistente del pilota')]
    parameters=profile_rows(driver['profile'],'Attuale · ')
    if driver['policy_profile']:
        parameters+=profile_rows(driver['policy_profile'],'Salvato · ')
        if driver['policy_profile']['algorithm']=='pure_pursuit':
            parameters.append(row('Versione del riferimento','Pure Pursuit 1' if reference_ready(driver,store.track_id) else 'Reattivo precedente','Modello precedente conservato; nessuna qualifica neurale attribuita.'))
    if driver['profile']['algorithm']!='pure_pursuit':
        from game_protocol import training_task
        task=training_task(store.track_id,state.get('phase','control'),driver['profile']['episodeSeconds'])
        parameters.append(row('Compito attuale',f"{task['laps']} giri · {task['limitSeconds']:.0f} s",'Controllo: un giro; Passo: tre giri. Budget proporzionato alla pista.'))
    for entry in history:
        if not entry['id'].startswith('session:'):continue
        session=next(s for s in training if 'session:'+s['id']==entry['id'])
        task=session['payload'].get('task')
        if task:entry['detailRows'].append(row('Compito della sessione',f"{task['laps']} giri · {task['limitSeconds']:.0f} s",task['version']))
    return dict(id=identity,name=driver['name'],summary=summary,parameters=parameters,
                history=sorted(history,key=lambda x:x['created'],reverse=True),
                results=sorted(results,key=lambda x:x['created'],reverse=True),
                reset=[row('Resetta apprendimento','5 per continuare','Azzera rete, candidato, checkpoint, passi e tempo attuali. Mantiene nome, parametri e storico.','reset')])
