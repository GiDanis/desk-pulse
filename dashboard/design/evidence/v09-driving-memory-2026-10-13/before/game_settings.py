"""Task settings with drafts, explicit selectors and stable focus identities.

No geometry, learning runtime or storage write is needed to browse/edit values.
The service applies the selected configuration only after a deliberate action.
"""
from copy import deepcopy
from game_catalog import TRACKS, race_eligible

from game_profiles import METHODS as PRESETS
METHODS={k:v[1] for k,v in PRESETS.items()}
MODES={'impara':'Impara','gara':'Gara','prova':'Prova standard','campione':'Guida modello'}
OPTIONS={'population':[8,16,32,64,128,256],'hidden':[8,16,32,64],
         'mutation':[.05,.15,.3],'seed':[1,2,3,4,5,11,21,42],
         'episodeSeconds':[30,60,120,180],'learningRate':[.0001,.0003,.001],
         'rollout':[64,128,256,1024,2048],'epochs':[1,2,4,8],'gamma':[.95,.99,.995,.999],
         'algorithm':['evolution','ppo','neat','pure_pursuit','imitation','ppo_smooth'],'traffic':[False,True],
         'mode':list(MODES),'laps':[3,5,10]}
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
        'laps':('Giri','Distanza della gara; le reti restano congelate.')}


def row(identity,title,value='Apri',description='',enabled=True):
    return dict(id=identity,title=title,value=str(value),detail=str(value),description=description,enabled=enabled)


class GameSettings:
    def __init__(self,service):
        self.service=service;self.section='session';self.view='root';self.group='network'
        self.focus={};self.selected='mode';self.draft=None;self.profiles={};self.base=None
        self.edit=None;self.picker=None;self.confirm=None;self.message=''
        self.picker_return=False;self.confirm_return=''

    def current(self):
        s=self.service
        return dict(mode=s._mode,track=s._track,driver=s._selected,laps=s._race_laps,participants=s._participants[:],
                    profile=deepcopy(next((d['profile'] for d in s._drivers if d['id']==s._selected),{})))

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
        return self.draft[key] if key in ('mode','laps') else self.draft['profile'].get(key)

    def text(self,key,value):
        if key=='algorithm':return METHODS.get(value,value)
        if key=='mode':return MODES[value]
        if key=='traffic':return 'Avversario fisso' if value else 'Solo pista'
        if key=='episodeSeconds':return str(value)+' s'
        if key=='rollout':return f'{value:,}'.replace(',','.')+' passi/copia'
        return str(value).replace('.',',')

    def setting(self,key,enabled=True):
        title,description=LABELS[key]
        algo = self.draft['profile'].get('algorithm')
        if key=='population' and algo in ('ppo','ppo_smooth'):
            title,description='Copie ambiente','Tentativi paralleli; in pista una guida dimostrativa.'
        elif key=='population' and algo=='pure_pursuit':
            title,description='Vetture','Guida geometrica di riferimento.'
        elif key=='population' and algo=='imitation':
            title,description='Copie ambiente','Tentativi paralleli di imitazione della linea di riferimento.'
        if key=='mutation' and algo=='neat':
            description='Intensità delle modifiche ai pesi e bias.'
        if key=='algorithm':
            description=PRESETS[algo][3]
            if algo=='evolution':description=f"Rete densa a {self.draft['profile']['hidden']} neuroni · selezione e mutazione."
            elif algo=='neat':description=PRESETS[algo][3]
            elif algo=='ppo':description='Policy gradient Actor-Critic · Campionamento stocastico.'
            elif algo=='pure_pursuit':description='Controllore geometrico matematico ad asse rigido · Sempre pronto.'
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
            if self.picker=='preset':
                import importlib.util
                return [row('preset:'+k,v[1],'Crea',v[3],k!='neat' or importlib.util.find_spec('neat') is not None) for k,v in PRESETS.items()]
            if self.picker=='driver':return [row('pick:'+p['id'],p['name'],'Selezionato' if p['id']==d['driver'] else 'Scegli',METHODS.get(p['profile']['algorithm'],'Identità persistente') + ' · ' + ('Modello salvato' if p['policy'] else 'Da allenare')) for p in s._store.drivers(d['track'])]
            return [row('pick:'+t['id'],t['name'],'Selezionato' if t['id']==d['track'] else 'Scegli',t.get('description','Asfalto asciutto · vettura standard · percorso proprio.')) for t in TRACKS]
        if self.view=='participants':
            def eligible(p):return race_eligible(p,d['track'],max(2,len(d['participants'])+int(p['id'] not in d['participants']))) if d['mode']=='gara' else bool(p['policy'])
            return [row('participant:'+p['id'],p['name'],'Schierato' if p['id'] in d['participants'] else 'Non schierato' if eligible(p) else 'Da qualificare' if p['policy'] else 'Da allenare',
                        'Una vettura; rete salvata congelata.' if eligible(p) else 'Completa la qualifica su questo circuito; puoi usare Prova.' if p['policy'] else 'Serve un modello salvato su questo circuito.',eligible(p)) for p in s._store.drivers(d['track'])]
        if self.view=='advanced':
            return [row('group:network','Rete','Consulta','Tentativi paralleli e dimensione della rete.'),
                    row('group:learning','Apprendimento','Consulta','Parametri specifici del metodo scelto.'),
                    row('group:reproducibility','Riproducibilità','Consulta','Seme iniziale e limite di ogni tentativo.')]
        if self.view=='group':
            method=d['profile']['algorithm']
            keys={'network':['population']+([] if method in ('neat','pure_pursuit') else ['hidden']),
                  'learning':['learningRate','rollout','epochs','gamma'] if method in ('ppo','ppo_smooth') else (['learningRate'] if method=='imitation' else ([] if method=='pure_pursuit' else ['mutation'])),
                  'reproducibility':['seed','episodeSeconds']}[self.group]
            rows=[self.setting(k,enabled=False) for k in keys]
            if self.group=='learning' and method=='ppo_smooth':
                rows.append(row('info:noise','Regolarità','Costo sterzo','Probabilità PPO gaussiana coerente; costo dei comandi bruschi.',False))
            elif self.group=='network' and method=='imitation':
                rows.append(row('info:expert','Guida esperta','Guida e traffico','Esempi del maestro negli stati visitati; la rete guida da sola.',False))
            return rows
        if self.section=='session':
            driver=next((p for p in s._drivers if p['id']==d['driver']),{})
            output=[self.setting('mode'),row('driver','Pilota',driver.get('name','—'),METHODS.get(driver.get('profile',{}).get('algorithm'),'Apri la rosa')+' · Scegli chi allenare.') if d['mode'] in ('impara','campione') else row('participants','Schieramento',str(len(d['participants']))+' piloti','Apri la rosa dei modelli salvati su questo circuito.'),
                    row('track','Circuito',next(t['name'] for t in TRACKS if t['id']==d['track']),'Asfalto asciutto · vettura standard.')]
            if d['mode'] in ('gara','prova'):output.append(self.setting('laps'))
            output.append(row('start',{'impara':'Avvia allenamento','gara':'Avvia gara','prova':'Avvia prova','campione':'Osserva modello'}[d['mode']],'Start',
                              (METHODS.get(d['profile']['algorithm'],'') if d['mode']=='impara' else f"{d['laps']} giri · reti congelate" if d['mode'] in ('gara','prova') else 'Rete congelata · nessun apprendimento')+(' · bozza da confermare' if self.dirty else '')))
            return output
        if self.section=='training':
            if d['mode']!='impara':return [row('readonly','Allenamento','Non previsto','Questa modalità usa reti congelate.',False)]
            algo=d['profile'].get('algorithm')
            method_row=self.setting('algorithm',enabled=False)
            if algo=='pure_pursuit':
                return [method_row,
                        row('traffic','Scenario','Guida e traffico','Controllore geometrico; non richiede apprendimento.',False),
                        row('advanced','Parametri avanzati','Consulta','Rete, apprendimento e riproducibilità.'),
                        row('apply','Applica modifiche','Conferma','Controllore matematico · Nessun apprendimento necessario.',self.dirty)]
            return [method_row,
                    row('traffic','Accademia','Progressiva','Partenza → Passo → Traffico. Dal prossimo Start; il percorso precedente resta salvato.' if d['profile'].get('version')==1 else 'Partenza → Passo → Traffico. Avanza dopo prove valide.',False),
                    row('advanced','Parametri avanzati','Consulta','Rete, apprendimento e riproducibilità.'),
                    row('apply','Applica modifiche','Conferma','Un pilota si allena; gli avversari restano congelati.',self.dirty)]
        return [row('create','Nuovo pilota','Crea','Identità con allenamento e storico indipendenti.'),
                row('pilot','Scheda pilota','Apri','Durata, metodo, sessioni e risultati.'),
                row('reset','Gestisci apprendimento','Apri','Reset del percorso attivo con storico conservato.'),
                row('transfer','Trasferisci da altra pista','Apri','Pesi iniziali compatibili; nuova qualifica richiesta.'),
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
        title='Conferma' if self.confirm else 'Metodo del nuovo pilota' if self.picker=='preset' else 'Scegli pilota' if self.picker=='driver' else 'Scegli circuito' if self.picker else 'Schieramento' if self.view=='participants' else 'Parametri avanzati' if self.view in ('advanced','group') else {'session':'Prepara la sessione','training':'Allenamento','management':'Gestione piloti'}[self.section]
        subtitle=self.message or ('Informazioni del paradigma · Non modificabili' if self.view in ('advanced','group') else ('Modifica valore' if self.edit else 'Modifiche in bozza' if self.dirty else 'Profilo del pilota preconfigurato' if self.section=='training' else 'Configurazione salvata'))
        return dict(rows=rows,selectedIndex=index,selectedId=self.selected,section=self.section,view=self.view,title=title,
                    subtitle=subtitle,dirty=self.dirty,editing=bool(self.edit),tabs=not bool(self.picker or self.confirm or self.view!='root'),
                    confirmation=bool(self.confirm),draft=deepcopy(self.draft))

    def incompatibility(self):
        if self.draft['mode']!='impara':return False
        previous=self.service.profileFor(self.draft['driver'],self.draft['track'])
        return any(previous.get(k)!=self.draft['profile'].get(k) for k in ('algorithm','hidden','population','traffic','seed','observation'))

    def request_apply(self,action):
        if self.dirty and (self.incompatibility() or action in ('pilot','reset','transfer')):
            self.confirm_return=self.selected
            self.confirm=action;self.selected='confirm.cancel';self.message='Apre un percorso distinto; i precedenti restano conservati.'
            return True
        return self.apply(action)

    def apply(self,action):
        s=self.service
        if action=='transfer':
            source=next(t['id'] for t in TRACKS if t['id']!=s._track)
            result=s.transferFrom(source)
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
            key=self.edit['key'];target=self.draft if key in ('mode','laps') else self.draft['profile']
            target[key]=self.edit['value'];self.edit=None;self.message=''
            return True
        if identity=='confirm.cancel':self.confirm=None;self.selected=self.confirm_return;self.message='';self.normalize();return True
        if identity=='confirm.apply':
            if self.confirm=='discard':self.open(True);return True
            return self.apply(self.confirm)
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
            elif len(people)<4:people.append(target)
            else:self.message='Puoi schierare al massimo quattro piloti';return False
            return True
        if identity in OPTIONS:
            self.edit={'key':identity,'value':self.value(identity)};self.message='';return True
        if identity in ('driver','track'):
            self.focus[self.view+':'+self.section]=identity;self.picker=identity;self.selected='pick:'+self.draft[identity];return True
        if identity=='participants':self.view='participants';self.selected='';self.normalize();return True
        if identity=='advanced':self.view='advanced';self.selected='group:network';return True
        if identity.startswith('group:'):self.group=identity[6:];self.view='group';self.selected='';self.normalize();return True
        if identity=='create':
            if self.dirty:self.confirm_return=identity;self.confirm='apply';self.selected='confirm.cancel';self.message='Applica o scarta la bozza prima di creare un pilota.';return True
            self.picker='preset';self.selected='';self.normalize();return True
        if identity=='transfer':
            self.confirm_return=identity;self.confirm='apply' if self.dirty else 'transfer';self.selected='confirm.cancel'
            self.message='Conferma la sessione prima di trasferire i pesi' if self.dirty else 'Trasferimento dei pesi, non del checkpoint';return True
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
            elif self.picker:self.selected=self.picker;self.picker=None
            elif self.view=='group':self.view='advanced';self.selected='group:'+self.group
            elif self.view in ('advanced','participants'):self.selected='advanced' if self.view=='advanced' else 'participants';self.view='root'
            elif self.dirty:self.confirm_return=self.selected;self.confirm='discard';self.selected='confirm.cancel';self.message='La bozza contiene modifiche non salvate'
            else:return 'close'
        return ''
