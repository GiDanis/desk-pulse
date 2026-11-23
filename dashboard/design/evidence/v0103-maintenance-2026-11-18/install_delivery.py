"""Install only the qualified maintenance delta, with a verified external rollback."""
from pathlib import Path
import json,os,shutil,subprocess,sys,time
from prepare_delivery import W,H,R,B,run,sha,write,inventory,verify

D=H/'.local/share/SmartPC/SmartPC'
sys.path.insert(0,str(W/'test-project/dashboard'))
from soak import service_state,health_record,gui_identity

def ready(expected):
    state=service_state();pid=int(state['MainPID']);health=health_record(pid,D)
    assert state['ActiveState']=='active' and state['SubState']=='running' and state['NRestarts']=='0'
    gui=gui_identity(pid,health)
    assert health['selection']==expected and health.get('pending') is None
    return state,health,gui

def main():
    assert os.geteuid()==0
    os.umask(0o077)
    candidate=json.loads((W/'candidate.json').read_text())
    backup=json.loads((B/'backup-verification.json').read_text())
    external=json.loads((W/'external-backup.json').read_text())
    assert external['status']=='verified' and external['archiveSha256']==backup['archiveSha256']
    assert json.loads((W/'arm-checks/checks.json').read_text())['status']=='passed'
    for theme in ('base','functional','apple'):
        folder='base-final' if theme=='base' else theme
        native=json.loads((W/'eglfs'/folder/'report.json').read_text())
        assert native['status']=='passed' and not native['qmlWarnings'],theme
        assert native['callbacks']>=100 and native['poseTicks']>=100,theme+' insufficient moving samples'
    assert subprocess.run(['systemctl','is-active','smartpc-dashboard'],capture_output=True,text=True).stdout.strip()=='inactive'
    verify(R,candidate['baselineManifestSha256']);verify(W/'runtime',candidate['runtimeManifestSha256'])
    before=json.loads((B/'before-private.json').read_text());frozen=inventory(B/'pre-install-private.json')
    for field in ('databases','gameArtifacts','preferenceHashes','fishIds','visitIds','theme'):
        assert before[field]==frozen[field],field+' changed during isolated qualification'
    unit=Path('/etc/systemd/system/smartpc-fan-ownership.service');script=Path('/usr/local/libexec/smartpc-fan-ownership')
    assert not unit.exists() and not script.exists(),'Existing fan policy must not be overwritten'
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();moved=False;fan=False
    try:
        assert R.stat().st_dev==(W/'runtime').stat().st_dev
        run('chown','-R','root:root',W/'runtime')
        R.rename(B/'previous-runtime');moved=True;(W/'runtime').rename(R)
        shutil.copy2(W/'os/smartpc-fan-ownership',script);script.chmod(0o755)
        shutil.copy2(W/'os/smartpc-fan-ownership.service',unit);unit.chmod(0o644)
        fan=True
        run('systemctl','daemon-reload');run('systemctl','enable','--now',unit.name)
        assert (Path('/sys/class/gpio/gpio101/value')).read_text().strip()=='1'
        assert not Path('/sys/bus/platform/drivers/pwm-fan/soc@3000000:pwm-fan').exists()
        verify(R,candidate['runtimeManifestSha256']);os.sync()
        run('systemctl','start','smartpc-dashboard')
        deadline=time.monotonic()+75;last=None;result=None;issue=None
        while time.monotonic()<deadline:
            try:
                result=ready(candidate['theme'])
                if last is not None and result[1]['time']>last:break
                last=result[1]['time']
            except (AssertionError,OSError,ValueError,KeyError,IndexError) as error:issue=type(error).__name__
            time.sleep(1)
        else:raise RuntimeError('Fresh ready GUI did not appear: '+str(issue))
        state,health,gui=result
        after=inventory(B/'after-private.json')
        for field in ('gameArtifacts','preferenceHashes','fishIds','visitIds','theme'):
            assert before[field]==after[field],field+' was not preserved'
        assert before['databases']['game']==after['databases']['game'],'Game database changed'
        assert before['databases']['aquarium']==after['databases']['aquarium'],'Aquarium database changed'
        environment=dict(p.decode().split('=',1) for p in (Path('/proc')/str(gui[0])/'environ').read_bytes().split(b'\0') if b'=' in p)
        profile={k:environment.get(k) for k in ('QT_QPA_PLATFORM','QT_QPA_EGLFS_INTEGRATION','QSG_RHI_BACKEND','QT_DISABLE_SHADER_DISK_CACHE','LD_PRELOAD','SMARTPC_AQUARIUM_RENDERER')}
        assert profile['QT_QPA_PLATFORM']=='eglfs' and profile['QSG_RHI_BACKEND']=='opengl'
        assert profile['QT_DISABLE_SHADER_DISK_CACHE']=='1' and profile['LD_PRELOAD']==str(R/'libsmartpc_egl_context_bridge.so')
        invocation=subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','InvocationID','--value'],text=True).strip()
        journal=subprocess.check_output(['journalctl','_SYSTEMD_INVOCATION_ID='+invocation,'--no-pager','-o','cat'],text=True)
        (B/'installed-journal-private.txt').write_text(journal)
        warnings=[line for line in journal.splitlines() if any(s in line for s in ('ReferenceError:','TypeError:','Cannot assign','Unable to assign','QQmlApplicationEngine failed','failed to create OpenGL','Failed to initialize','Binding loop detected'))]
        assert not warnings,'QML/graphics warning in new service'
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
        report={'status':'installed','version':candidate['version'],'runtimeManifestSha256':candidate['runtimeManifestSha256'],
            'runtimeFiles':candidate['runtimeFiles'],'deltaFiles':candidate['deltaFiles'],'service':state,'guiPid':gui[0],
            'theme':candidate['theme'],'freshReadyHeartbeat':True,'heartbeatContext':health.get('context'),
            'profile':profile,'sameBoot':True,'rebootPerformed':False,'qmlGraphicsWarnings':warnings,
            'gameDatabaseAndArtifactsPreserved':True,'aquariumDatabasePreserved':True,
            'preferencesPreserved':len(before['preferenceHashes']),'gameArtifacts':len(before['gameArtifacts']),
            'fishIdentitiesPreserved':len(before['fishIds']),'visitsPreserved':len(before['visitIds']),
            'fan':'Stock GPIO101 high/full speed retained; duplicate PWM controller detached',
            'rollbackRuntime':str(B/'previous-runtime'),'privateBackup':str(B),'externalBackupVerified':True,
            'freeBytes':shutil.disk_usage(H).free,'scope':'Installed; targeted PC/ARM/EGLFS. Physical fan/panel/input and long soak remain distinct.'}
        write(W/'installation.json',report);write(B/'installation.json',report)
        print(json.dumps(report),flush=True)
    except BaseException:
        run('systemctl','stop','smartpc-dashboard')
        if fan:
            subprocess.run(['systemctl','disable','--now',unit.name],check=False)
            subprocess.run([str(script),'restore'],check=False)
            unit.unlink(missing_ok=True);script.unlink(missing_ok=True);run('systemctl','daemon-reload')
        if moved:
            if R.exists():R.rename(B/('failed-runtime-'+str(time.time_ns())))
            (B/'previous-runtime').rename(R)
            failed=B/('failed-state-'+str(time.time_ns()));failed.mkdir()
            for name in json.loads((B/'selected-roots-private.json').read_text()):
                original=Path(name)
                if original==R:continue
                if original.exists():
                    target=failed/str(original).lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);original.rename(target)
                original.parent.mkdir(parents=True,exist_ok=True)
                run('cp','-a',B/'snapshot'/str(original).lstrip('/'),original)
        os.sync();run('systemctl','start','smartpc-dashboard')
        write(B/'rollback-result.json',{'status':'restored','baseline':candidate['baselineManifestSha256']})
        raise

if __name__=='__main__':main()
