"""Lightweight relay to the isolated reference learner; no Torch imports."""
from pathlib import Path
import os,queue,time

BACKEND='sb3-skill-1'


def qualified_ancestry(store,policy,release):
    from game_residual import key
    if release.get('qualified') is not True:return False
    seen=set()
    for _ in range(32):
        digest=key(policy)
        if digest in release.get('policies',[]):return True
        parent=(policy.get('origin') or {}).get('baseHash')
        if not parent or parent in seen:return False
        seen.add(parent)
        try:policy=store.load(parent)
        except (OSError,ValueError):return False
    return False


def factory_policy(store,profile):
    from game_temporal import TemporalPolicy
    release=store.reference_release()
    digest=release.get('basesByMethod',{}).get(profile['algorithm'])
    if release.get('qualified') is not True or digest not in release.get('policies',[]):
        raise ValueError('Base qualificata del metodo non disponibile')
    policy=store.load(digest);TemporalPolicy(policy)
    if policy['hidden']!=profile['hidden'] or (policy.get('origin') or {}).get('backend')!=BACKEND:
        raise ValueError('Base qualificata incompatibile')
    return policy


def selected(root,request):
    from game_modes import learning
    if not learning(request['mode']):return False
    from game_store import GameStore
    store=GameStore(root,request.get('track','oval-1'));person=store.driver(request['driver'])
    digest=person.get('candidate') or person.get('policy')
    return bool(digest and (store.load(digest).get('origin') or {}).get('backend')==BACKEND)


def relay(command,frames,root,request):
    from game_process import spawn_role
    interpreter=Path(os.environ.get('SMARTPC_GAME_LEARNER_PYTHON',str(Path.home()/'pilot-learner-runtime/bin/python')))
    if not interpreter.is_file():raise ValueError('Ambiente di apprendimento separato non disponibile')
    process,link,source=spawn_role('reference',root,request,interpreter=str(interpreter))
    try:
        while True:
            while command.poll():link.send(command.recv())
            while link.poll():command.send(link.recv())
            try:
                packet=source.get_nowait()
                try:frames.put_nowait(packet)
                except queue.Full:
                    try:frames.get_nowait();frames.put_nowait(packet)
                    except (queue.Full,queue.Empty):pass
            except queue.Empty:pass
            if not process.is_alive():
                while link.poll():command.send(link.recv())
                if process.exitcode:raise RuntimeError('Processo di apprendimento interrotto')
                break
            time.sleep(.005)
    except (EOFError,BrokenPipeError):
        if process.is_alive():
            try:link.send({'type':'stop'})
            except (EOFError,OSError):pass
            process.join(8)
    finally:
        if process.is_alive():process.terminate();process.join(1)
        if process.is_alive():process.kill();process.join(1)
        process.close();link.close()
