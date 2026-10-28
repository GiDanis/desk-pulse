"""Small factual dossier projection of model architecture and policy roles."""


def model_rows(store,driver):
    def row(title,value,description):return dict(id='',title=title,value=str(value),description=description)
    if driver['profile']['algorithm']=='race_master':return []
    state=driver.get('curriculum') or {}
    digest=driver.get('latestCandidate') or driver.get('candidate') or driver.get('policy')
    if not digest:return [row('Modello personale','Da preparare','Nessun modello salvato per questo contesto.')]
    policy=store.load(digest)
    architecture=policy.get('architecture','dense');kind=policy.get('kind')
    memory=('GRU · '+str(policy['hidden'])+' unità' if architecture in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver')
        else str(policy.get('history',1))+' osservazioni' if architecture=='history'
        else 'Due reti · selettore neurale' if architecture=='neural-experts-2x64-v1' else 'Rete densa')
    result=[row('Memoria della guida',memory,
        'Stato personale per vettura, conservato fra giri e pausa.' if architecture in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver')
        else 'Storia causale a lunghezza fissa.' if architecture=='history'
        else 'Senza stato ricorrente; il replay di apprendimento è una memoria distinta.'),
        row('Candidato condiviso' if driver.get('latestCandidate') else 'Candidato salvato',(driver.get('latestCandidate') or driver.get('candidate') or 'Assente')[:12],
            'Rete in allenamento; può peggiorare e non sostituisce automaticamente la versione gara.')]
    from game_residual import key
    for field,title in (('champion','Riferimento solo'),('attackChampion','Migliore traffico'),('raceChampion','Versione gara conservata')):
        value=state.get(field) or {};model=value.get('policy')
        result.append(row(title,key(model)[:12] if model else 'Non registrato',
            'Versione conservata dalle verifiche del percorso; la Qualifica ufficiale resta separata.' if model
            else 'Nessuna versione distinta registrata per questo ruolo.'))
    origin=policy.get('origin') or {}
    if origin.get('backend')=='sb3-skill-1':
        result.extend([row('Apprendimento','Lettura diretta degli attuatori',
            'Percezione ricorrente congelata; tutti i coefficienti finali di sterzo e pedale restano addestrabili.'),
            row('Sensori',policy.get('features','—'),'Telemetria corrente, strada e rivali; nessuna azione del Maestro negli ingressi.')])
        if architecture=='gru-intent-deep':
            result.append(row('Controllo della vettura','Due strati da 256 unità','Manovra prevista dalla rete e comandi appresi; nessuna correzione del bot.'))
        if architecture=='gru-maneuver':
            result.append(row('Controllo della vettura','Sterzo e pedali distinti','Due reti da 128 unità per due strati; memoria neurale personale della manovra.'))
            if policy.get('maneuverHidden',2)!=2:result.append(row('Memoria della manovra',str(policy['maneuverHidden'])+' unità','Decisione ricorrente distinta dal controllo degli attuatori.'))
    if origin:
        seed=origin.get('seed',origin.get('trainingSeed'))
        result.append(row('Origine della preparazione',origin.get('kind','Registrata'),
            ('Seme '+str(seed)+' · ' if seed is not None else '')+'Preparazione iniziale distinta dai miglioramenti personali.'))
    return result
