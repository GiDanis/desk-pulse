"""Read-only per-driver facts, including previous profiles and frozen results."""
from datetime import datetime
from game_catalog import TRACKS, qualified, reference_ready

from game_modes import learning, lap_time, qualified_snapshot, label
from game_results import exercise
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
    output=[row(prefix+'Metodo',METHODS.get(method,method),'Accademia · esercizi progressivi di guida e traffico' if profile.get('version')==2 else 'Traffico attivo' if profile['traffic'] else 'Guida solitaria')]
    output.append(row('Famiglia',PRESETS.get(method,('','','Sconosciuta',''))[2],'Regole del pilota fisse; nuovo metodo richiede un nuovo pilota.'))
    if method=='pure_pursuit':
        output.extend([row('Controllore','Riferimento geometrico','Controllore deterministico; versione indicata nel modello.'),
                       row('Stato','Da qualificare','Nessuna rete neurale; linea di riferimento deterministica.'),
                       row('Partenza',f"Seed {profile['seed']}",'Nessun addestramento o aggiornamento dei pesi.')])
        return output
    if method=='imitation':
        output.extend([
            row('Rete ed Esperto',f"{profile['hidden']} neuroni · "+('Guida e traffico' if profile.get('version')==2 else 'Pure Pursuit'),'Rete neurale densa con apprendimento supervisionato su pilota esperto.'),
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
    resets=[e for e in events if e['kind'] in ('reset','reset_all')]
    history=[];results=[];training=[];races=arrivals=wins=0
    for session in store.sessions(complete=False):
        p=session['payload'];mode=session['mode']
        if learning(mode) and p.get('driver')==identity:
            training.append(session)
            stats=p.get('training');profile=p.get('profile') or {}
            summary=(duration(stats['seconds'])+' · '+str(stats['steps'])+' passi') if stats else 'Durata di sessione non registrata'
            history.append({**row(label(mode)+' · '+METHODS.get(profile.get('algorithm'),'Metodo precedente'),summary,
                                 date(session['created'])+' · '+p.get('configuration',{}).get('track',{}).get('name','Ovale')+' · '+{'interrupted':'interrotta','paused':'in pausa','running':'in corso','complete':'conclusa','failed':'errore'}[session['status']]),'created':session['created'], 'profile':profile,'id':'session:'+session['id'],'detailRows':[row('Durata e passi',summary,'Pause escluse; i dati assenti delle sessioni precedenti non vengono stimati.')]+profile_rows(profile) if profile else []})
        people=p.get('participants',[])
        person=next((x for x in people if x['id']==identity),None)
        if mode not in ('gara','prova','campione','qualifica') or not person:continue
        if mode=='qualifica':
            result=next((r for r in p.get('results',[]) if r['id']==identity),{})
            laps=[r for r in result.get('lapTimes',[]) if not r['standingStart']]
            valid=[r['time'] for r in laps if r['clean']]
            value=lap_time(min(valid) if valid else None)+f' · {len(valid)}/{len(laps)} giri validi'
        elif session['status']!='complete':
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
        results.append({**row(label(mode),value,description),'created':session['created'],'policy':person.get('policy'),'id':'session:'+session['id'],'category':'qualification' if mode=='qualifica' else 'race' if mode=='gara' else 'previous','detailRows':([row('Giro '+str(r['lap']-1),lap_time(r['time']),'Valido' if r['clean'] else 'Invalidato: fuori pista o contatto') for r in laps]+[row('Versione',person['policy'][:12],'Policy congelata · lancio escluso'),row('Velocità massima',f"{result.get('maxSpeed',0)*3.6:.1f} km/h",'Velocità al suolo misurata')] if mode=='qualifica' else [])})
    for event in events:
        p=event['payload'];kind=event['kind']
        if kind in ('profile','academy'):
            old=p['previous'];new=p['next'];value=METHODS[new['algorithm']]+(' · nuovo percorso' if p['newPath'] else ' · parametri aggiornati')
            changes=[f'{k}: {old[k]} → {v}' for k,v in new.items() if old[k]!=v]
            description='; '.join(changes) or 'Profilo invariato'
        elif kind in ('memory','consolidation'):
            value='Base personale v'+str(p.get('revision',0)) if kind=='consolidation' else 'Conoscenza riutilizzata'
            description='Verifica sui contesti acquisiti' if kind=='consolidation' else 'Origine '+p.get('source','local')+' · esperienza locale conservata'
        elif kind=='reset_all':value='Intero pilota azzerato';description='Base e contesti archiviati; paradigma e identità conservati'
        elif kind=='reset':value='Apprendimento azzerato';description='Nome, impostazioni e risultati precedenti conservati'
        elif kind=='transfer':value='Pesi trasferiti';description='Inizializzazione da '+p['source']+'; qualifica da completare'
        else:
            facts=exercise(p);value=facts['value'];description=facts['description']
            results.append({**facts,'created':event['created'],'id':'event:'+str(event['id']),'category':'training'})
        track_name=next((t['name'] for t in TRACKS if t['id']==event['track_id']),event['track_id'])
        history.append({**row({'profile':'Cambio parametri','academy':'Percorso Accademia','reset':'Reset','evaluation':'Valutazione','transfer':'Trasferimento','memory':'Memoria','consolidation':'Consolidamento','reset_all':'Reset completo'}[kind],value,date(event['created'])+' · '+track_name+' · '+description),'created':event['created'],'id':'event:'+str(event['id']), 'detailRows':profile_rows(p['previous'],'Prima · ')+profile_rows(p['next'],'Dopo · ') if kind in ('profile','academy') else []})
    state=driver['curriculum'] or {};champion=state.get('champion') if qualified(driver,store.track_id) else None
    cert=qualified_snapshot(driver,store.track_id)
    status='Versione qualificata · '+lap_time(cert['bestLap']) if cert else 'Candidato da qualificare' if driver['candidate'] else 'Modello da qualificare' if driver['policy'] else 'Da allenare'
    total_seconds=store.total_seconds(identity)
    track_name=next(t['name'] for t in TRACKS if t['id']==store.track_id)
    summary=[row('Pilota',driver['name'],'Apri la rosa e scegli il pilota', 'driver'),
             row('Allenamento attuale',duration(driver['seconds']),f"{driver['steps']:,} passi · {track_name} · percorso attivo"),
             row('Storico complessivo',duration(total_seconds),f'{len(training)} sessioni registrate · {len(resets)} reset'),
             row('Modello da gara',status,'Versione '+cert['policy'][:12]+' · il candidato nuovo richiede una nuova qualifica' if cert else 'Serve un giro valido su questa pista'),
             row('Gare concluse',f'{races} · {wins} vittorie',f'{arrivals} arrivi · risultati di tutti i modelli'),
             row('Creato',date(driver['created']),'Identità persistente del pilota')]
    memory=driver.get('memory') or {}
    summary.insert(1,row('Base di guida',memory.get('label','Da costruire'),'Versione '+str(memory.get('revision',0))+' · riuso automatico fra piste dello stesso pilota'))
    for record in sorted(store.records(identity=identity),key=lambda r:(r['trackId'],r['category'],r['maxSpeed']['mode'])):
        config=record['configuration'];name=next((t['name'] for t in TRACKS if t['id']==record['trackId']),record['trackId'])
        lap=record.get('bestLap');speed=record['maxSpeed']
        results.append(row('Record · '+name,(f"Giro {lap['value']:.2f} s · " if lap else 'Giro — · ')+f"V max {speed['value']*3.6:.1f} km/h",
            config['physics']+' · '+speed['mode']+' · '+str(config['vehicle'].get('id','standard'))+' · '+str(config['condition'].get('id','asciutto'))+' · giri puliti; primo giro da fermo',identity='record:'+record['category']+':'+speed['mode'])|{'created':speed.get('created',''),'policy':speed['policy']})
    parameters=profile_rows(driver['profile'],'Attuale · ')
    parameters.extend([row('Origine della base',memory.get('source') or 'Primo allenamento','Policy '+(memory.get('policy') or '—')[:12]),
        row('Abilità conservate',', '.join(memory.get('skills',[])) or 'Da verificare','Misurate sui contesti di ripasso; qualifiche di gara separate.')])
    if state.get('academyVersion'):
        from game_curriculum import PHASE_LABELS
        stats=state.get('stats',{})
        if getattr(store,'objective','impara')!='impara':
            summary.extend([row('Obiettivo',label(store.objective),'Checkpoint separato; base personale condivisa'),row('Serie pulita migliore',stats.get('bestSeries',0),'Giri consecutivi senza uscita o contatto negli episodi di apprendimento.'),row('Incontri e sorpassi',str(stats.get('passes',0))+'/'+str(stats.get('passAttempts',0)),'Sorpassi puliti su manovre iniziate; bot congelati.')])
        summary.extend([row('Rientri riusciti',str(stats.get('recoverySuccess',0))+'/'+str(stats.get('recoveries',0)),'Esercizi di recupero fuori pista; giro pulito valutato separatamente.')])
        metric=state.get('learningMetrics',{})
        if 'approxKL' in metric:
            parameters.extend([row('Distanza fra policy',f"{metric['approxKL']:.5f}",'KL approssimata; arresto se supera il limite.'),row('Quota clipping',f"{metric.get('clipFraction',0):.1%}",'Componente limitata dal vincolo PPO.'),row('Qualità del critic',f"{metric.get('explainedVariance',0):.3g}",'Varianza spiegata: valori negativi segnalano previsioni poco affidabili.')])
        summary.extend([row('Partenze riuscite',f"{stats.get('launchSuccess',0)}/{stats.get('launches',0)}",'Tentativi di Partenza registrati; qualifica indipendente nei risultati.'),
                        row('Esercizi iniziali',f"{stats.get('warmupSuccess',0)}/{stats.get('warmups',0)}",'Partenza da 1, 3 e 8 metri prima dei 20 metri; nessun comando assistito.'),
                        row('Stalli',stats.get('no_progress',0),'Episodi senza avanzamento; frenate e soste nel traffico distinte.'),
                        row('Sorpassi validi',stats.get('passes',0),'Passaggi con margine, senza contatto o uscita di pista.'),
                        row('Percorso',PHASE_LABELS[state['phase']],'Un pilota in allenamento; gli avversari restano congelati.')])
        import statistics
        for key,title in (('firstMeterTimes','Primo metro'),('tenMeterTimes','Primi 10 metri')):
            values=stats.get(key,[])
            summary.append(row(title,f'{statistics.median(values):.2f} s' if values else 'Da misurare',
                               'Mediana degli ultimi 256 episodi che hanno raggiunto la distanza.'))
        summary.append(row('Tempo fermo',f"{stats.get('stationarySeconds',0):.1f} s",'Secondi simulati sotto 0,5 m/s; comprende le soste nel traffico.'))
        certificates=state.get('qualifications',{})
        parameters.extend([row('Sensori','68 ingressi','Bordi fino a 150 m, ingombro, aderenza, tre rivali e tempo del compito.'),
                           row('Fisica','Vettura standard · f2-1','Trasferimento del carico, forze pneumatici combinate, contatti graduati e fuori pista recuperabile.'),
                           row('Ritiro','Sagoma trasparente','L’auto ritirata resta visibile e non partecipa più a sensori e contatti.'),
                           row('Avversari','Congelati','Riferimenti geometrici o modelli Gara 4 salvati all’avvio della sessione.')])
        for key,title in (('solo','Solitario'),('race2','Gara 2'),('race4','Gara 4')):
            cert=certificates.get(key,{})
            valid=bool(driver['policy'] and cert.get('candidateHash')==driver['policy'] and cert.get('valid'))
            summary.append(row('Verifica tecnica '+title,f"{cert['valid']}/{cert['total']}" if valid else 'Da verificare',
                               'Prova del modello attuale, su scenari indipendenti.' if valid else 'Nessuna qualifica attribuita dai soli risultati di training.'))
    if driver['policy_profile']:
        parameters+=profile_rows(driver['policy_profile'],'Salvato · ')
        if driver['policy_profile']['algorithm']=='pure_pursuit':
            parameters.append(row('Versione del riferimento',('Guida e traffico 2' if driver['policy_profile'].get('version')==2 else 'Pure Pursuit 1') if reference_ready(driver,store.track_id) else 'Reattivo precedente','Controllore deterministico; nessuna qualifica neurale attribuita.'))
    if driver['profile']['algorithm']!='pure_pursuit':
        from game_protocol import training_task
        from game_driving_memory import task as academy_task
        task=state.get('task') or academy_task(store.track_id,state.get('phase','launch')) if driver['profile'].get('version')==2 else training_task(store.track_id,state.get('phase','control'),driver['profile']['episodeSeconds'])
        parameters.append(row('Compito attuale',f"{task['distance']:.0f} m · {task['limitSeconds']:.0f} s" if task.get('distance') is not None else f"Continuo · finestre {task['limitSeconds']:.0f} s" if task.get('continuous') else f"{task['laps']} giri · {task['limitSeconds']:.0f} s",task.get('label','Controllo: un giro; Passo: tre giri. Budget proporzionato alla pista.')))
    for entry in history:
        if not entry['id'].startswith('session:'):continue
        session=next(s for s in training if 'session:'+s['id']==entry['id'])
        task=session['payload'].get('task')
        if task:entry['detailRows'].append(row('Compito della sessione',f"{task['distance']:.0f} m · {task['limitSeconds']:.0f} s" if task.get('distance') is not None else f"Continuo · finestre {task['limitSeconds']:.0f} s" if task.get('continuous') else f"{task['laps']} giri · {task['limitSeconds']:.0f} s",task.get('label',task['version'])))
    results += [dict(r,category='training') for r in history if r['id'].startswith('session:')]
    for c in driver.get('timedQualifications',[]):
        results.append(dict(row('Qualifica · '+c['track'],lap_time(c['bestLap']),'Versione '+c['policy'][:12]+' · '+str(len(c['laps']))+' giri validi',identity='cert:'+c['policy']),created=c['updated'],category='qualification',detailRows=[row('Giro '+str(l['lap']-1),lap_time(l['time']),date(l['created'])+' · '+l['session'][:8]) for l in c['laps']]))
    results.sort(key=lambda r:r['created'],reverse=True)
    categories=[dict(row('Allenamento','Apri','Esercizi, giri e verifiche tecniche.','result:trainingResults'),created=''),dict(row('Qualifica','Apri','Giri ufficiali, versioni e contesti.','result:qualificationResults'),created=''),dict(row('Gare','Apri','Arrivi, ritiri, tempi e record.','result:raceResults'),created='')]
    return dict(trainingResults=[r for r in results if r.get('category')=='training'],qualificationResults=[r for r in results if r.get('category')=='qualification' or r['title']=='Qualifica'],raceResults=[r for r in results if r['title']=='Gara'],id=identity,name=driver['name'],summary=summary,parameters=parameters,
                history=sorted(history,key=lambda x:x['created'],reverse=True),
                results=categories,allResults=sorted(results,key=lambda r:r['created'],reverse=True),
                reset=[row('Resetta esperienza locale','5 per continuare','Azzera questo contesto; base personale e altri percorsi conservati.','reset'),
                       row('Resetta intero pilota','5 per continuare','Azzera base e tutti i contesti; identità, paradigma e storico conservati.','reset.all')])
