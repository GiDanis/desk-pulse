"""Verify selected overrides and other theme profiles against protected backup."""
import hashlib,json
from pathlib import Path
from PySide6.QtCore import QSettings
P=Path('/var/lib/smartpc-dashboard/v086-source-proof')
receipt=json.loads((P/'activation-receipt.json').read_text());backup=Path(receipt['backup'])/'.config/SmartPC/Dashboard.conf'
old=QSettings(str(backup),QSettings.Format.IniFormat);new=QSettings('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf',QSettings.Format.IniFormat)
oldcfg=json.loads(old.value('appearance/config','{}'));newcfg=json.loads(new.value('appearance/config','{}'))
assert {k:v for k,v in oldcfg.items() if k!='bundleRevision'}=={k:v for k,v in newcfg.items() if k!='bundleRevision'}
assert newcfg['bundleRevision']==receipt['activeTheme']
a=json.loads(old.value('appearance/themeOverrides','{}'));b=json.loads(new.value('appearance/themeOverrides','{}'))
prefix='studio.applecalm@';target=prefix+receipt['activeTheme']['version']+'#'+receipt['activeTheme']['digest']
assert {k:v for k,v in a.items() if not k.startswith(prefix)}=={k:v for k,v in b.items() if not k.startswith(prefix)},'Other theme profiles changed'
assert b.get(target)==oldcfg['overrides'],'Active customizations changed'
assert all(not k.startswith(prefix) or k==target for k in b),'Obsolete revision profile unexpectedly retained'
report={'status':'passed','activeConfigurationPreservedExceptRevision':True,'activeOverridesPreserved':True,'otherThemeProfilesPreserved':True,'policy':'retention latest removes obsolete revision overrides after three coherent heartbeats','oldRevisionProfileCount':sum(k.startswith(prefix) for k in a),'activeRevisionProfileCount':sum(k.startswith(prefix) for k in b)}
(P/'appearance-retention-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
