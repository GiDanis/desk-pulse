"""Independent three-sector timing; never changes physics or learning rewards."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,math
import numpy as np

VERSION='lap-timing-1'
LAYOUT='thirds-1'


def context_hash(config):
    from game_records import category
    category_hash,_=category(config)
    return hashlib.sha256(json.dumps([VERSION,LAYOUT,category_hash]).encode()).hexdigest()


class LapTiming:
    def __init__(self,world,source='preview',saved=None):
        self.source=source;self.track=world.track
        poses=self.track.poses(np.array([self.track.length/3,2*self.track.length/3]))
        self.origins=poses[:,:2];self.axes=np.c_[np.cos(poses[:,2]),np.sin(poses[:,2])]
        self.normals=np.c_[-self.axes[:,1],self.axes[:,0]]
        self.pending=[];self.cars=[]
        for i in range(world.count):
            self.cars.append(dict(start=world.time,standing=True,valid=world.time==0 and not bool(world.lap_invalid[i]),
                partial=world.time>0 or bool(world.lap_invalid[i]),splits=[],expected=0,last=None,personal=None,sessionBest=None,reference=None,display=None,
                driverId='',policyHash='',revision=0,lapId=int(world.lap_count[i])+1,reason=''))
        if saved:
            if saved.get('version')!=VERSION or saved.get('layout')!=LAYOUT or len(saved['cars'])!=world.count:
                raise ValueError('Cronometraggio salvato incompatibile')
            self.cars=deepcopy(saved['cars']);self.source=saved['source'];self.pending=deepcopy(saved.get('pending',[]))

    def bind(self,index,driver,policy,reference=None):
        s=self.cars[index]
        if s['policyHash'] and s['policyHash']!=policy:
            s['revision']+=1
            s.update(valid=False,reason='Modello cambiato',personal=None,sessionBest=None,reference=None,display=None,last=None)
        s.update(driverId=driver,policyHash=policy)
        if reference and s['personal'] is None:
            s['personal']=deepcopy(reference);s['reference']=deepcopy(reference) if reference.get('sectors') else None;s['revision']+=1

    def bind_preview_boundary(self,index,driver,policy,previous_lap,world_time):
        """A new candidate takes control on the first physics tick after finish.

        Preview bests compare successive candidates, never official records.
        Keep the completed lap attributed to its old frozen policy. Ordinary
        mid-lap switches and qualifying/racing still use the strict bind rule.
        """
        s=self.cars[index]
        if self.source!='preview' or s['lapId']!=previous_lap+1 or not s['last'] or s['last']['lap']!=previous_lap or not 0<=world_time-s['start']<=1/60+1e-8:
            raise ValueError('Cambio candidato consentito solo al traguardo della preview')
        s.update(driverId=driver,policyHash=policy,revision=s['revision']+1)

    def advance(self,w,old,new,t,dt,alive,dirty,lap_cross,clean,fraction):
        # Two extra normal crossings; the finish remains the authoritative lap event.
        d0=np.einsum('nkj,kj->nk',old[:,None,:]-self.origins,self.axes)
        d1=np.einsum('nkj,kj->nk',new[:,None,:]-self.origins,self.axes)
        crossed=(d0<0)&(d1>=0)&((d1-d0)>1e-12)
        for i in np.flatnonzero(alive):
            s=self.cars[i]
            if dirty[i] and s['valid']:s['valid']=False;s['reason']='Fuori pista o contatto';s['revision']+=1
            events=[]
            for k in np.flatnonzero(crossed[i]):
                f=float(-d0[i,k]/(d1[i,k]-d0[i,k]));point=old[i]+f*(new[i]-old[i])
                if abs(float((point-self.origins[k])@self.normals[k]))<=self.track.width/2:
                    events.append((f,int(k)))
            if lap_cross[i]:events.append((float(fraction[i]),2))
            for f,k in sorted(events):
                stamp=t+dt*f
                if k<2:
                    if k==s['expected']:
                        previous=s['splits'][-1] if s['splits'] else s['start']
                        if stamp>previous:s['splits'].append(stamp);s['expected']+=1
                        else:s['valid']=False;s['reason']='Intertempi fuori ordine';s['revision']+=1
                        s['display']=None;s['revision']+=1
                    elif k>s['expected']:s['valid']=False;s['reason']='Settore mancante';s['revision']+=1
                else:self._finish(w,i,stamp,bool(clean[i]))

    def _finish(self,w,i,stamp,clean):
        s=self.cars[i];duration=stamp-s['start']
        complete=len(s['splits'])==2 and s['expected']==2
        sectors=np.diff([s['start'],*s['splits'],stamp]).tolist() if complete else None
        valid=bool(s['valid'] and clean and complete and duration>0)
        reference=deepcopy(s['reference']);old_pb=deepcopy(s['personal'])
        record=dict(version=VERSION,layout=LAYOUT,lap=s['lapId'],time=duration,sectors=sectors,clean=valid,
            personalDelta=duration-old_pb['time'] if valid and not s['standing'] and old_pb else None,partial=s.get('partial',False),standingStart=s['standing'],policy=s['policyHash'],driver=s['driverId'],source=self.source,
            reason='' if valid else s['reason'] or 'Giro non valido',id=s['policyHash'][:12]+':'+str(s['lapId']))
        is_pb=valid and not s['standing'] and (old_pb is None or duration<old_pb['time'])
        if valid and not s['standing']:
            if is_pb:s['personal']=deepcopy(record)
            if s['sessionBest'] is None or duration<s['sessionBest']['time']:s['sessionBest']=deepcopy(record)
        s['last']=record
        s['display']=dict(sectors=sectors,deltas=self._delta(sectors,reference) if valid and not s['standing'] else [None]*3,
            label='Δ vs PB precedente' if is_pb and reference and reference==old_pb else self._label(reference),lap=s['lapId'])
        if self.source in ('gara','qualifica'):self.pending.append(deepcopy(record))
        s.update(start=stamp,standing=False,partial=False,valid=True,reason='',splits=[],expected=0,
            reference=deepcopy(s['personal'] if (s['personal'] or {}).get('sectors') else s['sessionBest']),
            lapId=s['lapId']+1,revision=s['revision']+1)

    def _delta(self,sectors,ref):
        if not sectors or not ref or not ref.get('sectors'):return [None]*3
        return [float(a-b) if a is not None else None for a,b in zip(sectors,ref['sectors'])]

    def _label(self,ref):
        if not ref:return 'Settori da misurare'
        return 'Δ vs personale' if ref==next((s['personal'] for s in self.cars if s['reference']==ref),None) else 'Δ vs giro di riferimento'

    def row(self,i):
        s=self.cars[i];last=s['last'];shown=s['display']
        if shown is None:
            ends=[s['start'],*s['splits']];sectors=[ends[j+1]-ends[j] for j in range(len(ends)-1)]+[None]*(3-len(s['splits']))
            shown=dict(sectors=sectors,deltas=self._delta(sectors,s['reference']) if s['valid'] and not s['standing'] else [None]*3,
                label=self._label(s['reference']),lap=s['lapId'])
        return dict(version=VERSION,layout=LAYOUT,source=self.source,policy=s['policyHash'],revision=s['revision'],
            lapId=s['lapId'],currentValid=s['valid'],standingStart=s['standing'],last=last,personal=s['personal'],
            sectors=shown['sectors'],deltas=shown['deltas'],referenceLabel=shown['label'],sectorLap=shown['lap'],reason=s['reason'])

    def drain(self):
        rows=self.pending;self.pending=[];return rows

    def snapshot(self):return dict(version=VERSION,layout=LAYOUT,source=self.source,cars=deepcopy(self.cars),pending=deepcopy(self.pending))


class TimingWriter:
    """Serialize confirmed lap events outside the simulation tick."""
    def __init__(self,store):
        self.store=store;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='race-timing');self.jobs=[]

    def submit(self,session,records):
        self.check()
        if records:self.jobs.append(self.pool.submit(self.store.save_timing,session,records))

    def check(self):
        remaining=[]
        for job in self.jobs:
            if job.done():job.result()
            else:remaining.append(job)
        self.jobs=remaining

    def flush(self):
        for job in self.jobs:job.result()
        self.jobs=[]

    def close(self):
        try:self.flush()
        finally:self.pool.shutdown(wait=True)
