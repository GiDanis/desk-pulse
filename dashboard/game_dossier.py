"""Read-only per-driver facts, including previous profiles and frozen results."""
from datetime import datetime
from game_catalog import TRACKS, qualified, reference_ready

from game_modes import learning, lap_time, qualified_snapshot, label
from game_results import exercise
from game_profiles import METHODS as PRESETS, VARIANTS
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
    if profile.get('learningBackend')=='sb3-skill-1':
        return [row(prefix+'Metodo',METHODS.get(method,method),'Ricetta fissa · ambiente di apprendimento separato.'),
            row('Preparazione','Imitazione sequenziale','Il docente prepara la rete; durante guida e rinforzo non interviene.'),
            row('Rete','GRU '+str(profile['hidden'])+' · 90 sensori','Memoria causale per vettura; encoder congelato, lettura di sterzo e pedale addestrabile.'),
            row('Controllo','Sterzo · gas · freno','Comandi interamente neurali; nessuna corsia o velocità imposta.'),
            row('Frequenze','AI 10 Hz · fisica 60 Hz','Dimostrazione a velocità reale distinta dalla raccolta accelerata.'),
            row('Aggiornamento','Rete 0,000003 · critic 0,0003','PPO: rollout 128 decisioni, quattro epoche; SAC/TD3: replay fino a 32.768 transizioni.'),
            row('Avvio critic','1.024 decisioni','Guida iniziale conservata mentre si preparano le stime del valore.'),
            row('Riproducibilità','Seed '+str(profile['seed']),'Checkpoint durevole con optimizer, replay, RNG, fisica e memoria ricorrente.')]
    if method.startswith(('residual_','race_')):
        from game_residual import recipe
        if profile.get('controlMode')=='direct':
            from game_direct_trainer import recipe
            spec=recipe(profile)
            return [row(prefix+'Metodo',METHODS.get(method,method),'Guida neurale diretta; ricetta fissa.'),
                row('Preparazione','Scuola e traffico' if method=='residual_tactic' else 'Scuola guida fisica','La base è una rete appresa; il bot non corregge la guida.'),
                row('Controllo','Sterzo · gas · freno','Intera corsa degli attuatori, senza corsia o velocità imposte.'),
                row('Rete',('2 × 64 neuroni · selezione neurale' if profile['hidden']==128 else str(profile['hidden'])+' neuroni · 90 ingressi'),'90 ingressi: dinamica, gomme, strada e rivali. Specialità solo/traffico aggiornate separatamente.' if spec.get('expertLearning') else '90 ingressi: dinamica, gomme, strada e rivali. Esperti e selezione apprendono insieme.'),
                row('Obiettivo','Giri validi più rapidi','Progresso e tempo, con contatti, tagli e stallo penalizzati.'),
                row('Frequenze','AI 10 Hz · fisica 60 Hz','La grafica segue un clock distinto.'),
                row('Aggiornamento','LR '+str(profile['learningRate']),'PPO su esperienze recenti.' if method=='residual_ppo' else 'Critic LR '+str(profile['learningRate'])+'; rete LR '+str(profile['learningRate']*spec['actorRateScale'])+'. Avvio critic: '+str(spec['criticWarmup'])+' decisioni; replay fino a 32.768 transizioni.'),
                row('Riproducibilità','Seed '+str(profile['seed']),'Base versionata, RNG, rete, ottimizzatori e replay persistenti.')]
        spec=recipe(profile)
        result=[row(prefix+'Metodo',METHODS.get(method,method),'Base capace e ricetta fissa.'),
            row('Base','Maestro · '+spec['base'],'La capacità iniziale deriva dal controller; le correzioni apprese sono misurate separatamente.')]
        if method=='race_master':return result+[row('Apprendimento','Non previsto','Riferimento fisso, senza aggiornamenti neurali.')]
        return result+[row('Rete',str(profile['hidden'])+' neuroni · 90 ingressi','Correzione della linea e della velocità.'),
            row('Frequenze','AI 10 Hz · fisica 60 Hz','La grafica segue un clock distinto.'),
            row('Aggiornamento','LR '+str(profile['learningRate']),'Esperienze recenti PPO.' if method=='residual_ppo' else 'Replay fino a 32.768 transizioni; due critic e target.'),
            row('Orizzonte','40 s','Sconto calcolato sui passi decisionali da 0,1 secondi.'),
            row('Riproducibilità','Seed '+str(profile['seed']),'Rete, ottimizzatori, RNG e replay persistenti.')]
    output=[row(prefix+'Metodo',METHODS.get(method,method),'Accademia · esercizi progressivi di guida e traffico' if profile.get('version')==2 else 'Traffico attivo' if profile['traffic'] else 'Guida solitaria')]
    if profile.get('variant') in VARIANTS:
        v=VARIANTS[profile['variant']];output.append(row('Variante',v['name'],v['description']))
    output.append(row('Famiglia',PRESETS.get(method,('','','Sconosciuta',''))[2],'Regole del pilota fisse; nuovo metodo richiede un nuovo pilota.'))
    if method=='pure_pursuit':
        output.extend([row('Controllore','Riferimento geometrico','Controllore deterministico; versione indicata nel modello.'),
                       row('Apprendimento','Non previsto','Controllore a regole; i passi misurano esecuzione, non allenamento.'),
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
    if method in ('ppo','ppo_smooth','clone_ppo'):
        output.extend([row('Aggiornamento PPO',f"LR {profile['learningRate']} · γ {profile['gamma']}",'Passo di apprendimento e peso delle ricompense future.'),
                       row('Raccolta PPO',f"{profile['rollout']} passi · {profile['epochs']} epoche",'Esperienze raccolte e ripetizioni per aggiornamento.')])
        if method=='ppo_smooth':
            output.append(row('Esplorazione', 'PPO gaussiano con costo sterzo', 'Costo dello scarto fra comando e sterzo fisico; non misura la variabilità dei giri.'))
    else:output.append(row('Mutazione',profile['mutation'],'Intensità delle variazioni della rete.'))
    return output


def dossier(store,identity,driver=None):
    # One coherent driver read can serve the list, leaderboard and dossier.
    if driver is None:driver=store.driver(identity)
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
            changes=[f'{k}: {old.get(k,'—')} → {v}' for k,v in new.items() if old.get(k)!=v]
            description='; '.join(changes) or 'Profilo invariato'
        elif kind in ('memory','consolidation'):
            value='Base personale v'+str(p.get('revision',0)) if kind=='consolidation' else 'Conoscenza riutilizzata'
            description='Verifica sui contesti acquisiti' if kind=='consolidation' else 'Origine '+p.get('source','local')+' · esperienza locale conservata'
        elif kind=='reset_all':value='Intero pilota azzerato';description='Base e contesti archiviati; paradigma e identità conservati'
        elif kind=='curriculum_restart':value='Esercizi riavviati';description='Pesi, base personale e qualifiche conservati; nuovi contatori'
        elif kind=='reset':value='Apprendimento azzerato';description='Nome, impostazioni e risultati precedenti conservati'
        elif kind=='transfer':value='Pesi trasferiti';description='Inizializzazione da '+p['source']+'; qualifica da completare'
        elif kind=='racing_migration':value='Obiettivo sul tempo aggiornato';description='Guida e qualifiche conservate; nuova epoca di critic e replay'
        else:
            facts=exercise(p);value=facts['value'];description=facts['description']
            results.append({**facts,'created':event['created'],'id':'event:'+str(event['id']),'category':'training'})
        track_name=next((t['name'] for t in TRACKS if t['id']==event['track_id']),event['track_id'])
        history.append({**row({'profile':'Cambio parametri','academy':'Percorso Accademia','reset':'Reset','evaluation':'Valutazione','transfer':'Trasferimento','memory':'Memoria','consolidation':'Consolidamento','reset_all':'Reset completo','curriculum_restart':'Ripartenza esercizi','racing_migration':'Ricompense aggiornate'}[kind],value,date(event['created'])+' · '+track_name+' · '+description),'created':event['created'],'id':'event:'+str(event['id']), 'detailRows':profile_rows(p['previous'],'Prima · ')+profile_rows(p['next'],'Dopo · ') if kind in ('profile','academy') else []})
    state=driver['curriculum'] or {};champion=(state.get('raceChampion') or state.get('champion')) if qualified(driver,store.track_id) else None
    cert=qualified_snapshot(driver,store.track_id)
    status='Versione qualificata · '+lap_time(cert['bestLap']) if cert else 'Candidato da qualificare' if driver['candidate'] else 'Modello da qualificare' if driver['policy'] else 'Da allenare'
    total_seconds=store.total_seconds(identity)
    track_name=next(t['name'] for t in TRACKS if t['id']==store.track_id)
    summary=[row('Pilota',driver['name'],'Apri la rosa e scegli il pilota', 'driver'),
             row('Esecuzione attuale' if driver['profile']['algorithm'] in ('pure_pursuit','race_master') else 'Allenamento attuale',duration(driver['seconds']),f"{driver['steps']:,} passi di simulazione · {track_name}"),
             row('Storico complessivo',duration(total_seconds),f'{len(training)} sessioni registrate · {len(resets)} reset'),
             row('Modello da gara',status,'Versione '+cert['policy'][:12]+' · il candidato nuovo richiede una nuova qualifica' if cert else 'Serve un giro valido su questa pista'),
             row('Gare concluse',f'{races} · {wins} vittorie',f'{arrivals} arrivi · risultati di tutti i modelli'),
             row('Creato',date(driver['created']),'Identità persistente del pilota')]
    if state.get('migration'):
        summary.append(row('Ricetta aggiornata','Scuola guida · nuova epoca' if state['migration'].get('version')=='direct-driving-3' else 'Pesi conservati · premi coerenti',
            'Nuova base della scuola; critic e replay ripartono. Storia, contatori e modelli precedenti restano archiviati; la nuova policy richiede Qualifica.' if state['migration'].get('version')=='direct-driving-3' else 'Esperienze e contatori precedenti archiviati; nuovi contatori della ricetta. Pesi, tempi complessivi e qualifiche conservati.'))
    if state.get('lastEpisode',{}).get('manoeuvre'):
        summary.append(row('Ultimo esercizio',state['lastEpisode']['manoeuvre'],
            'Esito della raccolta; la verifica indipendente decide se promuovere il modello.'))
    if state.get('backend')=='sb3-skill-1':
        measured=state.get('learningMetrics') or state.get('stats') or {}
        summary.extend([row('Decisioni neurali',measured.get('decisions',0),'Sei passi fisici per decisione, salvo chiusura anticipata dell’episodio.'),
            row('Aggiornamenti',measured.get('updates',0),'Aggiornamenti reali del learner; non generazioni simulate.'),
            row('Episodi raccolti',measured.get('episodes',0),'Esperienze di allenamento distinte dal giro visibile e dalla Qualifica.')])
    if state.get('rewardVersion') in ('balanced-driving-1','balanced-driving-2','balanced-driving-3'):
        statistics=state.get('epochStats') or state.get('stats') or {};pedals=statistics.get('pedalCounts') or {};total=sum(pedals.values())
        summary.extend([row('Protocollo di guida','Evo progressivo' if state.get('rewardVersion')=='balanced-driving-2' else 'Bilanciato 1','Scenari confrontabili e verifiche indipendenti; nessun comando assistito.'),
                        row('Pressione sul tempo',f"{state.get('pacePressure',0):.0%}",'Aumenta dopo guida affidabile; un comando di frenata non vale da solo un premio.')])
        if total:
            summary.extend([row('Gas / rilascio / freno',f"{pedals.get('gas',0)/total:.0%} / {pedals.get('coast',0)/total:.0%} / {pedals.get('brake',0)/total:.0%}",'Episodi conclusi del protocollo attuale; non percentuali di forza o energia.'),
                            row('Aderenza in difficoltà',f"{statistics.get('understeerSeconds',0):.1f} s",'Richiesta anteriore elevata e traiettoria che peggiora, con persistenza verificata.')])
    plan=state.get('evoTraining') or {};epoch=state.get('epochStats') or {}
    if plan:
        from game_evo_plan import STAGES
        level=plan['level'];title=STAGES[level][1] if level<len(STAGES) else 'Esercizi completati'
        summary.extend([row('Esercizio progressivo',title,f"Fase {min(level+1,len(STAGES))}/{len(STAGES)} · {plan['stageGenerations']} aggiornamenti in questa fase"),
                        row('Aggiornamenti del percorso' if driver['profile']['algorithm'] in ('ppo','ppo_smooth','imitation','clone_ppo') else 'Generazioni del percorso',plan['generations'],'Ogni generazione confronta due scenari; dopo Partenza aggiunge il ripasso.'),
                        row('Passi del protocollo',max(0,driver['steps']-epoch.get('startedSteps',0)),'Contatori da questa ripartenza; lo storico precedente resta separato.')])
    for detail in reversed(list(epoch.get('byTask',{}).values())):
        attempts=detail['episodes']
        summary.append(row(detail['label'],f"{detail.get('success',0)}/{attempts} riusciti",
            f"{detail['track']} · {detail.get('no_progress',0)} stalli · {detail.get('contact',0)} incidenti · partenza {detail.get('initialSpeedKmh',0):.0f} km/h"))
    if driver.get('checkpoint'):
        # Residual metadata is already in the public curriculum. Loading its
        # full replay here would block the GUI after every save acknowledgement.
        checkpoint={'curriculum':state} if state.get('residualVersion') else store.load(driver['checkpoint'])
        inputs=checkpoint.get('inputContract')
        if inputs:
            summary.append(row('Ingressi della rete',inputs['version'],'Contesto costante '+str(round(inputs['constantCue'],4))+' · '+inputs['source']))
        branch=(checkpoint.get('curriculum') or {}).get('branchTransfer')
        if branch:
            summary.append(row('Memoria nel giro infinito','Base aggiornata adottata' if branch['adopted'] else 'Esperienza locale conservata',
                'Confronto a parità di scenari · 2 partenze e 2 prove da 120 s per versione.'))
        best=state.get('verifiedBest')
        if best:summary.append(row('Scelta Qualifica','Migliore verificato','Conservato separatamente dal candidato esplorativo. Nuovo hash: nuova Qualifica.'))
    if state.get('residualVersion'):
        stats=state.get('stats',{})
        proof=(state.get('champion') or {}).get('proof') or {}
        measured=proof.get('candidate',{}).get('median');base_time=state.get('baseMedian')
        if state.get('effectiveParameters',{}).get('evaluation')=='flying-pace-and-race-1' and proof.get('evaluationVersion')!='flying-pace-and-race-1':measured=None
        summary.append(row('Contributo verificato',f'{max(0,1-measured/base_time):.1%} più rapido' if measured and base_time else 'Ancora da misurare',
            f'Tre giri puliti · base {base_time:.2f} s · campione {measured:.2f} s' if measured and base_time else ('Base iniziale appresa dalla rete; il perfezionamento va misurato separatamente.' if driver['profile'].get('controlMode')=='direct' else 'La guida iniziale è del Maestro; nessun guadagno neurale presunto.')))
        summary.append(row('Costo delle verifiche',duration(state.get('evaluationSeconds',0)),str(state.get('evaluationSteps',0))+' passi congelati; esclusi dalle esperienze di allenamento.'))
        summary.append(row('Contatti / uscite',str(stats.get('contacts',0))+' / '+str(stats.get('trackLimits',0)),'Episodi di raccolta; qualifiche e gare sono separate.'))
        summary.extend([row('Stato apprendimento',state.get('status','Base pronta'),'Campione distinto dal candidato esplorativo.'),
            row('Passi decisionali',str((state.get('learningMetrics') or {}).get('decisions',state.get('learningMetrics',{}).get('physicalSteps',0)//6)),'AI a 10 Hz; passi fisici a 60 Hz.'),
            row('Esercizi completati',str(stats.get('success',0)),'Le finestre continue non sono tentativi falliti.'),
            row('Giri puliti / finestre',str(stats.get('cleanLaps',0))+' / '+str(stats.get('windows',0)),'Contatori nuovi: giri completati e finestre continue di raccolta separati.'),
            row('Sorpassi puliti',stats.get('passes',0),'Gli avversari hanno policy congelate.'),
            row('Aggiornamenti',state.get('updates',0),'Numero di aggiornamenti effettuati; il tempo delle verifiche è separato.')])
    memory=driver.get('memory') or {}
    if driver['profile'].get('controlMode')=='direct':
        attack=state.get('lastEpisode',{}).get('attack',{})
        if attack:
            summary.extend([row('Occasioni / attacchi',str(attack.get('opportunities',0))+' / '+str(attack.get('attacks',0)),
                'Ultimo esercizio: incontri praticabili e manovre realmente avviate, distinti dai passaggi confermati.'),
                row('Attesa affiancato',duration(attack.get('idleAlongsideSeconds',0)),
                'Tempo senza un vantaggio relativo significativo; non è un premio.'),
                row('Esercizio in raccolta',state.get('lastEpisode',{}).get('manoeuvre','Da avviare'),
                'La prova visibile è distinta dagli esercizi usati per aggiornare la rete.')])
        summary.insert(1,row('Base di guida','Rete preparata','Base neurale versionata; il Maestro non interviene durante la guida.'))
        
        for skill,counts in state.get('schoolStats',{}).items():
            summary.append(row('Scuola · '+skill,str(counts.get('valid',0))+' / '+str(counts.get('total',0)),'Esercizi riusciti / svolti; verifiche indipendenti prima della promozione.'))
        summary.append(row('Tentativi ripartiti',state.get('candidateRestarts',0),'Nuova ricerca dal campione dopo prove negative; esperienze e contatori conservati.'))
        if state.get('effectiveParameters',{}).get('evaluation') in ('flying-pace-and-race-1','flying-pace-and-attack-1'):
            solo=state.get('champion') or {};proof=solo.get('proof',{})
            lap_best=solo.get('flyingMedian') or (proof.get('candidate',{}).get('median') if proof.get('evaluationVersion')=='flying-pace-and-race-1' else None)
            ready=(state.get('raceChampion') or {}).get('flyingMedian')
            objective=state.get('trainingObjective','impara')
            stage='Sorpassi e difesa' if objective=='impara_sorpasso' else 'Passo continuo' if objective=='impara_infinito' else 'Ricerca del passo' if state.get('schoolGraduated') else 'Scuola guida'
            summary.extend([row('Fase',stage,
                'Dopo due riuscite per competenza, lezioni di ripasso e giri da partenze diverse.'),
                row('Migliore lanciato',lap_time(lap_best),'Mediana verificata su tre serie; il lancio è escluso.'),
                row('Versione pronta per gara',lap_time(ready),'Pesi distinti se il migliore sul giro deve ancora conservare il traffico. Qualifica e griglia usano la stessa policy che correrà.')])
            summary.append(row('Passi della nuova ricetta',max(0,driver['steps']-state.get('epochStart',{}).get('steps',0)),
                'Separati dal totale storico del pilota; i pesi appresi sono conservati.'))
    else:summary.insert(1,row('Base di guida',memory.get('label','Da costruire'),'Versione '+str(memory.get('revision',0))+' · riuso automatico fra piste dello stesso pilota'))
    for record in sorted(store.records(identity=identity),key=lambda r:(r['trackId'],r['category'],r['maxSpeed']['mode'])):
        config=record['configuration'];name=next((t['name'] for t in TRACKS if t['id']==record['trackId']),record['trackId'])
        lap=record.get('bestLap');speed=record['maxSpeed']
        results.append(row('Record · '+name,(f"Giro {lap['value']:.2f} s · " if lap else 'Giro — · ')+f"V max {speed['value']*3.6:.1f} km/h",
            config['physics']+' · '+speed['mode']+' · '+str(config['vehicle'].get('id','standard'))+' · '+str(config['condition'].get('id','asciutto'))+' · giri puliti; primo giro da fermo',identity='record:'+record['category']+':'+speed['mode'])|{'created':speed.get('created',''),'policy':speed['policy']})
    from game_catalog import configuration
    timing_pb=store.timing_reference(identity,configuration(store.track_id,driver['profile']['observation']))
    if timing_pb:
        summary.append(row('Personale lanciato',lap_time(timing_pb['time']),'Qualifica/Gara · '+('modello attuale' if timing_pb.get('policy')==driver['policy'] else 'modello precedente')))
        summary.append(row('Settori del personale',' / '.join(lap_time(s) for s in timing_pb['sectors']) if timing_pb.get('sectors') else 'Da misurare','Intertempi reali dello stesso giro; nessuna ricostruzione dei record storici.'))
    parameters=profile_rows(driver['profile'],'Attuale · ')
    from game_model_contract import model_rows
    parameters+=model_rows(store,driver)
    parameters.extend([row('Origine della base',memory.get('source') or 'Primo allenamento','Policy '+(memory.get('policy') or '—')[:12]),
        row('Abilità conservate',', '.join(memory.get('skills',[])) or 'Da verificare','Misurate sui contesti di ripasso; qualifiche di gara separate.')])
    if state.get('academyVersion'):
        from game_curriculum import PHASE_LABELS
        stats=state.get('stats',{})
        if getattr(store,'objective','impara')!='impara':
            summary.extend([row('Obiettivo',label(store.objective),'Checkpoint separato; base personale condivisa'),row('Serie pulita migliore',stats.get('bestSeries',0),'Giri consecutivi senza uscita o contatto negli episodi di apprendimento.'),row('Incontri e sorpassi',str(stats.get('passes',0))+'/'+str(stats.get('passAttempts',0)),'Sorpassi puliti su manovre iniziate; bot congelati.')])
        summary.extend([row('Rientri riusciti',str(stats.get('recoverySuccess',0))+'/'+str(stats.get('recoveries',0)),'Esercizi di recupero fuori pista; giro pulito valutato separatamente.')])
        eff=state.get('effectiveParameters')
        if eff:
            parameters.append(row('Parametri effettivi',eff['version'],eff['methodLabel']+' · '+eff['variantLabel']+' · seed '+str(eff['seed'])))
            network=eff.get('network',{})
            if 'responseInit' in network:
                parameters.extend([row('NEAT · risposta iniziale',network['responseInit'],'Tanh scalata 2,5 · nodi/connessioni variabili.'),
                    row('NEAT · sigma',str(network['weightSigma'])+' / '+str(network['biasSigma'])+' / '+str(network['mutationSigma']),'Pesi / bias / mutazione realmente configurati.')])
            if eff.get('ppo'):
                q=eff['ppo'];parameters.append(row('PPO · configurazione effettiva','γ '+str(round(q['gamma'],8))+' · λ '+str(q['gaeLambda']),
                    'LR '+str(q['learningRate'])+' · batch '+str(q['batchSize'])+' · clip '+str(q['clip'])+' · KL '+str(q['targetKL'])))
            if eff.get('recipe'):
                parameters.append(row('Ricetta ibrida','Imitazione' if eff['recipe']['phase']=='imitation' else 'Rinforzo',
                    'Passaggio solo dopo 18/20 partenze, 18/20 giri e 4/5 prove di cinque giri consecutivi.'))
        else:parameters.append(row('Parametri effettivi','Non ancora registrati','Il prossimo Start salva il descrittore; lo storico non viene stimato.'))
        causes=stats.get('terminationCauses',{})
        for cause,title in (('road_boundary','Ritiri · bordo esterno'),('vehicle_contact','Ritiri · collisione auto'),('geometry_guard','Ritiri · controllo geometria'),('retirement_unknown','Ritiri · causa non disponibile')):
            if causes.get(cause):summary.append(row(title,causes[cause],'Causa registrata dai nuovi episodi; gli eventi storici non sono riclassificati.'))
        known=sum(causes.get(k,0) for k in ('road_boundary','vehicle_contact','geometry_guard','retirement_unknown'))
        if stats.get('contact',0)>known:summary.append(row('Ritiri storici senza causa',stats['contact']-known,'Il vecchio contatore contact non distingueva bordo e collisione.'))
        diagnostic=state.get('controlDiagnostics') or {}
        if diagnostic.get('samples'):
            summary.append(row('Comandi · sterzo oltre 90%',f"{diagnostic['saturatedSteer']/diagnostic['samples']:.1%}",'Tutti i candidati dal nuovo protocollo; non è la sola guida del campione.'))
        cases=(state.get('evoTraining') or {}).get('selectedScenarios',[])
        if cases:
            summary.append(row('Candidato · scenari principali',str(sum(c['success'] for c in cases[:2]))+'/2','Stessa rete sui due casi; ripasso elencato separatamente.'))
            for i,c in enumerate(cases):summary.append(row(('Principale ' if i<2 else 'Ripasso ')+str(i+1),
                'Riuscito' if c['success'] else f"{100*c['progress']:.0f}% percorso",'Seed '+str(c['seed'])+' · '+c['cause']))
        metric=state.get('learningMetrics',{})
        if 'approxKL' in metric:
            parameters.extend([row('Distanza fra policy',f"{metric['approxKL']:.5f}",'KL approssimata; arresto se supera il limite.'),row('Quota clipping',f"{metric.get('clipFraction',0):.1%}",'Componente limitata dal vincolo PPO.'),row('Qualità del critic',f"{metric.get('explainedVariance',0):.3g}",'Varianza spiegata: valori negativi segnalano previsioni poco affidabili.')])
        summary.extend([row('Partenze riuscite',f"{stats.get('launchSuccess',0)}/{stats.get('launches',0)}",'Storico di tutti i protocolli; qualifica indipendente nei risultati.'),
                        row('Esercizi iniziali',f"{stats.get('warmupSuccess',0)}/{stats.get('warmups',0)}",'Partenza da 1, 3 e 8 metri prima dei 20 metri; nessun comando assistito.'),
                        row('Stalli',stats.get('no_progress',0),'Storico di tutti i protocolli; soste nel traffico distinte.'),
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
    if driver['profile']['algorithm'] not in ('pure_pursuit','race_master'):
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
                reset=([row('Maestro fisso','Non previsto','Riferimento senza apprendimento.','info.master')] if driver['profile']['algorithm']=='race_master' else [row('Azzera miglioramenti locali','5 per continuare','Ripristina la base iniziale del pilota; altri circuiti conservati.','reset'),row('Azzera tutti i miglioramenti','5 per continuare','Mantiene il Maestro; nuova Qualifica per ogni circuito.','reset.all')] if driver['profile']['algorithm'].startswith(('residual_','race_')) else [row('Resetta esperienza locale','5 per continuare','Riusa la base disponibile al prossimo Start; altri contesti conservati.','reset'),
                       row('Resetta intero pilota','5 per continuare','Riparte da pesi casuali; elimina base e qualifiche. Identità e storico conservati.','reset.all')]+([row('Riparti dagli esercizi','5 per continuare','Conserva i pesi attuali; riparte da Partenza con nuovi contatori.','reset.curriculum')] if driver['profile']['algorithm']=='evolution' and driver.get('checkpoint') and driver.get('curriculum') and getattr(store,'objective','impara')=='impara' else [])))
