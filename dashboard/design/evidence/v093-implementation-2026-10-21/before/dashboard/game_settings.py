"""Task settings with drafts, explicit selectors and stable focus identities.

No geometry, learning runtime or storage write is needed to browse/edit values.
The service applies the selected configuration only after a deliberate action.
"""
from copy import deepcopy
import math
from game_catalog import TRACKS, race_eligible

from game_profiles import METHODS as PRESETS, VARIANTS
METHODS={k:v[1] for k,v in PRESETS.items()}
from game_modes import MODES as CONTRACTS, learning, qualified_snapshot, GRID, lap_time, MAX_RACE_DRIVERS
MODES={k:v[0] for k,v in CONTRACTS.items()}
OPTIONS={'population':[8,16,32,64,128,256],'hidden':[8,16,32,64],
         'mutation':[.05,.15,.3],'seed':[1,2,3,4,5,11,21,42],
         'episodeSeconds':[30,60,120,180],'learningRate':[.0001,.0003,.001],
         'rollout':[64,128,256,1024,2048],'epochs':[1,2,4,8],'gamma':[.95,.99,.995,.999],
         'algorithm':list(PRESETS),'traffic':[False,True],
         'mode':list(MODES),'laps':[3,5,10],'grid':list(GRID),'view':['pilot','attempts'],'bots':[1,2,3]}
LABELS={'population':('Popolazione','Reti candidate per ogni generazione.'),
        'hidden':('Neuroni nascosti','Dimensione dello strato interno della rete.'),
        'mutation':('Mutazione','Intensità delle modifiche ai pesi della rete.'),
        'seed':('Seme allenamento','Partenza casuale riproducibile; non genera la pista.'),
        'episodeSeconds':('Limite tentativo','Tempo simulato massimo per ogni tentativo.'),
        'learningRate':('Passo di apprendimento','Ampiezza degli aggiornamenti della rete.'),
        'rollout':('Raccolta per aggiornamento','Passi raccolti per copia prima di aggiornare la rete.'),
        'epochs':('Epoche','Passaggi di apprendimento sugli stessi dati.'),
        'gamma':('Peso dei risultati futuri','Quanto pesano le ricompense più lontane.'),
        'algorithm':('Metodo','Come il pilota modifica la propria rete.'),
        'traffic':('Scenario','Accademia progressiva: partenza, passo, sorpassi e gara.'),
        'mode':('Modalità','Allenamento, gara o prova dei modelli salvati.'),
        'grid':('Griglia','Ordine dal miglior giro della versione qualificata.'),
        'view':('Vista allenamento','Pilota: dimostrazione indipendente; Tentativi: copie reali con ritmo dichiarato.'),
        'bots':('Bot in pista','Riferimenti congelati; solo il pilota scelto apprende.'),
        'laps':('Giri','Distanza della gara; le reti restano congelate.')}


def row(identity,title,value='Apri',description='',enabled=True):
    return dict(id=identity,title=title,value=str(value),detail=str(value),description=description,enabled=enabled)


class GameSettings:
    def __init__(self,service):
        self.service=service;self.section='session';self.view='root';self.group='network'
        self.focus={};self.selected='mode';self.draft=None;self.profiles={};self.base=None
        self.edit=None;self.picker=None;self.confirm=None;self.message=''
        self.picker_return=False;self.confirm_return='';self.group_return='advanced'

    def current(self):
        s=self.service
        return dict(mode=s._mode,track=s._track,driver=s._selected,laps=s._race_laps,participants=s._participants[:],
                    grid=s._grid_order,view=s._training_view,bots=s._bots,profile=deepcopy(next((d['profile'] for d in s._drivers if d['id']==s._selected),{})))

    def open(self,force=False):
        if force or self.draft is None or (not self.dirty and self.current()!=self.base):
            self.base=self.current();self.draft=deepcopy(self.base);self.profiles={};self.message=''
        self.view='root';self.edit=self.picker=self.confirm=None
        self.selected=self.focus.get('root:'+self.section,'mode' if self.section=='session' else 'algorithm' if self.section=='training' else 'create')
        self.normalize()

    @property
    def dirty(self):return self.draft is not None and self.draft!=self.base

    def value(self,key):
        if self.edit and self.edit['key']==key:return self.edit['value']
        return self.draft[key] if key in ('mode','laps','grid','view','bots') else self.draft['profile'].get(key)

    def text(self,key,value):
        if key=='algorithm':return METHODS.get(value,value)
        if key=='mode':return MODES.get(value,value)
        if key=='grid':return GRID[value]
        if key=='view':return 'Pilota' if value=='pilot' else 'Tentativi'
        if key=='traffic':return 'Avversario fisso' if value else 'Solo pista'
        if key=='episodeSeconds':return str(value)+' s'
        if key=='rollout':return f'{value:,}'.replace(',','.')+' passi/copia'
        return str(value).replace('.',',')

    def selected_driver(self):
        return next((p for p in self.service._drivers if p['id']==self.draft['driver']),{}) if self.draft['track']==self.service._track else {}

    def active_task(self):
        from game_driving_memory import task
        driver=self.selected_driver();state=driver.get('curriculum') or {}
        phase=state.get('phase','launch') if self.draft['profile'].get('version')==2 else 'launch'
        return task(self.draft['track'],phase)

    def setting(self,key,enabled=True):
        title,description=LABELS[key]
        if key=='mode':description=CONTRACTS.get(self.value(key),('', ''))[1]
        if key=='episodeSeconds':
            spec=self.active_task()
            return row(key,'Limite esercizio',f"{spec['limitSeconds']:.0f} s",spec['label']+' · durata calcolata dal protocollo e dal circuito.',False)
        if key=='gamma':
            gamma=self.value(key);seconds=-1/60/math.log(gamma)
            return row(key,'Orizzonte ricompense',f'{seconds:.1f} s',('Profilo storico; dopo Start l’Accademia usa 40 s.' if self.draft['profile'].get('version')==1 else 'Peso dei risultati futuri, espresso in tempo simulato.'),False)
        algo = self.draft['profile'].get('algorithm')
        if key=='population' and algo in ('ppo','ppo_smooth','clone_ppo'):
            title,description='Copie ambiente','Tentativi paralleli; in pista una guida dimostrativa.'
        elif key=='population' and algo=='pure_pursuit':
            title,description='Vetture','Guida geometrica di riferimento.'
        elif key=='population' and algo=='imitation':
            title,description='Copie ambiente','Tentativi paralleli di imitazione della linea di riferimento.'
        if key=='mutation' and algo=='neat':
            effective=(self.selected_driver().get('curriculum') or {}).get('effectiveParameters',{}).get('network',{})
            return row(key,title,'σ '+str(effective['mutationSigma']) if effective else 'Dopo Start',
                ('Pesi '+str(effective['weightSigma'])+' · bias '+str(effective['biasSigma'])+' · risposta '+str(effective['responseInit'])) if effective else 'Il prossimo Start registra i parametri effettivi del preset.',False)
        if key=='mutation' and algo=='evolution':description='Nuovo protocollo: σ normalizzato per strato; variazioni piccole e rare più ampie.'
        if key=='rollout':description=f"{self.value('rollout')/60:.2f} s per copia · {self.value('rollout')*self.draft['profile']['population']:,} transizioni totali.".replace(',', '.')
        if key=='algorithm':
            description=PRESETS[algo][3]
            if algo=='evolution':description=f"Rete densa a {self.draft['profile']['hidden']} neuroni · selezione e mutazione."
            elif algo=='neat':description=PRESETS[algo][3]
            elif algo=='ppo':description='Policy gradient Actor-Critic · Campionamento stocastico.'
            elif algo=='pure_pursuit':description='Riferimento geometrico; richiede un giro di Qualifica per gareggiare.'
            elif algo=='imitation':description=PRESETS[algo][3]
            elif algo=='ppo_smooth':description=PRESETS[algo][3]
        return row(key,title,self.text(key,self.value(key)),description,enabled)

    def rows(self):
        if not self.draft:return []
        d=self.draft;s=self.service
        if s._storage_error:return [row('readonly','Archivio non disponibile','Errore',s._message,False)]
        if self.confirm:
            title={'discard':'Scarta modifiche','start':'Conferma e avvia','pilot':'Conferma e apri','reset':'Conferma e apri','transfer':'Trasferisci pesi','apply':'Applica modifiche'}[self.confirm]
            return [row('confirm.cancel','Annulla','Mantieni','Torna alla bozza senza applicarla.'),row('confirm.apply',title,'Conferma',self.confirm_description())]
        if self.picker:
            if self.picker in ('preset','variantPreset'):
                import importlib.util
                if self.picker=='variantPreset':
                    return [row('preset:'+k,v['name'],'Crea',v['description'],v['algorithm']!='neat' or importlib.util.find_spec('neat') is not None) for k,v in VARIANTS.items()]
                return [row('preset:'+k,v[1],'Crea',v[3],k!='neat' or importlib.util.find_spec('neat') is not None) for k,v in PRESETS.items()]+[row('preset.variants','Varianti e stili','Apri','Configurazioni sperimentali e specializzazioni; profilo fisso.')]

            if self.picker=='source':
                choices=[]
                for t in TRACKS:
                    if t['id']==d['track']:continue
                    source=s._store.driver(d['driver'],t['id']) or {}
                    choices.append(row('source:'+t['id'],t['name'],'Importa' if source.get('policy') else 'Non disponibile','Modello del solo pilota selezionato; compatibilità verificata prima di applicarlo.',bool(source.get('policy'))))
                return choices
            if self.picker=='driver':return [row('pick:'+p['id'],p['name'],'Selezionato' if p['id']==d['driver'] else 'Scegli',METHODS.get(p['profile']['algorithm'],'Identità persistente') + ' · ' + ('Modello salvato' if p['policy'] or p.get('candidate') else 'Da allenare')) for p in s._store.drivers(d['track'])]
            residual=d['profile'].get('algorithm','').startswith(('race_','residual_'))
            return [row('pick:'+t['id'],t['name'],'Da verificare' if residual and t['id']!='oval-1' else 'Selezionato' if t['id']==d['track'] else 'Scegli',
                'Nuova base da qualificare su questo circuito.' if residual and t['id']!='oval-1' else t.get('description','Asfalto asciutto · vettura standard · percorso proprio.'),
                not residual or t['id']=='oval-1') for t in TRACKS]
        if self.view=='participants':
            def eligible(p):return race_eligible(p,d['track'],max(2,len(d['participants'])+int(p['id'] not in d['participants']))) if d['mode']=='gara' else bool(p['policy'])
            return [row('participant:'+p['id'],p['name'],'Schierato' if p['id'] in d['participants'] else 'Non schierato' if eligible(p) else 'Da qualificare' if p['policy'] or p.get('candidate') else 'Da allenare',
                        'Versione qualificata · '+lap_time((qualified_snapshot(p,d['track']) or {}).get('bestLap')) if eligible(p) else 'Completa almeno un giro valido in Qualifica.' if p['policy'] else 'Serve un modello salvato su questo circuito.',eligible(p)) for p in s._store.drivers(d['track'])]
        if self.view=='advanced':
            return [row('group:network','Rete','Consulta','Tentativi paralleli e dimensione della rete.'),
                    row('group:learning','Apprendimento','Consulta','Parametri specifici del metodo scelto.'),
                    row('group:reproducibility','Memoria e riproducibilità','Consulta','Base personale, seme e provenienza del percorso.')]
        if self.view=='group' and d['profile']['algorithm'].startswith(('residual_','race_')):
            from game_dossier import profile_rows
            return [row('info:residual:'+str(i),r['title'],r['value'],r['description'],False) for i,r in enumerate(profile_rows(d['profile']))]
        if self.view=='group':
            method=d['profile']['algorithm']
            if method=='pure_pursuit':return [row('info:reference','Riferimento geometrico','Una vettura','Controllo deterministico della pista; nessuna rete o apprendimento.',False)]
            keys={'network':['population']+([] if method in ('neat','pure_pursuit') else ['hidden']),
                  'learning':['learningRate','rollout','epochs','gamma'] if method in ('ppo','ppo_smooth','clone_ppo') else (['learningRate'] if method=='imitation' else ([] if method=='pure_pursuit' else ['mutation'])),
                  'reproducibility':['seed']}[self.group]
            rows=[self.setting(k,enabled=False) for k in keys]
            if self.group=='network' and method!='pure_pursuit':
                from game_catalog import observation_size
                inputs=observation_size(d['profile']['observation'])
                rows.append(row('info:sensors','Sensori',str(inputs)+' ingressi','Schema '+d['profile']['observation']+'; migrazione a 68 dopo Start.' if inputs!=68 else 'Geometria, traffico, dinamica e contesto temporale.',False))
            if self.group=='network' and method=='neat':
                m=(self.selected_driver().get('curriculum') or {}).get('learningMetrics',{})
                rows.append(row('info:genome','Topologia attuale',str(m.get('nodes','—'))+' nodi · '+str(m.get('connections','—'))+' connessioni','Valori del genoma valutato; specie '+str(m.get('species','—'))+'.',False))
            if self.group=='learning' and method in ('ppo','ppo_smooth','clone_ppo'):
                from game_driving_memory import PPO_DEFAULTS
                tuning=(self.selected_driver().get('curriculum') or {}).get('tuning') or PPO_DEFAULTS
                rows.extend([row('info:ppo','Minibatch e GAE',str(tuning['batchSize'])+' · λ '+str(tuning['gaeLambda']),
                    'Clip '+str(tuning['clip'])+' · KL '+str(tuning['targetKL'])+' · valori del percorso; descrittore completo nel dossier.',False)])
                if method=='clone_ppo':
                    recipe=((self.selected_driver().get('curriculum') or {}).get('effectiveParameters') or {}).get('recipe',{})
                    rows.append(row('info:recipe','Imitazione → Rinforzo','PPO' if recipe.get('phase')=='reinforcement' else 'Maestro',
                        'PPO dopo 18/20 partenze, 18/20 giri e 4/5 prove di cinque giri consecutivi.',False))
                m=(self.selected_driver().get('curriculum') or {}).get('learningMetrics',{})
                if 'approxKL' in m:rows.append(row('info:kl','Ultimo aggiornamento',f"KL {m['approxKL']:.4f}",'Arresto anticipato' if m.get('earlyStop') else f"Quota clip {m.get('clipFraction',0):.1%}; qualità del critic nel dossier.",False))
            if self.group=='learning' and method=='neat':
                rows.append(row('info:topology','Mutazione strutturale','Nodi / connessioni','Aggiunta nodo 0,15; connessione 0,30. Specie e topologia evolvono.',False))
            if self.group=='learning' and method=='imitation':
                rows.append(row('info:dataset','Esempi del maestro','8.192 · batch 128','Quattro riserve: frenata, curva, rettilineo e rientro. Campionamento bilanciato.',False))
            if self.group=='learning':
                state=self.selected_driver().get('curriculum') or {};version=state.get('rewardVersion','')
                progressive=version in ('balanced-driving-2','balanced-driving-3','regular-driving-1','attacker-driving-1');balanced=version=='balanced-driving-1'
                rows.append(row('info:balance','Obiettivo di guida','Progressivo' if progressive else 'Al prossimo Start' if method=='evolution' else 'Bilanciato 1' if balanced else 'Al prossimo Start',
                    'Evo: difficoltà graduale, stessi scenari per tutti e ripasso nella selezione.' if method=='evolution' else 'Giri puliti, ingresso curva e tempo progressivo. Pesi personali conservati.',False))
                execution=state.get('execution') or {}
                groups=execution.get('collectors',0)
                rows.append(row('info:execution','Motore CPU',str(groups)+' gruppi' if groups else 'Un processo',
                    'Sensori nativi e ambienti persistenti quando il confronto ne dimostra il beneficio.',False))
            if self.group=='reproducibility':
                memory=self.selected_driver().get('memory') or {}
                rows.extend([row('info:memory','Base di guida',memory.get('label','Da costruire'),'Riusata fra piste; Infinito confronta la base aggiornata con il percorso locale.',False),
                    row('info:origin','Provenienza',memory.get('source') or 'Primo allenamento','Versione '+str(memory.get('revision',0))+' · base personale del solo pilota scelto.',False)])
            if self.group=='learning' and method=='ppo_smooth':
                rows.append(row('info:noise','Regolarità','Scarto comando/sterzo','Costo dello scarto rispetto allo sterzo fisico; non misura la varianza dei giri.',False))
            elif self.group=='network' and method=='imitation':
                rows.append(row('info:expert','Guida esperta','Guida e traffico','Esempi del maestro negli stati visitati; la rete guida da sola.',False))
            return rows
        if self.section=='session':
            driver=next((p for p in s._drivers if p['id']==d['driver']),{})
            output=[self.setting('mode'),row('driver','Pilota',driver.get('name','—'),METHODS.get(driver.get('profile',{}).get('algorithm'),'Apri la rosa')+' · Identità persistente.') if d['mode']!='gara' else row('participants','Schieramento',str(len(d['participants']))+' piloti','Versioni con un giro valido di Qualifica su questa pista.'),
                    row('track','Circuito',next(t['name'] for t in TRACKS if t['id']==d['track']),'Asfalto asciutto · vettura standard.')]
            if d['mode']=='gara':
                output.extend([self.setting('laps'),self.setting('grid')])
                from game_modes import grid_order
                people=[s._store.driver(i,d['track']) for i in d['participants']]
                try:
                    for i,(person,cert) in enumerate(grid_order(people,d['track'],d['grid'])):
                        output.append(row('info:grid:'+str(i),'P'+str(i+1)+' · '+person['name'],lap_time(cert['bestLap']),'Versione '+cert['policy'][:10]+' · rete congelata.',False))
                except ValueError:pass
            elif learning(d['mode']):
                if d['profile']['algorithm'] in ('evolution','neat'):output.append(self.setting('view'))
                if d['mode']=='impara_sorpasso':output.append(self.setting('bots'))
            elif d['mode']=='qualifica':
                verified=(driver.get('curriculum') or {}).get('verifiedBest')
                output.append(row('info:quali','Giri cronometrati','3 + lancio','Migliore verificato congelato.' if verified else 'Candidato salvato congelato; primo giro da fermo escluso.',False))
            can_start=not (learning(d['mode']) and d['profile']['algorithm'] in ('pure_pursuit','race_master'))
            output.append(row('start','Avvia '+MODES.get(d['mode'],d['mode']),'Start',
                CONTRACTS.get(d['mode'],('', ''))[1] if can_start else 'Il riferimento non apprende: scegli Qualifica o Gara.',can_start))
            return output
        if self.section=='training' and d['profile']['algorithm'].startswith(('residual_','race_')):
            return [self.setting('algorithm',False),row('info:base','Base pronta','Rete preparata' if d['profile'].get('controlMode')=='direct' else 'Maestro','Rete agli attuatori; il Maestro è servito per imparare la base.' if d['profile'].get('controlMode')=='direct' else 'La guida di base è già disponibile; la rete affina linea e velocità.',False),
                row('info:method','Allenamento','Non previsto' if d['profile']['algorithm']=='race_master' else 'Passo e tattica','Maestro resta fisso.' if d['profile']['algorithm']=='race_master' else 'Un pilota apprende; il migliore verificato resta disponibile.',False),
                row('advanced','Profilo tecnico','Consulta','Rete, frequenze, memoria e parametri effettivi.')]
        if self.section=='management' and d['profile']['algorithm'].startswith(('residual_','race_')):
            return [row('pilot','Scheda pilota','Apri','Metodo, sessioni e risultati del pilota.'),
                row('reset','Azzera miglioramenti','Non previsto' if d['profile']['algorithm']=='race_master' else 'Apri','Il Maestro è fisso.' if d['profile']['algorithm']=='race_master' else 'Ripristina la base iniziale, azzerando il perfezionamento locale.',d['profile']['algorithm']!='race_master'),
                row('info:roster','Rosa','Cinque piloti','Maestro, Crono, Memoria, Linea e Tattico; ricette fisse.',False)]
        if self.section=='training':
            if not learning(d['mode']):return [row('readonly','Allenamento','Non previsto','Questa modalità usa reti congelate.',False)]
            algo=d['profile'].get('algorithm')
            method_row=self.setting('algorithm',enabled=False)
            if algo=='pure_pursuit':
                return [method_row,
                        row('traffic','Scenario','Guida e traffico','Controllore geometrico; non richiede apprendimento.',False),
                        row('advanced','Profilo tecnico','Consulta','Rete, apprendimento e memoria personale.'),
                        row('apply','Applica modifiche','Conferma','Controllore matematico · Nessun apprendimento necessario.',self.dirty)]
            return [method_row,
                    row('traffic','Accademia','Progressiva','Partenza → Passo → Traffico. Dal prossimo Start; il percorso precedente resta salvato.' if d['profile'].get('version')==1 else 'Partenza → Passo → Traffico. Avanza dopo prove valide.',False),
                    self.setting('episodeSeconds',False),
                    row('advanced','Profilo tecnico','Consulta','Rete, apprendimento e memoria personale.'),
                    row('apply','Applica modifiche','Conferma','Un pilota si allena; gli avversari restano congelati.',self.dirty)]
        return [row('create','Nuovo pilota','Crea','Identità con allenamento e storico indipendenti.'),
                row('pilot','Scheda pilota','Apri','Durata, metodo, sessioni e risultati.'),
                row('reset','Gestisci apprendimento','Apri','Reset del percorso attivo con storico conservato.'),
                row('memory','Memoria del pilota','Consulta','Base riusata automaticamente; esperienza specifica per pista.'),
                row('transfer','Importazione avanzata','Apri','Recupera un modello storico compatibile su un percorso vuoto.'),
                row('apply','Applica modifiche','Conferma','Salva insieme i valori della bozza.',self.dirty)]

    def confirm_description(self):
        if self.confirm=='discard':return 'La sessione salvata e tutti i piloti restano invariati.'
        if self.confirm=='transfer':return 'Inizializza il percorso vuoto; il modello originale resta disponibile.'
        return 'Conferma la sessione; eventuali percorsi precedenti restano disponibili.'

    def normalize(self):
        rows=self.rows()
        if rows and not any(r['id']==self.selected for r in rows):self.selected=rows[0]['id']

    def snapshot(self):
        if not self.draft:return dict(rows=[],selectedIndex=0,section=self.section,view='root',dirty=False,title='Impostazioni',subtitle='')
        self.normalize();rows=self.rows();index=next((i for i,r in enumerate(rows) if r['id']==self.selected),0)
        title='Conferma' if self.confirm else 'Variante del nuovo pilota' if self.picker=='variantPreset' else 'Metodo del nuovo pilota' if self.picker=='preset' else 'Scegli pilota' if self.picker=='driver' else 'Scegli circuito' if self.picker else 'Schieramento' if self.view=='participants' else {'network':'Rete','learning':'Apprendimento','reproducibility':'Memoria e riproducibilità'}[self.group] if self.view=='group' else 'Profilo tecnico' if self.view=='advanced' else {'session':'Prepara la sessione','training':'Allenamento','management':'Gestione piloti'}[self.section]
        subtitle=self.message or ('Informazioni del paradigma · Non modificabili' if self.view in ('advanced','group') else ('Modifica valore' if self.edit else 'Modifiche in bozza' if self.dirty else 'Profilo del pilota preconfigurato' if self.section=='training' else 'Configurazione salvata'))
        return dict(rows=rows,selectedIndex=index,selectedId=self.selected,section=self.section,view=self.view,title=title,
                    subtitle=subtitle,dirty=self.dirty,editing=bool(self.edit),tabs=not bool(self.picker or self.confirm or self.view!='root'),
                    confirmation=bool(self.confirm),draft=deepcopy(self.draft))

    def incompatibility(self):
        if not learning(self.draft['mode']):return False
        previous=self.service.profileFor(self.draft['driver'],self.draft['track'])
        return any(previous.get(k)!=self.draft['profile'].get(k) for k in ('algorithm','variant','recipeVersion','hidden','population','traffic','seed','observation'))

    def request_apply(self,action):
        if self.dirty and (self.incompatibility() or action in ('pilot','reset','transfer')):
            self.confirm_return=self.selected
            self.confirm=action;self.selected='confirm.cancel';self.message='Apre un percorso distinto; i precedenti restano conservati.'
            return True
        return self.apply(action)

    def apply(self,action):
        s=self.service
        if action=='transfer':
            result=s.transferFrom(self.transfer_source)
        else:
            result=s.applySetup(self.draft) if self.dirty else True
        if not result:self.message=s._message;return False
        self.base=self.current();self.draft=deepcopy(self.base);self.profiles={};self.confirm=None;self.message=s._message
        if self.selected.startswith('confirm.'):self.selected=self.confirm_return or 'apply'
        if action=='start':
            if s.start():s.settingsRouteRequested.emit('running');return True
            self.message=s._message;return False
        if action in ('pilot','reset'):s.settingsRouteRequested.emit('pilot.picker' if self.picker_return else action);self.picker_return=False
        return True

    def action(self,identity,direction=1):
        if self.draft is None:self.open()
        if identity.startswith('section:'):
            if self.edit or self.confirm or self.picker or self.view!='root':return False
            self.focus['root:'+self.section]=self.selected;self.section=identity[8:];self.selected=self.focus.get('root:'+self.section,'');self.normalize();return True
        self.selected=identity;self.normalize()
        current=next((r for r in self.rows() if r['id']==self.selected),None)
        if not current or not current['enabled']:return False
        if self.edit:
            key=self.edit['key'];target=self.draft if key in ('mode','laps','grid','view','bots') else self.draft['profile']
            target[key]=self.edit['value'];self.edit=None;self.message=''
            return True
        if identity=='confirm.cancel':self.confirm=None;self.selected=self.confirm_return;self.message='';self.normalize();return True
        if identity=='confirm.apply':
            if self.confirm=='discard':self.open(True);return True
            return self.apply(self.confirm)
        if identity=='preset.variants':
            self.picker='variantPreset';self.selected='';self.normalize();return True
        if identity.startswith('preset:'):
            if not self.service.createDriverPreset(identity[7:]):self.message=self.service._message;return False
            self.open(True);self.message='Pilota creato · profilo fisso';self.selected='pilot';return True
        if identity.startswith('pick:'):
            chosen=identity[5:];old=(self.draft['driver'],self.draft['track']);self.profiles[old]=deepcopy(self.draft['profile'])
            self.draft[self.picker]=chosen
            key=(self.draft['driver'],self.draft['track']);self.draft['profile']=deepcopy(self.profiles.get(key) or self.service.profileFor(*key))
            if self.picker=='track':self.draft['participants']=[]
            self.selected=self.picker;self.picker=None;self.message=''
            if self.picker_return:return self.apply('pilot')
            return True
        if identity.startswith('participant:'):
            target=identity[12:];people=self.draft['participants']
            if target in people:people.remove(target)
            elif len(people)<MAX_RACE_DRIVERS:people.append(target)
            else:self.message='Puoi schierare al massimo cinque piloti';return False
            return True
        if identity in OPTIONS:
            self.edit={'key':identity,'value':self.value(identity)};self.message='';return True
        if identity in ('driver','track'):
            self.focus[self.view+':'+self.section]=identity;self.picker=identity;self.selected='pick:'+self.draft[identity];return True
        if identity=='participants':self.view='participants';self.selected='';self.normalize();return True
        if identity=='advanced':self.view='advanced';self.selected='group:network';return True
        if identity.startswith('group:'):self.group_return='advanced';self.group=identity[6:];self.view='group';self.selected='';self.normalize();return True
        if identity=='create':
            if self.dirty:self.confirm_return=identity;self.confirm='apply';self.selected='confirm.cancel';self.message='Applica o scarta la bozza prima di creare un pilota.';return True
            self.picker='preset';self.selected='';self.normalize();return True
        if identity=='memory':
            self.group_return='root';self.view='group';self.group='reproducibility';self.selected='info:memory';return True
        if identity.startswith('source:'):
            self.transfer_source=identity[7:];self.picker=None;self.confirm_return='transfer';self.confirm='transfer';self.selected='confirm.cancel';return True
        if identity=='transfer':
            if self.dirty:return self.request_apply('apply')
            self.picker='source';self.selected='';self.normalize();return True
        if identity in ('apply','start','pilot','reset'):return self.request_apply(identity)
        return False

    def key(self,key):
        if self.draft is None:self.open()
        if key in (2,8) and not self.edit:
            rows=self.rows();index=next((i for i,r in enumerate(rows) if r['id']==self.selected),0)
            if rows:self.selected=rows[max(0,min(len(rows)-1,index+(-1 if key==2 else 1)))]['id']
            self.focus[self.view+':'+self.section]=self.selected
        elif key in (4,6):
            if self.edit:
                values=OPTIONS[self.edit['key']]
                if self.edit['key']=='algorithm':
                    import importlib.util
                    values=[v for v in values if v!='neat' or importlib.util.find_spec('neat') is not None]
                i=values.index(self.edit['value']) if self.edit['value'] in values else 0
                self.edit['value']=values[(i+(-1 if key==4 else 1))%len(values)]
            elif self.view=='root' and not self.picker and not self.confirm:
                sections=['session','training','management'];i=sections.index(self.section)
                self.action('section:'+sections[(i+(-1 if key==4 else 1))%3])
        elif key==5:self.action(self.selected)
        elif key==7:
            if self.edit:self.edit=None
            elif self.confirm:self.confirm=None;self.selected=self.confirm_return;self.message='';self.normalize()
            elif self.picker=='variantPreset':self.picker='preset';self.selected='preset.variants'
            elif self.picker:self.selected=self.picker;self.picker=None
            elif self.view=='group':self.view=self.group_return;self.selected='memory' if self.group_return=='root' else 'group:'+self.group
            elif self.view in ('advanced','participants'):self.selected='advanced' if self.view=='advanced' else 'participants';self.view='root'
            elif self.dirty:self.confirm_return=self.selected;self.confirm='discard';self.selected='confirm.cancel';self.message='La bozza contiene modifiche non salvate'
            else:return 'close'
        return ''
