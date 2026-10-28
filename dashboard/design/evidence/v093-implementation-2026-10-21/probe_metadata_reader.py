"""Read-only real-store projection equality and main-loop responsiveness."""

def main():
    import argparse
    from contextlib import contextmanager
    import json
    import os
    from pathlib import Path
    import pickle
    import sqlite3
    import sys
    import time
    from types import SimpleNamespace
    
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sys.path.insert(0,str(a.source))
    os.environ.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    from PySide6.QtCore import QCoreApplication,QTimer
    from game import GameService
    from game_metadata import MetadataReader
    from game_dossier import dossier
    from game_store import GameStore
    
    app=QCoreApplication([])
    db=sqlite3.connect((a.root/'game.sqlite').as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    class Store(GameStore):
        def __init__(self):
            self.root=a.root
            self.policies=a.root/'policies'
            self.track_id='oval-1'
        @contextmanager
        def connect(self):yield db
    store=Store()
    drivers=store.drivers()
    proxy=SimpleNamespace(_drivers=drivers,_track=store.track_id,_store=store)
    expected={d['id']:dict(progress=GameService._progress(proxy,d),
                          dossier=dossier(store,d['id'],driver=d)) for d in drivers}
    classification=GameService._leaderboard(proxy)
    db.rollback()
    db.close()
    rows=[]
    gaps=[]
    clock=[time.perf_counter()]
    started=[0]
    request_at=[0]
    timeout=QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(app.quit)
    timeout.start(60000)
    heartbeat=QTimer()
    heartbeat.setInterval(5)
    def beat():
        now=time.perf_counter()
        gaps.append((now-clock[0])*1000)
        clock[0]=now
    heartbeat.timeout.connect(beat)
    heartbeat.start()
    def request():
        index=started[0]
        if index>=len(drivers)*2:
            app.quit()
            return
        driver=drivers[index%len(drivers)]
        started[0]+=1
        request_at[0]=time.perf_counter()
        reader.request(started[0],driver['id'],'oval-1','impara')
    def receive(result):
        before=time.perf_counter()
        assert not result.get('error'),result
        identity=result['selected']
        driver=next(d for d in result['drivers'] if d['id']==identity)
        assert driver['_progress']==expected[identity]['progress']
        assert result['dossier']==expected[identity]['dossier']
        assert result['classification']==classification
        rows.append(dict(ticket=result['ticket'],roundTripMs=(before-request_at[0])*1000,
                         payloadBytes=len(pickle.dumps(result)),projectionEqual=True))
        QTimer.singleShot(40,request)
    reader=MetadataReader(a.root,receive)
    QTimer.singleShot(20,request)
    try:app.exec()
    finally:reader.close()
    report=dict(status='passed' if len(rows)==len(drivers)*2 else 'timeout',rows=rows,
                maxMainLoopGapMs=max(gaps,default=0),heartbeatSamples=len(gaps),lastReaderStats=reader.last_stats,
                scope='Private reader, real store mode=ro, no QML/GPU/training or writes')
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    assert report['status']=='passed'

if __name__=="__main__":main()
