"""Session validation and preparation owned by the on-demand child process.

This module has no Qt or model imports. A GUI key event only validates the
small draft; SQLite projections, profile writes and checkpoint loads are child
work. Every acknowledgement belongs to one session epoch.
"""
from copy import deepcopy


def validate_draft(draft):
    from game_catalog import TRACKS
    from game_modes import MODES, LEGACY, GRID, MAX_RACE_DRIVERS
    from game_store import validate_profile
    d=deepcopy(dict(draft))
    if d['track'] not in {t['id'] for t in TRACKS} or d['mode'] not in set(MODES)|LEGACY:
        raise ValueError('Sessione non valida')
    if not isinstance(d['driver'],str) or not d['driver']:raise ValueError('Scegli un pilota')
    d['profile']=validate_profile(d['profile'])
    if d['profile']['algorithm'].startswith(('race_','residual_')) and d['track']!='oval-1':
        raise ValueError('Nuova base da qualificare su questo circuito')
    if type(d['laps']) is not int or d['laps'] not in (3,5,10):raise ValueError('Giri non validi')
    if d['grid'] not in GRID or d['view'] not in ('pilot','attempts') or type(d['bots']) is not int or d['bots'] not in (1,2,3):
        raise ValueError('Opzioni non valide')
    ids=d['participants']
    if not isinstance(ids,list) or len(ids)>MAX_RACE_DRIVERS or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Schieramento non valido')
    return d


def prepare(root,request):
    from game_store import GameStore
    from game_modes import learning,MAX_RACE_DRIVERS
    from game_catalog import race_eligible
    d=validate_draft(request['setup'])
    store=GameStore(root,d['track'])
    people={p['id']:p for p in store.drivers()}
    if d['driver'] not in people:raise ValueError('Pilota sconosciuto')
    if any(i not in people for i in d['participants']):raise ValueError('Schieramento non valido')
    if learning(d['mode']) and d['profile']['algorithm'] in ('pure_pursuit','race_master'):
        raise ValueError('Il riferimento non apprende: scegli Qualifica o Gara')
    if d['mode']=='gara':
        if not 2<=len(d['participants'])<=MAX_RACE_DRIVERS:raise ValueError('Schiera da due a cinque piloti qualificati')
        if any(not race_eligible(people[i],d['track'],len(d['participants'])) for i in d['participants']):
            raise ValueError('Serve un giro valido di Qualifica per ogni pilota')
    if d['mode']=='qualifica' and not any(people[d['driver']].get(k) for k in ('candidate','policy')):
        raise ValueError('Salva prima un candidato in Impara')
    if learning(d['mode']):store.set_profile(d['driver'],d['profile'])
    return d


def session_main(command,frames,root,request):
    try:
        startup_stage(command,request,'validazione')
        d=prepare(root,request)
        startup_stage(command,request,'sessione')
        command.send(dict(type='setup',session=request['epoch'],setup=d))
        from game_reference_backend import selected,relay
        if selected(root,request):relay(command,frames,root,request)
        else:
            from game_worker import worker_main
            worker_main(command,frames,root,request)
    except Exception as error:
        try:command.send(dict(type='error',session=request['epoch'],message=str(error)))
        except (OSError,EOFError):pass
    finally:
        command.close()


def startup_stage(command,request,phase):
    if 'setup' not in request:return
    import time
    command.send(dict(type='startup_stage',session=request['epoch'],phase=phase,at=time.monotonic()))
