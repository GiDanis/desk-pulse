"""Verify changed boot, fresh GUI, installed bytes and retained user settings."""
import hashlib,json,subprocess,time
from pathlib import Path
from PySide6.QtCore import QSettings
P=Path('/var/lib/smartpc-dashboard/v087-performance-proof');H=Path('/var/lib/smartpc-dashboard')
before=json.loads((P/'baseline-health.json').read_text());pre=json.loads((P/'pre-reboot-health.json').read_text());after=json.loads((P/'reboot-health.json').read_text());receipt=json.loads((P/'install-receipt.json').read_text())
assert before['bootId']!=after['bootId']
assert after['version']==receipt['version']=='0.8.7-rc.1' and after['files']==514 and not after['manifestMismatches']
assert hashlib.sha256(Path('/opt/smartpc/dashboard/release-manifest.json').read_bytes()).hexdigest()==receipt['manifestSha256']
assert after['service']['ActiveState']=='active' and after['service']['SubState']=='running' and after['service']['NRestarts']=='0'
assert 0<=time.time()-after['time']<15
hb=after['guiHeartbeat'];assert hb and hb['ready'] and 0<=hb['ageSeconds']<15 and hb['pending'] is None
assert hb['selection']==after['activeTheme']==receipt['activeTheme']
assert after['preferenceHashes']==before['preferenceHashes']
assert after['allPreferenceHashes']==pre['allPreferenceHashes']
old=QSettings(str(Path(receipt['backup'])/'config/SmartPC/Dashboard.conf'),QSettings.Format.IniFormat);new=QSettings(str(H/'.config/SmartPC/Dashboard.conf'),QSettings.Format.IniFormat)
a=json.loads(old.value('appearance/config','{}'));b=json.loads(new.value('appearance/config','{}'))
assert {k:v for k,v in a.items() if k!='bundleRevision'}=={k:v for k,v in b.items() if k!='bundleRevision'}
assert b['bundleRevision']==receipt['activeTheme']
c=json.loads(old.value('appearance/themeOverrides','{}'));d=json.loads(new.value('appearance/themeOverrides','{}'));prefix='studio.applecalm@';identity=receipt['activeTheme'];target=prefix+identity['version']+'#'+identity['digest']
assert {k:v for k,v in c.items() if not k.startswith(prefix)}=={k:v for k,v in d.items() if not k.startswith(prefix)}
assert d.get(target)==a['overrides']
journal=subprocess.check_output(['sudo','-n','journalctl','-b','-u','smartpc-dashboard','--no-pager'],text=True)
warnings=[l for l in journal.splitlines() if any(x in l for x in ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault'))];assert not warnings,warnings
(P/'reboot-journal.txt').write_text(journal)
report={'status':'passed','version':after['version'],'files':after['files'],'bootIdBefore':before['bootId'],'bootIdAfter':after['bootId'],'activeTheme':after['activeTheme'],'nonAppearancePreferencesPreserved':True,'nonAppearancePreferenceCount':after['nonAppearancePreferenceCount'],'allPostActivationPreferencesSurviveReboot':True,'appearanceCustomizationsPreserved':True,'otherThemeProfilesPreserved':True,'service':after['service'],'guiHeartbeat':hb,'backup':receipt['backup'],'manifestSha256':receipt['manifestSha256'],'qmlWarnings':warnings,'verifiedAt':time.time()}
(P/'reboot-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
