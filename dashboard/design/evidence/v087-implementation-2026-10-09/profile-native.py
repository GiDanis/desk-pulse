"""Attribute residual CPU cost separately from comparable timing measurements."""
from pathlib import Path
import json,pstats,subprocess,time
H=Path('/var/lib/smartpc-dashboard');P=H/'v087-performance-proof';S=H/'smartpc-v087-performance-staging/project';D=S/'dashboard'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','PYTHONPATH='+str(D),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 with (P/'native-profile.txt').open('w') as out:subprocess.run(['runuser','-u','smartpc','--','env',*env,'python3','-m','cProfile','-o',str(P/'candidate-apple.pstats'),str(D/'verify_performance_ui.py'),'--theme','apple','--bundle-project',str(S/'theme-projects/apple-calm/bundle'),'--output',str(P/'profiled-apple.json')],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=180)
 report=json.loads((P/'profiled-apple.json').read_text());assert not report['qml_messages'] and not report['network_attempts']
 stats=pstats.Stats(str(P/'candidate-apple.pstats'))
 entries=[{'file':f,'line':line,'function':name,'primitiveCalls':cc,'calls':nc,'selfSeconds':tt,'cumulativeSeconds':ct} for (f,line,name),(cc,nc,tt,ct,callers) in stats.stats.items()]
 (P/'native-profile-summary.json').write_text(json.dumps({'status':'passed','scope':'cProfile CPU attribution only; timings intentionally excluded from A/B comparison','totalSeconds':stats.total_tt,'topCumulative':sorted(entries,key=lambda r:r['cumulativeSeconds'],reverse=True)[:35],'topSelf':sorted(entries,key=lambda r:r['selfSeconds'],reverse=True)[:35]},indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
