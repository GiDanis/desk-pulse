"""Observe the actual GUI, its supervisor and helpers without sending input."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def service_state():
    result=subprocess.check_output(['systemctl','show','smartpc-dashboard',
        '-p','MainPID','-p','ActiveState','-p','SubState','-p','NRestarts','-p','ControlGroup'],text=True)
    return dict(line.split('=',1) for line in result.splitlines())


def proc_stat(pid,proc=Path('/proc')):
    fields=(proc/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'parent':int(fields[1]),'start':fields[19],
            'cpuTicks':int(fields[11])+int(fields[12]),'threads':int(fields[17])}


def gui_identity(supervisor,health,*,proc=Path('/proc'),now=None):
    if not isinstance(health,dict) or type(health.get('pid')) is not int:
        raise ValueError('GUI heartbeat missing identity')
    gui=health['pid']
    stat=proc_stat(gui,proc)
    if stat['start']!=str(health.get('processStart','')):
        raise ValueError('GUI PID/start token mismatch')
    command=(proc/str(gui)/'cmdline').read_bytes().split(b'\0')
    if len(command)<2 or not command[1].endswith(b'/app.py'):
        raise ValueError('Heartbeat PID is not the GUI launcher')
    ancestor=gui
    for _ in range(32):
        if ancestor==supervisor:break
        if ancestor<=1:raise ValueError('GUI is outside the service process tree')
        ancestor=proc_stat(ancestor,proc)['parent']
    else:raise ValueError('GUI ancestry limit exceeded')
    age=(time.time() if now is None else now)-health.get('time',0)
    if not 0<=age<5 or health.get('ready') is not True or health.get('pending') is not None:
        raise ValueError('GUI heartbeat stale or not ready')
    return (gui,stat['start'])


def health_record(supervisor,data_root,proc=Path('/proc')):
    status=(proc/str(supervisor)/'status').read_text().splitlines()
    uid=next(line.split()[1] for line in status if line.startswith('Uid:'))
    key=hashlib.sha256(os.fsencode(str(data_root.resolve()))).hexdigest()+'.json'
    return json.loads((proc/str(supervisor)/'root/tmp'/('smartpc-theme-health-'+uid)/key).read_text())


def process_sample(pid):
    before=proc_stat(pid)
    status={line.split(':',1)[0]:line.split(':',1)[1].strip()
            for line in (Path('/proc')/str(pid)/'status').read_text().splitlines() if ':' in line}
    if status.get('State','').startswith('Z'):raise ProcessLookupError('Process has exited')
    rss=int(status['VmRSS'].split()[0])
    pss=None
    try:
        pss=next(int(line.split()[1]) for line in (Path('/proc')/str(pid)/'smaps_rollup').read_text().splitlines() if line.startswith('Pss:'))
    except (OSError,StopIteration):pass
    fds=len(list((Path('/proc')/str(pid)/'fd').iterdir()))
    after=proc_stat(pid)
    if before['start']!=after['start']:raise ValueError('Process identity changed during sample')
    return dict(before,rssKiB=rss,pssKiB=pss,fds=fds)


def read_temp():
    values={}
    for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:values[(zone/'type').read_text().strip()]=int((zone/'temp').read_text())/1000
        except (OSError,ValueError):pass
    return values


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('duration',type=float,nargs='?',default=1800)
    parser.add_argument('--interval',type=float,default=10)
    parser.add_argument('--data-root',type=Path,default=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if args.duration<=0 or args.interval<=0:parser.error('positive duration/interval required')
    start=time.monotonic();samples=deque(maxlen=10000);errors=[];initial=None;last={}
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    ticks=os.sysconf('SC_CLK_TCK')
    while time.monotonic()-start<args.duration:
        try:
            state=service_state();supervisor=int(state['MainPID'])
            if state['ActiveState']!='active' or state['SubState']!='running' or supervisor<=0:
                raise ValueError('Service is not running')
            health=health_record(supervisor,args.data_root)
            gui=gui_identity(supervisor,health)
            identity=(supervisor,proc_stat(supervisor)['start'],*gui,state['NRestarts'])
            if initial is None:initial=identity
            if identity!=initial:raise ValueError('Supervisor/GUI identity or restart count changed')
            if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=boot:raise ValueError('Boot changed')
            cgroup=Path('/sys/fs/cgroup')/state['ControlGroup'].lstrip('/')
            pids=[int(p) for p in (cgroup/'cgroup.procs').read_text().split()]
            processes=[];now=time.monotonic()
            for pid in pids:
                try:row=process_sample(pid)
                except (FileNotFoundError,ProcessLookupError):
                    if pid in (supervisor,gui[0]):raise
                    continue
                key=(pid,row['start']);previous=last.get(key)
                row['cpuPercentOneCore']=(100*(row['cpuTicks']-previous[1])/ticks/(now-previous[0])) if previous else None
                row['role']='gui' if pid==gui[0] else 'supervisor' if pid==supervisor else 'helper'
                last[key]=(now,row['cpuTicks']);processes.append(row)
            last={key:value for key,value in last.items() if key[0] in pids}
            samples.append({'elapsed_s':round(now-start,3),'time':time.time(),'processes':processes,
                'cgroupMemoryBytes':int((cgroup/'memory.current').read_text()),
                'temperaturesC':read_temp(),'healthAge_s':time.time()-health['time'],
                'ready':health['ready'],'context':health.get('context',{})})
        except (OSError,ValueError,TypeError,KeyError,IndexError,StopIteration,subprocess.CalledProcessError) as error:
            if str(error) not in errors and len(errors)<64:errors.append(str(error))
        time.sleep(min(args.interval,max(0,args.duration-(time.monotonic()-start))))
    memories=[p['rssKiB'] for s in samples for p in s['processes'] if p['role']=='gui']
    report={'status':'passed' if samples and not errors else 'failed','bootId':boot,
        'elapsed_s':round(time.monotonic()-start,3),'samples':len(samples),
        'pid_initial':initial[2] if initial else None,'guiIdentity':list(initial[2:4]) if initial else None,
        'rss_min_kib':min(memories) if memories else None,'rss_max_kib':max(memories) if memories else None,
        'errors':errors,'observations':list(samples),
        'scope':'Passive observation only; bounded to the latest 10000 samples; no physical/live qualification.'}
    encoded=json.dumps(report,indent=2)
    if args.output:args.output.write_text(encoded+'\n')
    print(encoded)
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
