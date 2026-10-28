"""QML-facing lifecycle; the heavy runtime exists only after explicit Start."""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import queue
import sqlite3
import time
import uuid

from PySide6.QtCore import QObject, Property, QStandardPaths, QTimer, Signal, Slot

from game_catalog import configuration, TRACKS, scope_hash, race_eligible, qualified, visual_content, reference_ready,race_cohort
from game_store import GameStore, validate_profile
from game_curriculum import PHASE_LABELS
from game_profiles import METHODS


class GameService(QObject):
    changed=Signal()
    sceneChanged=Signal()
    operationFinished=Signal(str,bool,str)
    settingsRouteRequested=Signal(str)

    def __init__(self, root=None, parent=None):
        super().__init__(parent)
        default=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'game'
        self._root=Path(root or os.environ.get('SMARTPC_GAME_STORE') or default)
        self._storage_error=''
        try:
            self._store=GameStore(self._root)
            self._drivers=self._store.drivers()
        except (OSError,ValueError,sqlite3.Error) as error:
            self._store=None;self._drivers=[];self._storage_error=str(error)
        self._selected=self._drivers[0]['id'] if self._drivers else ''
        self._history=[];self._classification={}
        self._dossier={}
        self._mode='impara'
        self._participants=[]
        self._race_laps=3
        self._track='oval-1'
        self._run_state='idle'
        self._save_state='idle'
        self._message='Scegli un pilota · 5 Start'
        if self._storage_error:self._message='Archivio gioco non disponibile: '+self._storage_error
        self._scene={'cars':[],'sensors':[],'sequence':0,'engine':'CPU','meta':{}}
        self._display='tutte'
        self._camera='segui'
        self._selected_attempt=0
        self._process=self._command=self._frames=None
        self._epoch=''
        self._pause_started=None
        self._start_started=None
        self._release_after_save=False
        self._closing=False
        self._timer=QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._poll)
        from game_settings import GameSettings
        self._settings=GameSettings(self)
        self._refresh()

    def _refresh(self):
        if self._store:
            try:
                self._drivers=self._store.drivers()
                self._history=self._store.history(self._selected)
                self._classification=self._leaderboard()
                from game_dossier import dossier
                self._dossier=dossier(self._store,self._selected)
            except (OSError,ValueError,sqlite3.Error) as error:
                self._storage_error=str(error);self._message='Archivio gioco non disponibile: '+str(error)
        self.changed.emit()

    @Property('QVariantMap',notify=changed)
    def snapshot(self):
        visual_config,drawing=visual_content(self._track)
        driver=next((row for row in self._drivers if row['id']==self._selected),{})
        rows=[{'id':d['id'],'name':d['name'],'number':d['number'],'algorithm':(d['policy_profile'] or d['profile'])['algorithm'],
               'policyHash':d['policy'] or '', 'steps':d['steps'],'seconds':d['seconds'],
               'traffic':(d['policy_profile'] or d['profile'])['traffic'],'hasPolicy':d['trained'],
               'verified':qualified(d,self._track),
               'reference':reference_ready(d,self._track),
               'hasCandidate':bool(d['candidate']),
               'selected':d['id']==self._selected,'participant':d['id'] in self._participants} for d in self._drivers]
        return {'mode':self._mode,'runState':self._run_state,'saveState':self._save_state,
                'controlMode':'simulation' if self.captured else 'navigation',
                'message':self._message,'selectedDriverId':self._selected,
                'selectedDriverName':driver.get('name',''),'drivers':rows,
                'display':self._display,'camera':self._camera,'participants':self._participants,'raceLaps':self._race_laps,
                'profile':driver.get('profile',{}),'configuration':visual_config,
                'trackId':self._track,'tracks':[dict(t) for t in TRACKS],
                'drawing':drawing,
                'settings':self._settings.snapshot(),
                'algorithms':[{'id':method,'name':data[1],
                    'available':bool(importlib.util.find_spec('numpy') and (method!='neat' or importlib.util.find_spec('neat')))}
                    for method,data in METHODS.items()],
                'leaderboard':self._classification,'history':self._history,
                'progress':self._progress(driver),'dossier':self._dossier,
                'available':not bool(self._storage_error)}

    def _progress(self, driver):
        state=driver.get('curriculum') or {}
        champion=state.get('champion') if qualified(driver,self._track) else None
        proof=champion['proof'] if champion else None
        points=[{'round':p['round'],'valid':p['candidate']['valid'],'total':p['candidate']['total'],
                 'time':p['candidate']['median'],'best':p['candidate']['best'],
                 'phaseId':p['phase'],
                 'phase':PHASE_LABELS.get(p['phase'],p['phase']),'promoted':p['promoted']}
                for p in state.get('evaluations',[])]
        return {'phase':PHASE_LABELS.get(state.get('phase','legacy'),'Precedente') if driver.get('candidate') or driver.get('policy') else 'Da allenare',
                'phaseId':state.get('phase','legacy'),'academy':bool(state.get('academyVersion')),
                'verified':bool(champion),'champion':proof['candidate'] if proof else {},
                'baseline':state.get('baseline') or {},'evaluations':points,
                'promotionGain':proof['champion']['median']-proof['candidate']['median'] if proof and proof['champion'] and proof['champion']['median'] is not None else None,
                'rewardVersion':state.get('rewardVersion','legacy'),
                'evaluationSeconds':state.get('evaluationSeconds',0)}

    def _leaderboard(self):
        from game_catalog import LEGACY_OBSERVATION_VERSION,ACADEMY_OBSERVATION_VERSION
        accepted={scope_hash(self._track),scope_hash(self._track,LEGACY_OBSERVATION_VERSION),scope_hash(self._track,ACADEMY_OBSERVATION_VERSION)}
        sessions=[s for s in self._store.sessions() if s['payload'].get('scope') in accepted]
        latest_race=next((s for s in sessions if s['mode']=='gara'),None)
        latest_trial=next((s for s in sessions if s['mode']=='prova'),None)
        output={'race':[],'trial':[],'raceId':'','trialId':'','date':''}
        if latest_race:
            data=latest_race['payload']
            names={d['id']:d for d in data['participants']}
            for row in sorted(data['results'],key=lambda x:x['position']):
                person=names[row['id']]
                output['race'].append({**row,'name':person['name'],'policyHash':person['policy'],
                                       'previous':(self._store.driver(row['id']) or {}).get('policy')!=person['policy']})
            output['raceId'],output['date']=latest_race['id'],latest_race['created']
            output['racePhysics']=data.get('configuration',{}).get('physics','Precedente')
        if latest_trial:
            import statistics
            data=latest_trial['payload']
            for person in data['participants']:
                rows=[x for x in data['results'] if x['driver']==person['id']]
                valid=[x['time'] for x in rows if x['time'] is not None]
                progress=statistics.median([x['progress'] for x in rows])
                output['trial'].append({'id':person['id'],'name':person['name'],'valid':len(valid),
                    'time':statistics.median(valid) if valid else None,'best':min(valid) if valid else None,
                    'progress':progress,'policyHash':person['policy'],
                    'previous':(self._store.driver(person['id']) or {}).get('policy')!=person['policy']})
            output['trial'].sort(key=lambda x:(-x['valid'],x['time'] if x['time'] is not None else float('inf'),
                                              x['best'] if x['best'] is not None else float('inf'),-x['progress']))
            last=None;position=0
            data=latest_trial['payload']
            for row in output['trial']:
                row['total']=sum(1 for r in data.get('results',[]) if r.get('driver')==row['id'])
                row['laps']=data.get('rules',{}).get('laps',1)
                row['protocol']=data.get('trialProtocol','legacy-five-starts')
            for i,row in enumerate(output['trial']):
                key=(row['valid'],row['time'],row['best'],row['progress'] if not row['valid'] else None)
                if key!=last:position=i+1
                row['position']=position;last=key
            output['trialId']=latest_trial['id']
            output['trialPhysics']=data.get('configuration',{}).get('physics','Precedente')
        for kind,mode,latest in (('race','gara',latest_race),('trial','prova',latest_trial)):
            config=latest['payload']['configuration'] if latest else configuration(self._track,ACADEMY_OBSERVATION_VERSION)
            output[kind+'Records']=self._store.record_summary(config,mode)
        return output

    @Property('QVariantMap',notify=sceneChanged)
    def scene(self):return self._scene

    @Property(bool,notify=changed)
    def captured(self):return self._run_state in ('starting','running','pausing')

    @Slot()
    def openSettings(self):
        self._settings.open();self.changed.emit()

    @Slot()
    def openPilotPicker(self):
        self._settings.open(True);self._settings.section='session';self._settings.action('driver')
        self._settings.picker_return=True;self.changed.emit()

    @Slot(int,result=str)
    def settingsKey(self,key):
        result=self._settings.key(key);self.changed.emit();return result

    @Slot(str,int,result=bool)
    def settingsAction(self,identity,direction=1):
        result=self._settings.action(identity,direction);self.changed.emit();return result

    @Slot(str,str,result='QVariantMap')
    def profileFor(self,identity,track):
        return (self._store.driver(identity,track) or {}).get('profile',{}) if self._store else {}

    @Slot(str,result=bool)
    def setTrack(self,identity):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        try:
            self.stop();self._store.select_track(identity);self._track=identity
            self._participants=[];self._message='Circuito selezionato · percorso indipendente'
            self._refresh();return True
        except (OSError,ValueError,sqlite3.Error) as error:
            self._message=str(error);self.changed.emit();return False

    @Slot('QVariantMap',result=bool)
    def applySetup(self,draft):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        old_track=self._track
        try:
            d=dict(draft);track=d['track'];identity=d['driver'];mode=d['mode']
            if track not in {t['id'] for t in TRACKS} or mode not in ('impara','gara','prova','campione'):raise ValueError('Sessione non valida')
            driver=self._store.driver(identity,track)
            if not driver:raise ValueError('Pilota sconosciuto')
            profile=validate_profile(dict(d['profile']))
            if profile['algorithm']=='neat' and importlib.util.find_spec('neat') is None:raise ValueError('NEAT non disponibile')
            if type(d['laps']) is not int or d['laps'] not in (3,5,10):raise ValueError('Giri non validi')
            ids=list(d['participants'])
            if len(ids)>4 or len(set(ids))!=len(ids) or any(not (self._store.driver(i,track) or {}).get('policy') for i in ids):raise ValueError('Schieramento non valido')
            self.stop();self._store.select_track(track)
            if mode=='impara':self._store.set_profile(identity,profile)
            self._track=track;self._selected=identity;self._mode=mode;self._race_laps=d['laps'];self._participants=ids
            self._message='Sessione confermata';self._refresh();return True
        except (KeyError,TypeError,OSError,ValueError,sqlite3.Error) as error:
            self._store.select_track(old_track)
            self._message=str(error);self.changed.emit();return False

    @Slot(str,result=bool)
    def transferFrom(self,source):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        try:
            self.stop();self._store.initialize_from(self._selected,source)
            self._message='Pesi iniziali trasferiti · nuova qualifica richiesta';self._refresh();return True
        except (OSError,ValueError,sqlite3.Error) as error:
            self._message=str(error);self.changed.emit();return False

    @Slot(str,result=bool)
    def selectDriver(self, identity):
        if self._storage_error or self.captured or self._save_state=='saving' or not self._store.driver(identity):return False
        self.stop()
        self._selected=identity
        self._selected_attempt=0
        self._message='Pilota selezionato · 5 Start'
        self._refresh()
        return True

    @Slot(str,result=bool)
    def setMode(self, mode):
        if self.captured or self._save_state=='saving' or mode not in ('impara','gara','prova','campione'):return False
        self.stop()
        self._mode=mode
        if mode=='gara' and not self._participants:
            self._participants=[row['id'] for row in self._store.drivers() if race_eligible(row,self._track)][:4]
        self._message='Scegli i partecipanti' if mode in ('gara','prova') else '5 Start'
        self.changed.emit()
        return True

    @Slot(int,result=bool)
    def setRaceLaps(self, laps):
        if self.captured or self._save_state=='saving' or laps not in (3,5,10):return False
        self.stop();self._race_laps=laps;self.changed.emit();return True

    @Slot(str,result=bool)
    def toggleParticipant(self, identity):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        item=self._store.driver(identity)
        if not item or not item['policy']:
            self._message='Questo pilota non ha un modello salvato';self.changed.emit();return False
        if identity not in self._participants and self._mode=='gara' and not race_eligible(item,self._track):
            self._message='Questo pilota deve completare la qualifica sul circuito';self.changed.emit();return False
        if identity in self._participants:self._participants.remove(identity)
        elif len(self._participants)<4:self._participants.append(identity)
        else:return False
        self.changed.emit()
        return True

    @Slot(str,result=bool)
    def createDriver(self, name):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        self.stop()
        try:self._selected=self._store.create_driver(name)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._refresh()
        return True

    @Slot(str,result=bool)
    def createDriverPreset(self, algorithm):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        self.stop()
        try:self._selected=self._store.create_driver('',algorithm)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._refresh();return True

    @Slot(str,result=bool)
    def resetDriver(self, identity):
        if self._storage_error or self.captured or self._save_state=='saving' or identity!=self._selected:return False
        self.stop()
        try:self._store.reset_driver(identity)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._participants=[p for p in self._participants if p!=identity]
        self._save_state='idle';self._selected_attempt=0
        self._message='Apprendimento azzerato · storico conservato'
        self._refresh();return True

    @Slot(str,result=bool)
    def resetAllDriver(self,identity):
        if self._storage_error or self.captured or self._save_state=='saving' or identity!=self._selected:return False
        self.stop()
        try:self._store.reset_all(identity)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._participants=[p for p in self._participants if p!=identity]
        self._save_state='idle';self._selected_attempt=0
        self._message='Base e contesti azzerati · storico conservato';self._refresh();return True

    @Slot('QVariantMap',result=bool)
    def configure(self, changes):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        self.stop()
        try:
            driver=self._store.driver(self._selected)
            profile=validate_profile({**driver['profile'],**dict(changes)})
            if profile['algorithm']=='neat' and importlib.util.find_spec('neat') is None:
                raise ValueError('NEAT non disponibile')
            self._store.set_profile(self._selected,profile)
            self._message='Profilo salvato'
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._refresh()
        return True

    @Slot(result=bool)
    def start(self):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        if self._process and self._process.is_alive() and self._run_state=='paused':
            if not self._send({'type':'resume'}):return False
            self._timer.setInterval(16);self._run_state='starting';self._start_started=time.monotonic();self.changed.emit();return True
        self.stop()
        if self._process is not None:return False
        academy_start=self._mode=='impara'
        if self._mode=='impara' and self._store.driver(self._selected)['profile']['algorithm']=='pure_pursuit':self._mode='campione'
        if self._mode in ('gara','prova','campione'):
            ids=self._participants if self._mode!='campione' else [self._selected]
            error=''
            if self._mode=='gara' and not 2<=len(ids)<=4:error='Schiera da due a quattro piloti con modello salvato'
            elif not ids:error='Schiera almeno un pilota con modello salvato'
            elif any(not (self._store.driver(identity) or {}).get('policy') for identity in ids):error='Un partecipante non ha ancora un modello da gara'
            elif self._mode=='gara' and any(not race_eligible(self._store.driver(identity),self._track,len(ids)) for identity in ids):error='Completa la qualifica Gara 2 o Gara 4 dei piloti; puoi usare Prova'
            if not error:
                try:race_cohort([self._store.driver(i) for i in ids],self._track)
                except ValueError as problem:error=str(problem)
            if error:self._message=error;self.changed.emit();return False
        if importlib.util.find_spec('numpy') is None:
            self._message='Runtime di apprendimento non disponibile';self._run_state='error';self.changed.emit();return False
        from game_worker import worker_main
        context=multiprocessing.get_context('spawn')
        self._command,child=context.Pipe()
        self._frames=context.Queue(maxsize=2)
        self._epoch=uuid.uuid4().hex
        request={'mode':self._mode,'driver':self._selected,'participants':self._participants[:],
                 'academy':academy_start,
                 'epoch':self._epoch,'selected':self._selected_attempt,'laps':self._race_laps,'track':self._track}
        self._process=context.Process(target=worker_main,args=(child,self._frames,str(self._root),request),daemon=False)
        try:self._process.start()
        except (OSError,RuntimeError) as error:
            child.close();self.stop();self._fail('Avvio non riuscito: '+str(error));return False
        child.close()
        self._run_state='starting';self._start_started=time.monotonic();self._save_state='idle'
        self._message='Avvio';self.changed.emit();self._timer.setInterval(33);self._timer.start()
        return True

    @Slot(result=bool)
    def pause(self):
        if self._run_state not in ('running','starting'):return False
        if not self._send({'type':'pause'}):return False
        self._timer.setInterval(16)
        self._run_state='pausing';self._pause_started=time.monotonic()
        self._message='Pausa in corso';self.changed.emit()
        return True

    @Slot()
    def suspend(self):
        """Leaving the family releases its process after the durable pause."""
        if not self._process:return
        self._release_after_save=True
        if self._run_state in ('running','starting'):self.pause()
        elif self._run_state!='pausing' and self._save_state!='saving':self.stop()

    def _fail(self, message):
        self._run_state='error';self._message=message
        self._pause_started=self._start_started=None
        if self._save_state=='saving':self._save_state='error'
        for operation in ('start','pause','save'):self.operationFinished.emit(operation,False,message)
        self.changed.emit()

    def _send(self, message):
        try:
            if not self._command:return False
            self._command.send(message);return True
        except (BrokenPipeError,EOFError,OSError):
            self._fail('Worker interrotto · checkpoint precedente');return False

    @Slot(int)
    def selectAttempt(self, delta):
        if self._run_state!='running':return
        count=max(1,self._scene.get('meta',{}).get('count',1))
        self._selected_attempt=(self._selected_attempt+delta)%count
        self._send({'type':'select','index':self._selected_attempt})
        self.changed.emit()

    @Slot(int)
    def displayStep(self, delta):
        if self._run_state!='running':return
        modes=['segui','duello','circuito','sensori']
        self._camera=modes[(modes.index(self._camera)+delta)%len(modes)]
        self._display='sensori' if self._camera=='sensori' else 'tutte'
        self.changed.emit()

    def _poll(self):
        if not self._process:return
        if self._closing:
            if not self._process.is_alive():self.stop()
            return
        if self._command:
            try:
                while self._command.poll():
                    message=self._command.recv()
                    if message.get('session')!=self._epoch:continue
                    kind=message['type']
                    if kind=='ready':
                        self._timer.setInterval(33)
                        self._run_state='running';self._start_started=None;self._message={'impara':'Impara','gara':'Gara','prova':'Prova standard','campione':'Campione'}[self._mode]
                        self.operationFinished.emit('start',True,'')
                        self._refresh()
                    elif kind=='paused':
                        self._timer.setInterval(250)
                        self._run_state='paused';self._pause_started=None
                        self._save_state='saving' if self._mode=='impara' else 'idle';self._message=message.get('message') or 'In pausa'
                        self.operationFinished.emit('pause',True,'')
                    elif kind=='saved':self._save_state='saved';self._refresh();self.operationFinished.emit('save',True,'')
                    elif kind=='save_failed':self._save_state='error';self._message='Salvataggio non riuscito: '+message['message'];self.operationFinished.emit('save',False,message['message'])
                    elif kind=='finished':self._run_state='finished';self._message='Gara conclusa' if self._mode=='gara' else 'Prova conclusa';self._refresh()
                    elif kind=='error':self._fail(message['message'])
                    self.changed.emit()
            except (EOFError,OSError):pass
        newest=None
        try:
            while True:
                frame=self._frames.get_nowait()
                if frame.get('session')==self._epoch and frame.get('sequence',0)>self._scene.get('sequence',0):newest=frame
        except (queue.Empty,OSError):pass
        if newest:
            self._scene=newest;self.sceneChanged.emit()
        now=time.monotonic()
        if self._release_after_save and self._run_state not in ('starting','running','pausing') and self._save_state!='saving':
            self.stop();return
        if self._pause_started and now-self._pause_started>2:
            self._process.terminate();self._fail('Sessione interrotta · checkpoint precedente')
        if self._start_started and now-self._start_started>20:
            self._process.terminate();self._fail('Avvio non riuscito')
        if not self._process.is_alive():
            if self._run_state not in ('error','idle','finished'):
                self._fail('Worker interrotto · checkpoint precedente')
            self._timer.stop()

    @Slot()
    def stop(self):
        if self._process:
            if self._process.is_alive():
                try:self._command.send({'type':'stop'})
                except (BrokenPipeError,EOFError,OSError):pass
                self._process.join(0.15)
                if self._process.is_alive():self._process.terminate();self._process.join(0.3)
                if self._process.is_alive():
                    self._process.kill();self._process.join(0.3)
                if self._process.is_alive():
                    self._closing=True;self._run_state='pausing'
                    self._message='Chiusura worker in corso';self._timer.start();self.changed.emit();return
            self._process.close();self._process=None
        if self._command:self._command.close();self._command=None
        if self._frames:self._frames.close();self._frames=None
        self._timer.stop()
        self._closing=False
        self._run_state='idle';self._pause_started=self._start_started=None
        self._release_after_save=False
        self._scene={'cars':[],'sensors':[],'sequence':0,'engine':'CPU','meta':{}}
        self.sceneChanged.emit();self.changed.emit()

    def close(self):self.stop()
