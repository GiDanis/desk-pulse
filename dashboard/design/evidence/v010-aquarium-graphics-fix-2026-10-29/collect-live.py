from pathlib import Path
import hashlib,json,os,pwd,re,subprocess,sys,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');R=Path('/opt/smartpc/dashboard');D=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC');label=sys.argv[1];assert label in ('preboot','postboot','postrestart','final')
s=dict(l.split('=',1) for l in subprocess.check_output(['systemctl','show','smartpc-dashboard.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True).splitlines());u=pwd.getpwnam('smartpc').pw_uid
root=Path('/proc')/s['MainPID']/'root/tmp';b=json.loads((root/('smartpc-theme-health-'+str(u))/(hashlib.sha256(os.fsencode(str(D))).hexdigest()+'.json')).read_text());assert b['ready'] and time.time()-b['time']<5
pid=b['pid'];env=dict(v.split('=',1) for v in Path('/proc/'+str(pid)+'/environ').read_bytes().decode().split('\0') if '=' in v)
lib=sorted({l.split()[-1] for l in Path('/proc/'+str(pid)+'/maps').read_text().splitlines() if any(k in l for k in ('libGLES','libEGL','PVR','egl_context_bridge'))})
gl=json.loads((root/'smartpc-rc3-native-context.json').read_text());assert gl['pid']==pid and gl['version'].startswith('OpenGL ES 3.')
assert env.get('SMARTPC_AQUARIUM_RENDERER')=='3d' and 'libsmartpc_egl_context_bridge.so' in env.get('LD_PRELOAD','') and '/usr/local/lib/libGLESv2.so' not in env.get('LD_PRELOAD','')
rows=[json.loads(l) for l in subprocess.check_output(['journalctl','-b','-u','smartpc-dashboard.service','-o','json','--no-pager'],text=True).splitlines()];messages=[r.get('MESSAGE','') for r in rows if str(r.get('_PID'))==str(pid) and isinstance(r.get('MESSAGE'),str)]
versions=[m.groups() for l in messages if (m:=re.search(r'Created OpenGL context QSurfaceFormat\(version (\d+)\.(\d+)',l))];assert versions and tuple(map(int,versions[-1]))>=(3,0)
needles=('Failed to build graphics pipeline','No GLSL shader code','Unsupported texture format','ReferenceError','TypeError','Unable to assign','Error loading QML','SIGSEGV');issues=[l for l in messages if any(n in l for n in needles)];assert not issues,issues
m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.2-rc.3' and all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
a={'status':'passed','label':label,'observedAt':time.time(),'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'version':m['version'],'runtimeFiles':len(m['sha256']),'service':s,'gui':b,'renderer':env.get('SMARTPC_AQUARIUM_RENDERER'),'profile':env.get('SMARTPC_AQUARIUM_GRAPHICS_PROFILE'),'ldPreload':env.get('LD_PRELOAD'),'nativeContext':gl,'qtRhiVersion':list(map(int,versions[-1])),'libraries':lib,'qmlGraphicsIssues':issues,'scope':'Actual installed service; software context, hashes, journal and health; not physical panel proof'}
(W/('live-'+label+'.json')).write_text(json.dumps(a,indent=2)+'\n');print(json.dumps(a),flush=True)
