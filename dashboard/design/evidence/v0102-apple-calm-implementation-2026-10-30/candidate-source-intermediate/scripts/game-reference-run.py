"""Run a lab command against a frozen source tree, isolated from later edits."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,time

COMMANDS=('prepare','train','refit','evaluate','collect','stabilize','sensors','skills','install','adapter','intent','maneuver','coverage','cycle','memory','factory','refine-factory','mix','race','demonstrations','critic')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job',type=Path,required=True);p.add_argument('command',choices=COMMANDS)
    p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args()
    a.job=a.job.resolve();snapshot=a.job/'source';source=Path(__file__).resolve().parents[1]
    if not snapshot.exists():
        temporary=a.job/'source.tmp';temporary.mkdir(parents=True)
        members=[*source.joinpath('dashboard').glob('game*.py'),*source.joinpath('dashboard').glob('game*.json'),
            *source.joinpath('dashboard/game_lab').glob('*.py'),*source.joinpath('dashboard/game-tracks').rglob('*.json'),
            *source.joinpath('scripts').glob('game-reference-*.py')]
        native=source/'dashboard/libsmartpc_game_native.so'
        if native.exists():members.append(native)
        for f in members:
            dest=temporary/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
        files={str(f.relative_to(temporary)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(temporary.rglob('*')) if f.is_file()}
        (temporary/'source-manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
        temporary.replace(snapshot)
    manifest=json.loads((snapshot/'source-manifest.json').read_text())
    for name,sha in manifest['files'].items():
        if hashlib.sha256((snapshot/name).read_bytes()).hexdigest()!=sha:raise ValueError('Frozen source changed: '+name)
    arguments=a.arguments[1:] if a.arguments[:1]==['--'] else a.arguments
    env=dict(os.environ,PYTHONPATH=str(snapshot/'dashboard'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    command=[sys.executable,str(snapshot/'scripts'/('game-reference-'+a.command+'.py')),*arguments]
    started=time.time();result=subprocess.run(command,cwd=snapshot,env=env)
    receipt=dict(command=a.command,arguments=arguments,started=started,finished=time.time(),exitCode=result.returncode,
        python=sys.executable,sourceManifestSha256=hashlib.sha256((snapshot/'source-manifest.json').read_bytes()).hexdigest())
    with (a.job/'runs.jsonl').open('a') as stream:stream.write(json.dumps(receipt,sort_keys=True)+'\n')
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
