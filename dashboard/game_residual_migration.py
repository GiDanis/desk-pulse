"""Offline, recoverable replacement of the active game store. Caller stops GUI."""
from pathlib import Path
import ctypes
from contextlib import closing
import hashlib
import json
import os
import sqlite3
import time


def inventory(root):
    root=Path(root)
    result={}
    for path in sorted(root.rglob('*')):
        if path.is_file():result[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def exchange(left,right):
    """Atomic directory exchange, including rollback after failed GUI startup."""
    libc=ctypes.CDLL(None,use_errno=True)
    rename=getattr(libc,'renameat2',None)
    if rename is None:raise RuntimeError('Scambio atomico directory non disponibile')
    if rename(-100,os.fsencode(left),-100,os.fsencode(right),2):
        err=ctypes.get_errno();raise OSError(err,os.strerror(err))


def prepare(root):
    from game_store import GameStore
    root=Path(root);stage=root.with_name(root.name+'-residual-stage-'+str(time.time_ns()))
    store=GameStore(stage)
    assert [d['name'] for d in store.drivers()]==['Maestro','Crono','Memoria','Linea','Tattico']
    return stage


def install(root,stage,backup):
    """Preserve the old full directory externally; no destructive reset script."""
    root,stage,backup=map(Path,(root,stage,backup))
    if backup.exists():raise ValueError('Backup già presente')
    with closing(sqlite3.connect('file:'+str(stage/'game.sqlite')+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Nuovo archivio non integro')
        names=[r[0] for r in db.execute('SELECT name FROM drivers ORDER BY number')]
        if names!=['Maestro','Crono','Memoria','Linea','Tattico']:raise ValueError('Nuova rosa non valida')
    before=inventory(root);os.sync();exchange(root,stage)
    try:
        backup.parent.mkdir(parents=True,exist_ok=True)
        stage.rename(backup);os.sync()
        if inventory(backup)!=before:raise RuntimeError('Backup differente dall’archivio originale')
    except BaseException:
        exchange(root,backup if backup.exists() else stage)
        raise
    return dict(version='residual-migration-1',backup=str(backup),oldFiles=len(before),
        originalHashesPreserved=True,roster=names,atomicExchange=True)
