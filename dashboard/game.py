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
from collections import deque

from PySide6.QtCore import QObject, Property, QStandardPaths, QTimer, Qt, Signal, Slot

from game_catalog import configuration, TRACKS, scope_hash, race_eligible, qualified, visual_content, reference_ready
from game_store import GameStore, validate_profile
from game_curriculum import PHASE_LABELS
from game_modes import MODES, LEGACY, learning, qualified_snapshot, GRID, MAX_RACE_DRIVERS
from game_profiles import METHODS


class GameService(QObject):
    changed=Signal()
    sceneChanged=Signal()
    operationFinished=Signal(str,bool,str)
    settingsRouteRequested=Signal(str)

    def __init__(self, root=None, parent=None, *, async_metadata=False,process_backend='spawn'):
        super().__init__(parent)
        if process_backend not in ('spawn','local'):raise ValueError('Backend processo non valido')
        self._process_backend=process_backend
        self._async_metadata=async_metadata
        self._metadata_reader=None
        self._metadata_ticket=0
        self._metadata_closed=False
        self._metadata_failures=0
        self._metadata_scope=None
        default=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))/'game'
        self._root=Path(root or os.environ.get('SMARTPC_GAME_STORE') or default)
        self._storage_error=''
        try:
            self._store=GameStore(self._root)
            if self._store.reference_release().get('qualified') is True:self._process_backend='local'
            self._drivers=[] if async_metadata else self._store.drivers()
        except (OSError,ValueError,sqlite3.Error) as error:
            self._store=None;self._drivers=[];self._storage_error=str(error)
        self._selected=next((d['id'] for d in self._drivers if d['profile']['algorithm']!='race_master'),self._drivers[0]['id'] if self._drivers else '')
        self._history=[];self._classification={}
        self._dossier={}
        self._mode='impara'
        self._participants=[]
        self._race_laps=3
        self._grid_order='fastest_first';self._training_view='pilot';self._bots=2
        self._track='oval-1'
        self._run_state='idle'
        self._save_state='idle'
        self._message='Scegli un pilota · 5 Start'
        if self._storage_error:self._message='Archivio gioco non disponibile: '+self._storage_error
        self._scene={'cars':[],'sensors':[],'sequence':0,'engine':'CPU','meta':{}}
        self._display='tutte'
        self._camera='circuito'
        self._selected_attempt=0
        self._process=self._command=self._frames=None
        self._epoch=''
        self._pause_started=None;self._pause_ack_started=None
        self._start_started=None
        self._release_after_save=False
        self._closing=False
        self._stop_started=None
        self._stop_stage=0
        self._pending_start=None
        self._pending_mutation=None
        self.input_diagnostics=deque(maxlen=128)
        self.startup_diagnostics=deque(maxlen=32)
        self._timer=QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._poll)
        from game_settings import GameSettings
        self._settings=GameSettings(self)
        self._refresh()

    def _refresh(self):
        if self._metadata_closed:return
        if self._async_metadata and self._store:
            scope=(self._track,getattr(self._store,'objective','impara'))
            if self._metadata_scope is not None and scope!=self._metadata_scope:
                self._drivers=[]
                self._classification={}
                self._dossier={}
            self._metadata_scope=scope
            if self._dossier.get('id')!=self._selected:self._dossier={}
            if self._metadata_reader is None or self._metadata_reader.closed:
                if self._metadata_reader:self._metadata_reader.deleteLater()
                from game_metadata import MetadataReader
                self._metadata_reader=MetadataReader(self._root,self._metadata_ready,self,backend=self._process_backend)
            self._metadata_ticket+=1
            self._metadata_reader.request(self._metadata_ticket,self._selected,self._track,
                                          getattr(self._store,'objective','impara'))
            self.changed.emit()
            return
        if self._store:
            try:
                self._drivers=self._store.drivers()
                self._classification=self._leaderboard()
                from game_dossier import dossier
                self._dossier=dossier(self._store,self._selected,driver=next((d for d in self._drivers if d['id']==self._selected),None))
            except (OSError,ValueError,sqlite3.Error) as error:
                self._storage_error=str(error);self._message='Archivio gioco non disponibile: '+str(error)
        self.changed.emit()

    def _metadata_ready(self, result):
        if result['ticket']!=self._metadata_ticket:return
        if result.get('error'):
            self._storage_error=result['error']
            self._message='Archivio gioco non disponibile: '+result['error']
            self._metadata_failures+=1
            if self._metadata_failures<=3:QTimer.singleShot(2000,self._refresh)
        else:
            self._storage_error=''
            self._metadata_failures=0
            self._drivers=result['drivers']
            self._selected=result['selected']
            self._classification=result['classification']
            self._dossier=result['dossier']
        self.changed.emit()

    def _menu_drivers(self, track):
        # Getters reuse the last complete read projection; commands still
        # validate against the writer store immediately before mutation/Start.
        if self._async_metadata and track==self._track:return self._drivers
        return self._store.drivers(track) if self._store else []

    @Property('QVariantMap',notify=changed)
    def snapshot(self):
        visual_config,drawing=visual_content(self._track)
        driver=next((row for row in self._drivers if row['id']==self._selected),{})
        rows=[{'id':d['id'],'name':d['name'],'number':d['number'],'algorithm':(d['policy_profile'] or d['profile'])['algorithm'],
               'policyHash':d['policy'] or '', 'steps':d['steps'],'seconds':d['seconds'],
               'traffic':(d['policy_profile'] or d['profile'])['traffic'],'hasPolicy':d['trained'],
               'verified':race_eligible(d,self._track), 'qualifyingTime':(qualified_snapshot(d,self._track) or {}).get('bestLap'),
               'reference':reference_ready(d,self._track),
               'hasCandidate':bool(d['candidate']),
               'selected':d['id']==self._selected,'participant':d['id'] in self._participants} for d in self._drivers]
        return {'mode':self._mode,'runState':self._run_state,'saveState':self._save_state,
                'controlMode':'simulation' if self.captured else 'navigation',
                'message':self._message,'selectedDriverId':self._selected,
                'selectedDriverName':driver.get('name',''),'drivers':rows,
                'gridOrder':self._grid_order,'trainingView':self._training_view,'bots':self._bots,'display':self._display,'camera':self._camera,'participants':self._participants,'raceLaps':self._race_laps,
                'profile':driver.get('profile',{}),'configuration':visual_config,
                'trackId':self._track,'tracks':[dict(t) for t in TRACKS],
                'drawing':drawing,
                'settings':self._settings.snapshot(),
                'algorithms':[{'id':method,'name':data[1],
                    'available':bool(importlib.util.find_spec('numpy') and (method!='neat' or importlib.util.find_spec('neat')))}
                    for method,data in METHODS.items() if method.startswith(('residual_','race_'))],
                'leaderboard':self._classification,
                'progress':self._progress(driver),'dossier':self._dossier,
                'available':not bool(self._storage_error)}

    def _progress(self, driver):
        if '_progress' in driver:return driver['_progress']
        state=driver.get('curriculum') or {}
        champion=(state.get('raceChampion') or state.get('champion')) if qualified(driver,self._track) else None
        proof=champion['proof'] if champion else None
        from game_results import exercise
        points=[]
        for p in state.get('evaluations',[]):
            detail=exercise(p)
            points.append({'round':p['round'],'valid':p['candidate']['valid'],'total':p['candidate']['total'],
                 'time':p['candidate']['median'],'best':p['candidate'].get('best',p['candidate']['median']),
                 'tested':detail['tested'],
                 'goalMeters':detail['goalMeters'],
                 'comparisonKey':str(detail['comparisonKey']),
                 'summary':detail['title']+' · '+detail['value'],
                 'retained':p['candidate'].get('retained',False),
                 'phaseId':p['phase'],
                 'phase':PHASE_LABELS.get(p['phase'],p['phase']),'promoted':p.get('promoted',p.get('accepted',False))})
        return {'phase':PHASE_LABELS.get(state.get('phase','legacy'),'Precedente') if driver.get('candidate') or driver.get('policy') else 'Da allenare',
                'phaseId':state.get('phase','legacy'),'academy':bool(state.get('academyVersion')),
                'verified':bool(champion),'champion':proof['candidate'] if proof else {},
                'baseline':state.get('baseline') or {},'evaluations':points,
                'promotionGain':(proof.get('raceReferenceMedian') if proof.get('raceAccepted') and proof.get('raceReferenceMedian') is not None else proof['champion']['median'])-proof['candidate']['median'] if proof and proof['champion'] and proof['champion']['median'] is not None else None,
                'rewardVersion':state.get('rewardVersion','legacy'),
                'evaluationSeconds':state.get('evaluationSeconds',0)}

    def _leaderboard(self):
        current={d['id']:d for d in self._drivers}
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
                                       'previous':current.get(row['id'],{}).get('policy')!=person['policy']})
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
                    'previous':current.get(person['id'],{}).get('policy')!=person['policy']})
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
        output['qualificationRecords']=self._store.record_summary(configuration(self._track,ACADEMY_OBSERVATION_VERSION),'qualifica')
        output['qualification']=[]
        for d in self._drivers:
            cert=qualified_snapshot(d,self._track)
            if cert:output['qualification'].append(dict(id=d['id'],name=d['name'],bestLap=cert['bestLap'],time=cert['bestLap'],policyHash=cert['policy'],status='Qualificato',finishTime=cert['bestLap']))
        output['qualification'].sort(key=lambda r:r['bestLap'])
        for i,r in enumerate(output['qualification']):r['position']=i+1
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
        started=time.monotonic();before=self._settings.selected
        result=self._settings.key(key)
        self.input_diagnostics.append(dict(key=key,before=before,after=self._settings.selected,
            view=self._settings.view,editing=bool(self._settings.edit),state=self._run_state,
            milliseconds=(time.monotonic()-started)*1000))
        self.changed.emit();return result

    @Slot(str,int,result=bool)
    def settingsAction(self,identity,direction=1):
        result=self._settings.action(identity,direction);self.changed.emit();return result

    @Slot(str,str,result='QVariantMap')
    def profileFor(self,identity,track):
        if self._async_metadata:
            return next((d['profile'] for d in self._drivers if d['id']==identity and track==self._track),{})
        return (self._store.driver(identity,track) or {}).get('profile',{}) if self._store else {}

    @Slot(str,result=bool)
    def setTrack(self,identity):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        if self._defer_mutation(lambda:self.setTrack(identity)):return True
        if identity!='oval-1' and any(d['profile']['algorithm'].startswith(('race_','residual_')) for d in self._drivers):
            self._message='Nuova base da qualificare su questo circuito';self.changed.emit();return False
        try:
            self.stop();self._store.select_track(identity);self._track=identity
            self._participants=[];self._message='Circuito selezionato · percorso indipendente'
            self._refresh();return True
        except (OSError,ValueError,sqlite3.Error) as error:
            self._message=str(error);self.changed.emit();return False

    @Slot('QVariantMap',result=bool)
    def applySetup(self,draft):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        if self._defer_mutation(lambda:self._apply_stopped_setup(draft)):return True
        old_track=self._track
        try:
            d=dict(draft);track=d['track'];identity=d['driver'];mode=d['mode']
            if track not in {t['id'] for t in TRACKS} or mode not in set(MODES)|LEGACY:raise ValueError('Sessione non valida')
            driver=self._store.driver(identity,track)
            if not driver:raise ValueError('Pilota sconosciuto')
            profile=validate_profile(dict(d['profile']))
            if profile['algorithm'].startswith(('race_','residual_')) and track!='oval-1':raise ValueError('Nuova base da qualificare su questo circuito')
            if profile['algorithm']=='neat' and importlib.util.find_spec('neat') is None:raise ValueError('NEAT non disponibile')
            if type(d['laps']) is not int or d['laps'] not in (3,5,10):raise ValueError('Giri non validi')
            if d.get('grid',self._grid_order) not in GRID or d.get('view',self._training_view) not in ('pilot','attempts') or d.get('bots',self._bots) not in (1,2,3):raise ValueError('Opzioni non valide')
            ids=list(d['participants'])
            if len(ids)>MAX_RACE_DRIVERS or len(set(ids))!=len(ids) or any(not self._store.driver(i,track) for i in ids):raise ValueError('Schieramento non valido')
            self.stop();self._store.select_track(track)
            if learning(mode):self._store.set_profile(identity,profile)
            self._track=track;self._selected=identity;self._mode=mode;self._race_laps=d['laps'];self._participants=ids
            self._grid_order=d.get('grid',self._grid_order);self._training_view=d.get('view',self._training_view);self._bots=d.get('bots',self._bots)
            if self._grid_order not in GRID or self._training_view not in ('pilot','attempts') or self._bots not in (1,2,3):raise ValueError('Opzioni non valide')
            if learning(mode):self._store.select_objective(mode)
            self._message='Sessione confermata';self._refresh();return True
        except (KeyError,TypeError,OSError,ValueError,sqlite3.Error) as error:
            self._store.select_track(old_track)
            self._message=str(error);self.changed.emit();return False

    @Slot(str,result=bool)
    def transferFrom(self,source):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        if self._defer_mutation(lambda:self.transferFrom(source)):return True
        try:
            self.stop();self._store.initialize_from(self._selected,source)
            self._message='Pesi iniziali trasferiti · nuova qualifica richiesta';self._refresh();return True
        except (OSError,ValueError,sqlite3.Error) as error:
            self._message=str(error);self.changed.emit();return False

    @Slot(str,result=bool)
    def selectDriver(self, identity):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        if self._defer_mutation(lambda:self.selectDriver(identity)):return True
        if not any(d['id']==identity for d in self._menu_drivers(self._track)):return False
        self.stop()
        self._selected=identity
        self._selected_attempt=0
        self._message='Pilota selezionato · 5 Start'
        self._refresh()
        return True

    @Slot(str,result=bool)
    def setMode(self, mode):
        if self.captured or self._save_state=='saving' or mode not in set(MODES)|LEGACY:return False
        if self._defer_mutation(lambda:self.setMode(mode)):return True
        self.stop()
        self._mode=mode
        if mode not in ('impara','impara_infinito','impara_sorpasso') and self._camera in ('telemetria','premi','rete'):
            self._camera='circuito';self._display='tutte'
        if learning(mode):self._store.select_objective(mode)
        if mode=='gara' and not self._participants:
            self._participants=[row['id'] for row in self._store.drivers() if race_eligible(row,self._track)][:MAX_RACE_DRIVERS]
        self._message='Scegli i partecipanti' if mode in ('gara','prova') else '5 Start'
        self._refresh()
        return True

    @Slot(int,result=bool)
    def setRaceLaps(self, laps):
        if self.captured or self._save_state=='saving' or laps not in (3,5,10):return False
        if self._defer_mutation(lambda:self.setRaceLaps(laps)):return True
        self.stop();self._race_laps=laps;self.changed.emit();return True

    @Slot(str,result=bool)
    def toggleParticipant(self, identity):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        item=self._store.driver(identity)
        if not item or (not item['policy'] and not qualified_snapshot(item,self._track)):
            self._message='Questo pilota non ha un modello salvato';self.changed.emit();return False
        if identity not in self._participants and self._mode=='gara' and not race_eligible(item,self._track):
            self._message='Questo pilota deve completare la qualifica sul circuito';self.changed.emit();return False
        if identity in self._participants:self._participants.remove(identity)
        elif len(self._participants)<MAX_RACE_DRIVERS:self._participants.append(identity)
        else:return False
        self.changed.emit()
        return True

    @Slot(str,result=bool)
    def createDriver(self, name):
        if self._drivers and all(d['profile']['algorithm'].startswith(('residual_','race_')) for d in self._drivers):
            self._message='Rosa fissa: Maestro, Crono, Memoria, Linea e Tattico';self.changed.emit();return False
        if self._storage_error or self.captured or self._save_state=='saving':return False
        self.stop()
        try:self._selected=self._store.create_driver(name)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._refresh()
        return True

    @Slot(str,result=bool)
    def createDriverPreset(self, algorithm):
        if self._drivers and all(d['profile']['algorithm'].startswith(('residual_','race_')) for d in self._drivers):
            self._message='La rosa contiene soltanto i cinque piloti verificati';self.changed.emit();return False
        if self._storage_error or self.captured or self._save_state=='saving':return False
        self.stop()
        try:self._selected=self._store.create_driver('',algorithm)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._refresh();return True

    @Slot(str,result=bool)
    def resetDriver(self, identity):
        if self._storage_error or self.captured or self._save_state=='saving' or identity!=self._selected:return False
        if self._defer_mutation(lambda:self.resetDriver(identity)):return True
        self.stop()
        try:self._store.reset_driver(identity)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._participants=[p for p in self._participants if p!=identity]
        self._save_state='idle';self._selected_attempt=0
        self._message='Apprendimento azzerato · storico conservato'
        self._refresh();return True

    @Slot(str,result=bool)
    def restartDriverCurriculum(self,identity):
        if self._storage_error or self.captured or self._save_state=='saving' or identity!=self._selected:return False
        if self._defer_mutation(lambda:self.restartDriverCurriculum(identity)):return True
        self.stop()
        try:self._store.restart_curriculum(identity)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._save_state='idle';self._selected_attempt=0
        self._message='Esercizi riavviati · pesi conservati';self._refresh();return True

    @Slot(str,result=bool)
    def resetAllDriver(self,identity):
        if self._storage_error or self.captured or self._save_state=='saving' or identity!=self._selected:return False
        if self._defer_mutation(lambda:self.resetAllDriver(identity)):return True
        self.stop()
        try:self._store.reset_all(identity)
        except (OSError,ValueError,sqlite3.Error) as error:self._message=str(error);self.changed.emit();return False
        self._participants=[p for p in self._participants if p!=identity]
        self._save_state='idle';self._selected_attempt=0
        self._message='Base e contesti azzerati · storico conservato';self._refresh();return True

    @Slot('QVariantMap',result=bool)
    def configure(self, changes):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        if self._defer_mutation(lambda:self.configure(changes)):return True
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
        return self.startSetup(None)

    def startSetup(self,draft):
        if self._storage_error or self.captured or self._save_state=='saving':return False
        from game_session import validate_draft
        try:d=validate_draft(draft if draft is not None else self._settings.current())
        except (KeyError,TypeError,ValueError) as error:
            self._message=str(error);self.changed.emit();return False
        if self._process and self._process.is_alive() and self._run_state=='paused' and d==self._settings.current():
            if not self._send({'type':'resume'}):return False
            self._timer.setInterval(16);self._run_state='starting';self._start_started=time.monotonic();self.changed.emit();return True
        academy_start=learning(d['mode'])
        if academy_start and d['profile']['algorithm'] in ('pure_pursuit','race_master'):
            self._message='Il riferimento non apprende: scegli Qualifica o Gara';self.changed.emit();return False
        if d['mode'] in ('gara','prova','campione','qualifica'):
            people={p['id']:p for p in self._drivers}
            ids=d['participants'] if d['mode'] in ('gara','prova') else [d['driver']]
            error=''
            if d['mode']=='gara' and not 2<=len(ids)<=MAX_RACE_DRIVERS:error='Schiera da due a cinque piloti qualificati'
            elif not ids:error='Scegli un pilota'
            elif d['mode']=='gara' and any(not race_eligible(people.get(i),d['track'],len(ids)) for i in ids):error='Serve un giro valido di Qualifica per ogni pilota'
            elif d['mode']=='qualifica' and not any(people.get(ids[0],{}).get(k) for k in ('candidate','policy')):error='Salva prima un candidato in Impara'
            if error:self._message=error;self.changed.emit();return False
        if importlib.util.find_spec('numpy') is None:
            self._message='Runtime di apprendimento non disponibile';self._run_state='error';self.changed.emit();return False
        if self._process:
            self._pending_start=d
            self.stop()
            return True
        return self._launch(d)

    def _launch(self,d):
        self.startup_diagnostics.clear()
        self._epoch=uuid.uuid4().hex
        request={'mode':d['mode'],'driver':d['driver'],'participants':d['participants'][:],
                 'academy':learning(d['mode']),'grid':d['grid'],'view':d['view'],'bots':d['bots'],'trainingSource':getattr(self._store,'objective','impara'),
                 'epoch':self._epoch,'selected':self._selected_attempt,'laps':d['laps'],'track':d['track'],'setup':d}
        try:
            if self._process_backend=='local' or d['profile'].get('learningBackend')=='sb3-skill-1':
                from game_process import spawn_role
                self._process,self._command,self._frames=spawn_role('learner',self._root,request)
            else:
                from game_session import session_main
                context=multiprocessing.get_context('spawn')
                self._command,child=context.Pipe();self._frames=context.Queue(maxsize=2)
                self._process=context.Process(target=session_main,args=(child,self._frames,str(self._root),request),daemon=False)
                try:self._process.start()
                except Exception:
                    child.close();self._process.close();self._process=None
                    raise
                child.close()
        except (OSError,ValueError,RuntimeError) as error:
            self.stop();self._fail('Avvio non riuscito: '+str(error));return False
        self._run_state='starting';self._start_started=time.monotonic();self._save_state='idle'
        self._message='Avvio…';self.changed.emit();self._timer.setInterval(33);self._timer.start()
        return True

    def _setup_ready(self,d):
        self._track=d['track'];self._selected=d['driver'];self._mode=d['mode'];self._race_laps=d['laps']
        self._participants=d['participants'];self._grid_order=d['grid'];self._training_view=d['view'];self._bots=d['bots']
        # The child already initialized paths; these are local selectors only.
        self._store.track_id=d['track']
        if learning(d['mode']):self._store.select_objective(d['mode'])
        from copy import deepcopy
        self._settings.base=deepcopy(d);self._settings.draft=deepcopy(d)
        self._settings.profiles={};self._settings.confirm=None;self._settings.message='Avvio…'

    @Slot(result=bool)
    def pause(self):
        if self._run_state not in ('running','starting'):return False
        if not self._send({'type':'pause'}):return False
        self._timer.setInterval(16)
        self._run_state='pausing';self._pause_started=time.monotonic()
        self._pause_ack_started=None
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
        self._pause_started=self._start_started=None;self._pause_ack_started=None
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
        panels=['telemetria','premi','rete']
        if self._camera in panels:
            self._camera=panels[(panels.index(self._camera)+delta)%len(panels)]
            self.changed.emit();return
        count=max(1,self._scene.get('meta',{}).get('count',1))
        self._selected_attempt=(self._selected_attempt+delta)%count
        self._send({'type':'select','index':self._selected_attempt})
        self.changed.emit()

    @Slot(int)
    def displayStep(self, delta):
        if self._run_state!='running':return
        modes=['circuito','segui','duello','telemetria','sensori']
        if self._scene.get('meta',{}).get('count',1)<2:modes.remove('duello')
        if self._track!='oval-1' or self._mode not in ('impara','impara_infinito','impara_sorpasso'):modes.remove('telemetria')
        camera='telemetria' if self._camera in ('premi','rete') else self._camera
        self._camera=modes[((modes.index(camera) if camera in modes else 0)+delta)%len(modes)]
        self._display='sensori' if self._camera=='sensori' else 'tutte'
        self.changed.emit()

    def _poll(self):
        if not self._process:return
        if self._closing:
            self._poll_stop()
            return
        if self._command:
            try:
                while self._command.poll():
                    message=self._command.recv()
                    if message.get('session')!=self._epoch:continue
                    kind=message['type']
                    if kind=='startup_stage':
                        self.startup_diagnostics.append(dict(phase=message['phase'],at=message['at'],received=time.monotonic()))
                    elif kind=='setup':self._setup_ready(message['setup'])
                    elif kind=='ready':
                        self._timer.setInterval(33)
                        self._run_state='running';self._start_started=None;self._message=MODES.get(self._mode,(self._mode,''))[0]
                        self.operationFinished.emit('start',True,'')
                        self._refresh()
                    elif kind=='pause_pending':
                        self._pause_started=None;self._pause_ack_started=time.monotonic()
                        self._save_state='saving';self._message='Pausa · attesa operazioni in corso…'
                    elif kind=='paused':
                        self._pause_ack_started=None
                        self._timer.setInterval(250)
                        self._run_state='paused';self._pause_started=None
                        self._save_state='saving' if learning(self._mode) else 'idle';self._message=message.get('message') or 'In pausa'
                        self.operationFinished.emit('pause',True,'')
                    elif kind=='saved':self._ack_save(message)
                    elif kind=='save_failed':self._save_state='error';self._message='Salvataggio non riuscito: '+message['message'];self.operationFinished.emit('save',False,message['message'])
                    elif kind=='qualification':self._refresh()
                    elif kind=='finished':self._run_state='finished';self._message='Gara conclusa' if self._mode=='gara' else 'Prova conclusa';self._refresh()
                    elif kind=='error':self._fail(message['message'])
                    self.changed.emit()
            except (EOFError,OSError):pass
        newest=None
        try:
            while True:
                frame=self._frames.get_nowait()
                if frame.get('session')==self._epoch and frame.get('sequence',0)>self._scene.get('sequence',0):newest=frame
        except (queue.Empty,EOFError,OSError):pass
        if newest:
            newest['receivedMs']=time.monotonic()*1000
            self._scene=newest;self.sceneChanged.emit()
        now=time.monotonic()
        if self._release_after_save and self._run_state not in ('starting','running','pausing') and self._save_state!='saving':
            self.stop();return
        pending=getattr(self,'_pause_ack_started',None)
        if (self._pause_started and now-self._pause_started>10) or (pending and now-pending>10):
            self._process.terminate();self._fail('Sessione interrotta · checkpoint precedente')
        if self._start_started and now-self._start_started>20:
            self._process.terminate();self._fail('Avvio non riuscito')
        if not self._process.is_alive():
            if self._run_state not in ('error','idle','finished'):
                self._fail('Worker interrotto · checkpoint precedente')
            self._timer.stop()

    @Slot()
    def stop(self):
        if self._process and self._process.is_alive():
            if not self._closing:
                self._closing=True;self._stop_started=time.monotonic();self._stop_stage=0
                self._send({'type':'stop'})
                self._run_state='pausing';self._message='Chiusura e salvataggio…'
                self._timer.setInterval(20);self._timer.start();self.changed.emit()
            return
        self._finish_stop()

    def _poll_stop(self):
        try:
            while self._command and self._command.poll():
                message=self._command.recv()
                if message.get('session')==self._epoch:
                    if message.get('type')=='save_failed':
                        self._save_state='error';self._message=message['message'];self._pending_start=self._pending_mutation=None
                    elif message.get('type')=='saved':
                        self._ack_save(message)
        except (EOFError,OSError):pass
        if not self._process.is_alive():self._finish_stop();return
        elapsed=time.monotonic()-self._stop_started
        if elapsed>10 and self._stop_stage==0:
            self._process.terminate();self._stop_stage=1;self._pending_start=self._pending_mutation=None
            self._save_state='error';self._message='Worker interrotto · checkpoint precedente conservato'
        elif elapsed>10.5 and self._stop_stage==1:
            self._process.kill();self._stop_stage=2;self._pending_start=None

    def _ack_save(self,message):
        automatic=message.get('automatic',False)
        if not automatic or self._run_state in ('starting','running'):self._save_state='saved'
        self._refresh()
        if not automatic:self.operationFinished.emit('save',True,'')

    def _finish_stop(self):
        if self._process:
            self._process.join(0);self._process.close();self._process=None
        if self._command:self._command.close();self._command=None
        if self._frames:self._frames.cancel_join_thread();self._frames.close();self._frames=None
        self._timer.stop()
        self._closing=False
        self._run_state='idle';self._pause_started=self._start_started=None;self._pause_ack_started=None
        self._release_after_save=False
        self._scene={'cars':[],'sensors':[],'sequence':0,'engine':'CPU','meta':{}}
        self.sceneChanged.emit();self.changed.emit()
        pending=self._pending_start;self._pending_start=None
        if pending is not None:self._launch(pending)
        mutation=self._pending_mutation;self._pending_mutation=None
        if mutation is not None:mutation()

    def _defer_mutation(self,operation):
        if self._process is None:return False
        self._pending_mutation=operation
        self.stop()
        return True

    def _apply_stopped_setup(self,draft):
        if self.applySetup(draft):self._settings.open(True)

    def close(self):
        self._metadata_closed=True
        if self._metadata_reader:self._metadata_reader.close()
        self._pending_start=None
        self._pending_mutation=None
        self.stop()
        # Terminal application teardown only; interactive commands never join.
        if self._process:
            self._process.join(10.)
            if self._process.is_alive():self._process.terminate();self._process.join(.3)
            if self._process.is_alive():self._process.kill();self._process.join(.3)
            if not self._process.is_alive():self._finish_stop()
