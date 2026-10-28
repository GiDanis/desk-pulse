"""Persistent read-only metadata process, independent of the explicit learner.

Only the latest informational request is published. Commands and durable save
acknowledgements continue through GameService's existing worker protocol.
"""
from contextlib import contextmanager
import os
import multiprocessing
from pathlib import Path
import queue
import sqlite3
import time
from types import SimpleNamespace

from PySide6.QtCore import QObject, QTimer


def display_curriculum(state):
    if not state:return state
    # Only fields consumed by menu settings/eligibility. Full episodes, policies,
    # optimizer arrays and model snapshots remain in the read-only process/DB.
    result={key:state[key] for key in ('phase','effectiveParameters','learningMetrics',
            'tuning','rewardVersion','residualVersion','academyVersion','qualifications') if key in state}
    for key in ('champion','raceChampion'):
        if state.get(key):result[key]={'proof':state[key].get('proof',{})}
    if state.get('verifiedBest'):result['verifiedBest']=True
    return result


def _read_loop(root, requests, results):
    os.nice(10)
    os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    from game import GameService
    from game_dossier import dossier
    from game_store import GameStore

    class ReaderStore(GameStore):
        def __init__(self):
            self.root=Path(root)
            self.policies=self.root/'policies'
            self.track_id='oval-1'

        @contextmanager
        def connect(self):
            yield db

    db=sqlite3.connect((Path(root)/'game.sqlite').as_uri()+'?mode=ro',uri=True,timeout=3)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    store=ReaderStore()
    base_key=None
    projections={}
    try:
        while True:
            request=requests.get()
            if request is None:return
            ticket,selected,track,objective=request
            try:
                # A persistent connection observes commits from every writer.
                # One transaction owns the entire returned projection.
                db.execute('BEGIN')
                version=db.execute('PRAGMA data_version').fetchone()[0]
                key=(version,track,objective)
                if base_key!=key:
                    store.track_id=track
                    store.objective=objective
                    drivers=store.drivers()
                    proxy=SimpleNamespace(_drivers=drivers,_track=track,_store=store)
                    classification=GameService._leaderboard(proxy)
                    displayed=[]
                    for driver in drivers:
                        compact=dict(driver,_progress=GameService._progress(proxy,driver))
                        # Evaluation episodes are large private facts. The GUI
                        # receives their complete display projection, not replay.
                        for field in ('curriculum','policy_curriculum'):
                            if field in compact:compact[field]=display_curriculum(compact[field])
                        displayed.append(compact)
                    projections={}
                    base_key=key
                selected=selected or next((d['id'] for d in drivers if d['profile']['algorithm']!='race_master'),drivers[0]['id'] if drivers else '')
                if selected not in projections:
                    selected_driver=next((d for d in drivers if d['id']==selected),None)
                    if len(projections)>=16:projections.pop(next(iter(projections)))
                    projections[selected]=dict(selected=selected,drivers=displayed,
                        classification=classification,dossier=dossier(store,selected,driver=selected_driver))
                db.rollback()
                results.put(dict(projections[selected],ticket=ticket))
            except Exception as error:
                db.rollback()
                base_key=None
                results.put(dict(ticket=ticket,error=str(error)))
    finally:
        db.close()


class MetadataReader(QObject):
    def __init__(self, root, receive, parent=None,*,backend='spawn'):
        super().__init__(parent)
        self.root=str(root)
        self.backend=backend
        self.receive=receive
        self.process=None
        self.requests=self.results=None
        self.pending=None
        self.inflight=None
        self.closed=False
        self.last_stats={}
        self.timer=QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._poll)

    def request(self, ticket, selected, track, objective):
        if self.closed:return
        self.pending=(ticket,selected,track,objective)
        # Spawn after construction/engine loading, never from a property getter.
        self.timer.start()

    def _poll(self):
        if self.closed:return
        if self.process is None:
            started=time.monotonic()
            try:
                if self.backend=='local':
                    from game_process import spawn_role,ParentRequests,ParentResults
                    self.process,link,_=spawn_role('metadata',self.root)
                    self.requests=ParentRequests(link);self.results=ParentResults(link)
                else:
                    context=multiprocessing.get_context('spawn')
                    self.requests=context.Queue(maxsize=1);self.results=context.Queue(maxsize=1)
                    self.process=context.Process(target=_read_loop,args=(self.root,self.requests,self.results),name='smartpc-metadata',daemon=True)
                    self.process.start()
            except (OSError,ValueError,RuntimeError) as error:
                ticket=self.pending[0]
                self.receive(dict(ticket=ticket,error='Avvio metadati non riuscito: '+str(error)))
                self.close();return
            self.last_stats['spawnMs']=(time.monotonic()-started)*1000
        if self.inflight is not None:
            before=time.perf_counter()
            try:
                result=self.results.get_nowait()
            except (queue.Empty,EOFError,OSError):
                if not self.process.is_alive():
                    ticket=self.pending[0] if self.pending else self.inflight[0]
                    self.receive(dict(ticket=ticket,error='Reader metadati interrotto'))
                    self.close()
                return
            self.inflight=None
            self.last_stats['receiveMs']=(time.perf_counter()-before)*1000
            if self.pending is None:
                before=time.perf_counter()
                self.receive(result)
                self.last_stats['publishMs']=(time.perf_counter()-before)*1000
        if self.pending is not None:
            self.inflight=self.pending
            self.pending=None
            try:self.requests.put_nowait(self.inflight)
            except (OSError,EOFError,ValueError) as error:
                self.receive(dict(ticket=self.inflight[0],error='Metadati interrotti: '+str(error)))
                self.close();return
        elif self.inflight is None:
            self.timer.stop()

    def close(self):
        self.closed=True
        self.timer.stop()
        if self.process is not None:
            # This helper never writes; cancelling a read cannot lose a commit.
            if self.process.is_alive():self.process.terminate();self.process.join(.5)
            if self.process.is_alive():self.process.kill();self.process.join(.5)
            self.process.close()
            for channel in (self.requests,self.results):
                if channel:channel.cancel_join_thread();channel.close()
            self.process=None
