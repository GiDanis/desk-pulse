"""Qualify staged 0.8.7 using real EGLFS, then restore the running kiosk."""
import hashlib,json,subprocess,time
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');P=H/'v087-opening-proof';S=H/'smartpc-v087-opening-staging';D=S/'project/dashboard'
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','PYTHONPATH='+str(D),'SMARTPC_TEST_OPTIONAL_LINT=1']
egl=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
software=['QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software']
def run(args,name,graphics=software,timeout=240):
 print('Qualifying '+name,flush=True)
 with (P/(name+'.txt')).open('w') as out:subprocess.run(['runuser','-u','smartpc','--','env',*env,*graphics,'python3',*map(str,args)],stdout=out,stderr=subprocess.STDOUT,check=True,timeout=timeout)
manifest=json.loads((S/'runtime/release-manifest.json').read_text());assert manifest['version']=='0.8.7-rc.2'
for name,digest in manifest['sha256'].items():
 for root in (S/'runtime',D):assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
assert 'ActiveState=active' in subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=ActiveState'],text=True)
# Offscreen matrix does not need exclusive display ownership.
preflight=P/'native-theme-preflight.json'
if preflight.exists():
 report=json.loads(preflight.read_text());assert report['result']['status']=='passed' and report['result']['renderers']==1098
 from sys import path
 path.insert(0,str(D))
 from theme_bundle import validate_project
 assert validate_project(S/'project/theme-projects/apple-calm/bundle')['digest']==report['digest']
else:
 run([P/'native-preflight.py'],'native-preflight',timeout=650)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for script in ['check_theme_api_runtime.py','check_theme_bundle.py','check_theme_service_recovery.py','check_dashboard_summary.py']:
  run([D/script],'native-'+script[:-3])
 run([P/'check-cache-pc.py','--bundle-project',S/'project/theme-projects/apple-calm/bundle','--output',P/'native-cache.json'],'native-cache',egl)
 cache=json.loads((P/'native-cache.json').read_text());assert cache['status']=='passed' and cache['platform']=='eglfs'
 profiles=[]
 for theme,palette in [('base','day'),('functional','night'),('apple','day'),('apple','night')]:
  name='native-'+theme+'-'+palette
  run([D/'check_view_organization_ui.py','--theme',theme,'--palette',palette,'--capture-dir',P/name],name,egl)
  report=json.loads((P/name/'report.json').read_text());assert report['status']=='passed' and report['platform']=='eglfs' and not report['qmlWarnings'] and report['serieAAllTenGamesAccessible'] and report['favouriteRouteSeparated']
  profiles.append(name)
 run([D/'check_settings_theme_ui.py','--capture-dir',P/'native-settings'],'native-settings',egl)
 settings=json.loads((P/'native-settings/report.json').read_text());assert settings['status']=='passed'
 results={}
 for theme,motion,extra in [('apple','off',True),('base','off',False),('apple','normal',True)]:
  name='candidate-'+theme+'-'+motion
  args=[D/'verify_opening_ui.py','--theme',theme,'--motion',motion,'--bundle-project',S/'project/theme-projects/apple-calm/bundle','--output',P/(name+'.json')]

  run(args,name,egl)
  report=json.loads((P/(name+'.json')).read_text());assert report['status']=='passed' and report['platform']=='eglfs' and not report['network_attempts'] and not report['qml_messages'],report.get('qml_messages')
  results[name]=report['statistics'];print(json.dumps({'benchmark':name,'statistics':report['statistics']}),flush=True)
 report={'status':'passed','profiles':profiles,'settingsThemeTransactions':True,'benchmarks':results,'manifestSha256':hashlib.sha256((S/'runtime/release-manifest.json').read_bytes()).hexdigest(),'files':len(manifest['sha256']),'scope':'Native EGLFS; synthetic input/providers; no optical or live feed claims','time':time.time()}
 (P/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 print(subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=ActiveState,SubState,NRestarts'],text=True),flush=True)
