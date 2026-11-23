"""Async population, calendar and keypad management. No per-frame Python work."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import time
import uuid
from PySide6.QtCore import QObject,Property,QStandardPaths,QTimer,Signal,Slot
from aquarium_catalog import load_3d_catalog
from aquarium_store import AquariumStore


class AquariumPopulation(QObject):
    changed=Signal()
    completed=Signal(object,str)
    operationFinished=Signal(str,bool,str)
    def __init__(self,parent=None,*,path=None):
        super().__init__(parent)
        self.path=path or Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))/'aquarium/aquarium.sqlite'
        self.executor=None;self.store=None;self.catalog=None;self.state={};self.busy=False;self.closed=False;self.error=''
        self.section='present';self.index=0;self.target='';self.draft={};self.name_edit=False;self.cursor=0;self.picker='add';self.historyOffset=0
        self._request_id='';self._silent=False
        self.completed.connect(self._accept)
        self.timer=QTimer(self);self.timer.setInterval(60000);self.timer.timeout.connect(lambda:self.refresh())

    def load(self):
        if not self.state and not self.busy and not self.closed:self.submit('load')

    def submit(self,action,target='',args=None,request_id='',revision=None):
        if self.closed or self.busy:return False
        self.busy=True;self._request_id=request_id;self._silent=action=='refresh'
        if not self._silent:self.changed.emit()
        self.executor=self.executor or ThreadPoolExecutor(max_workers=1,thread_name_prefix='aquarium-state')
        def work():
            if self.store is None:
                self.catalog=load_3d_catalog();self.store=AquariumStore(self.path,self.catalog)
            if action=='prepared':
                if self.store.prepared(target) is False:raise ValueError('Orologio o dati cambiati · riapri l’Acquario')
            elif action=='shown':self.store.shown(target)
            elif action not in ('load','refresh'):self.store.command(action,target,args or {},request_id,revision)
            self.store.reconcile()
            return self.store.snapshot(self.historyOffset)
        future=self.executor.submit(work)
        def done(job):
            try:data,error=job.result(),''
            except Exception as exc:data,error=None,str(exc)
            if not self.closed:self.completed.emit(data,error)
        future.add_done_callback(done)
        return True

    @Slot(object,str)
    def _accept(self,data,error):
        if self.closed:return
        request_id=self._request_id;self._request_id=''
        changed=data is not None and data!=self.state or error!=self.error
        self.busy=False;self.error=error
        if data:self.state=data
        if self.state and not self.timer.isActive():self.timer.start()
        self.index=min(self.index,max(0,len(self.rows())-1))
        if changed or not self._silent:self.changed.emit()
        if request_id:self.operationFinished.emit(request_id,not bool(error),error)

    def refresh(self):
        if self.state and not self.busy:self.submit('refresh')

    def species(self):
        result={}
        import json
        for row in self.state.get('active',[]):
            profile=json.loads(row.get('savedLabel','{}')).get('speciesProfile')
            if profile:result[profile['id']]=profile
        result.update({s['id']:s for s in (self.catalog or {}).get('species',[])})
        return result

    def profile(self,r):
        import json
        saved=json.loads(r.get('savedLabel','{}')).get('speciesProfile')
        return saved or self.species()[r['species']]

    def fish_row(self,r,pending=False):
        s=self.profile(r);v=next((v for v in s['variants'] if v['id']==r['variant']),s['variants'][0]);seed=r['seed']
        return dict(id=r['id'],visitId='' if pending else r['visitId'],operationId=r.get('operationId',''),speciesId=s['id'],assetUrl=s['assetUrl'],name=r['name'],speciesName=s['name'],tint=v['tint'],size=s['referenceSize'],speed=s['speed'],frequency=s['tailFrequency'],phase=(seed%997)/997,seed=seed,startX=.15+(r['slotId']%3)*.32,startY=.24+(r['slotId']//3)*.38,depth=r['slotId']%3)

    def scene(self,effective,session):
        return dict(status='ready' if self.state else 'error' if self.error else 'loading',errorText=self.error,sessionId=session,populationRevision=self.state.get('revision',0),assetRevision=(self.catalog or {}).get('assetRevision',''),fish=[self.fish_row(r) for r in self.state.get('active',[])],pending=[self.fish_row(r,True) for r in self.state.get('pending',[])],effectivePlayback=effective,clockHealthy=self.state.get('clockHealthy',True))

    def rows(self):
        species=self.species();current=self.state.get('active',[]);available={s['id']:s for s in (self.catalog or {}).get('species',[])}
        def row(identity,title,value='',detail=''):return dict(id=str(identity),title=title,value=value,detail=detail)
        if self.section=='present':
            result=[row(r['id'],r['name'],self.profile(r)['name'],('Fisso' if not r['days'] else str(r['days'])+' giorni · '+self.stamp(r['due']))) for r in current]
            return result+[row('add','Aggiungi un pesce',str(len(current))+' / 6','Scegli tipo e variante dal catalogo')]
        if self.section=='catalog':return [row(s['id'],s['name'],'NEL GRUPPO' if s['id'] in self.state.get('pool',[]) else 'ESCLUSO',s['description']) for s in available.values()]
        if self.section=='rotation':return [row('help','Rotazione a giorni','CALENDARIO','Il tempo passa anche a board spenta. Imposta la durata nelle schede dei pesci.')]+[row(s['id'],s['name'],'INCLUSO' if s['id'] in self.state.get('pool',[]) else 'ESCLUSO','5 per cambiare il gruppo automatico') for s in available.values()]
        if self.section=='history':
            result=[row(r['id'],r['label']['name'],r['label']['speciesName'],self.stamp(r['started'])+' · '+('presente' if r['ended'] is None else self.stamp(r['ended']))) for r in self.state.get('history',[])]
            if self.historyOffset:result.append(row('newer','Permanenze più recenti'))
            if self.historyOffset+len(self.state.get('history',[]))<self.state.get('historyCount',0):result.append(row('older','Permanenze precedenti'))
            return result or [row('empty','Nessuna permanenza registrata')]
        if self.section=='species':return [row(s['id'],s['name'],'',s['description']) for s in available.values()]
        if self.section=='places':return [row(r['id'],'Al posto di '+r['name'],self.profile(r)['name'],'Il pesce precedente resterà nello storico') for r in current]
        if self.section=='fish':
            r=next((r for r in current if r['id']==self.target),None)
            if r is None:return [row('back','Torna ai pesci')]
            d=self.draft;s=self.profile(r)
            name=d['name']
            if self.name_edit:
                text=name.ljust(16);name=text[:self.cursor]+'['+text[self.cursor]+']'+text[self.cursor+1:]
            return [row('name','Nome',name,'2/8 lettera · 4/6 posizione · 5 termina' if self.name_edit else '5 per scrivere il nome'),row('variant','Variante',next(v['name'] for v in s['variants'] if v['id']==d['variant']),'4/6 per scegliere'),row('days','Permanenza','FISSO' if not d['days'] else str(d['days'])+' giorni','4/6 per cambiare · 0 mantiene il pesce'),row('next','Prossimo tipo',species.get(d['nextSpecies'],{'name':'Tipo non disponibile'})['name'] if d['nextSpecies'] else 'Dal gruppo automatico','4/6 per scegliere il successore'),row('save','Salva modifiche','','Durata calcolata dalla data di ingresso'),row('replace','Sostituisci adesso','','Scegli un tipo; conserva questo pesce nello storico'),row('remove','Rimuovi dalla vasca','','L’identità e lo storico vengono conservati'),row('back','Torna ai pesci','',s['description'])]
        return []

    @staticmethod
    def stamp(value):return datetime.fromtimestamp(value).strftime('%d/%m %H:%M') if value else '—'

    def management(self):
        titles={'present':'Pesci presenti','catalog':'Catalogo','rotation':'Rotazione','history':'Storico','fish':'Scheda del pesce','species':'Scegli il tipo','places':'Scegli il posto'}
        return dict(section=self.section,title=titles[self.section],selectedIndex=self.index,rows=self.rows(),busy=self.busy,message=self.error or ('Orologio da verificare · rotazione sospesa' if self.state and not self.state['clockHealthy'] else 'Preparazione di un nuovo pesce al ritorno in vasca' if self.state.get('pending') else ''),nameEditing=self.name_edit)

    def open(self):self.load();self.section='present';self.index=0;self.name_edit=False;self.changed.emit()

    def act(self,action,target='',args=None):
        return self.submit(action,target,args or {},uuid.uuid4().hex,(args or {}).get('revision',self.state.get('revision')))

    def key(self,key):
        if self.busy:return True
        if self.name_edit:
            alphabet=' ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            chars=list(self.draft['name'].ljust(16)[:16])
            if key in (4,6):self.cursor=(self.cursor+(-1 if key==4 else 1))%16
            elif key in (2,8):chars[self.cursor]=alphabet[(alphabet.find(chars[self.cursor])+(-1 if key==2 else 1))%len(alphabet)]
            elif key in (5,7):self.name_edit=False
            self.draft['name']=''.join(chars).rstrip();self.changed.emit();return True
        rows=self.rows()
        if key in (2,8):self.index=(self.index+(-1 if key==2 else 1))%max(1,len(rows))
        elif key in (4,6):
            step=-1 if key==4 else 1
            if self.section in ('present','catalog','rotation','history'):
                tabs=['present','catalog','rotation','history'];self.section=tabs[(tabs.index(self.section)+step)%4];self.index=0
            elif self.section=='fish' and rows:
                identity=rows[self.index]['id'];r=next(r for r in self.state['active'] if r['id']==self.target);d=self.draft
                if identity=='days':d['days']=max(0,min(3650,d['days']+step))
                elif identity in ('variant','next'):
                    values=[v['id'] for v in self.profile(r)['variants']] if identity=='variant' else ['']+[s['id'] for s in (self.catalog or {}).get('species',[])]
                    name='variant' if identity=='variant' else 'nextSpecies';d[name]=values[((values.index(d[name]) if d[name] in values else 0)+step)%len(values)]
        elif key==7:
            if self.section=='present':return False
            self.section='present';self.index=0
        elif key==5 and rows:
            target=rows[self.index]['id']
            if self.section=='present':
                if target=='add':self.picker='add';self.section='species';self.index=0
                else:
                    r=next(r for r in self.state['active'] if r['id']==target);self.target=target;self.draft=dict(name=r['name'],variant=r['variant'],days=r['days'],nextSpecies=r['next_species'],revision=self.state['revision']);self.section='fish';self.index=0
            elif self.section in ('catalog','rotation') and target!='help':self.act('pool',target)
            elif self.section=='fish':
                if target=='name':self.name_edit=True;self.cursor=0
                elif target=='save':self.act('save',self.target,self.draft)
                elif target=='remove':self.act('remove',self.target);self.section='present';self.index=0
                elif target=='replace':self.picker='replace';self.section='species';self.index=0
                elif target=='back':self.section='present';self.index=0
            elif self.section=='species':
                self.act(self.picker,self.target if self.picker=='replace' else '',{'species':target});self.section='present';self.index=0
            elif self.section=='history' and target in ('older','newer'):
                self.historyOffset=max(0,self.historyOffset+(100 if target=='older' else -100));self.index=0;self.submit('refresh')
            elif self.section=='history' and target!='empty':
                visit=next(r for r in self.state['history'] if r['id']==target);self.return_fish=visit['fish'];self.section='places';self.index=0
            elif self.section=='places':self.act('replace',target,{'fishId':self.return_fish});self.section='present';self.index=0
        self.changed.emit();return True

    def close(self):
        self.closed=True;self.timer.stop()
        if self.executor:
            if self.store:self.executor.submit(self.store.close)
            self.executor.shutdown(wait=True,cancel_futures=False)
