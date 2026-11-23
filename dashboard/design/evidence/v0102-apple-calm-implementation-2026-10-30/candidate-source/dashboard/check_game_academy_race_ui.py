"""Frozen reference races in the new physics; no claim of neural competence."""
import argparse,json,os,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')

def main():
    from theme_fixture_support import isolate_process,LegacyHarness
    p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path,required=True)
    p.add_argument('--quick',action='store_true');args=p.parse_args()
    private,base=isolate_process();h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal','game':True})
    args.capture_dir.mkdir(parents=True,exist_ok=True)
    def wait(condition,seconds=25):
        end=time.monotonic()+seconds
        while not condition() and time.monotonic()<end:h.pump(10)
        assert condition(),h.game.snapshot
    def capture(name):
        h.pump(40);assert h.window.grabWindow().save(str(args.capture_dir/(name+'.png')))
    try:
        assert h.game.setTrack('technical-1')
        pilots=[]
        for _ in range(4):
            identity=h.game._store.create_driver(algorithm='pure_pursuit')
            h.game._store.activate_academy(identity);pilots.append(identity)
        h.game._refresh();h.expression('familyId="game"');h.wait_ready()
        original={i:h.game._store.driver(i) for i in pilots};races=[]
        for count in (2,4):
            h.game.stop();assert h.game.setMode('gara');h.game._participants=pilots[:count]
            h.game._race_laps=3;h.game.changed.emit();assert h.game.start()
            wait(lambda:h.game.snapshot['runState']=='running' and len(h.game.scene['cars'])==count)
            assert h.game.scene['meta']['physics']=='f2-1';capture(str(count)+'-grid')
            ids={r['id'] for r in h.game.scene['cars']};last={};resets=0;start=time.monotonic()
            while time.monotonic()-start<(5 if args.quick else 180) and h.game.snapshot['runState']!='finished':
                h.pump(10);assert not h.messages,h.messages
                assert h.game.snapshot['runState'] in ('running','finished'),h.game.snapshot
                cars=h.game.scene['cars'];assert {r['id'] for r in cars}==ids
                for r in cars:
                    if r['id'] in last and r['progress']<last[r['id']]-1:resets+=1
                    last[r['id']]=r['progress']
            assert resets==0
            if args.quick:
                assert h.game.pause();wait(lambda:not h.game.captured)
                results=[]
            else:
                assert h.game.snapshot['runState']=='finished',h.game.snapshot
                results=h.game.snapshot['leaderboard']['race']
                assert len(results)==count and all(r['status']=='arrivato' and r['lap']==3 for r in results),results
            capture(str(count)+'-end');races.append({'participants':count,'laps':3,'results':results,'respawns':resets})
        assert {i:h.game._store.driver(i) for i in pilots}==original
        report={'status':'passed','platform':os.environ['QT_QPA_PLATFORM'],'window':[960,640],
                'scope':'frozen geometric references; not trained neural pilots','races':races,
                'complete':not args.quick,'driversUnchanged':True,'qmlWarnings':h.messages}
        (args.capture_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    finally:h.close();private.cleanup()

if __name__=='__main__':main()
