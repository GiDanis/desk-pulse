"""Real TTF registration, deduplication, shared leases and invalid glyph/font recovery."""
import os,tempfile
from pathlib import Path
import json,shutil,hashlib
os.environ['XDG_CONFIG_HOME']=tempfile.mkdtemp(prefix='smartpc-fonts-config-')
os.environ['SMARTPC_THEME_STORE']=tempfile.mkdtemp(prefix='smartpc-fonts-store-')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtGui import QGuiApplication
from theme_service import ThemeService,FontRegistry
from theme_pack import import_pack
app=QGuiApplication([])
source=Path(tempfile.mkdtemp(prefix='smartpc-fonts-source-'))
font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf');assert font.is_file(),'DejaVu Sans fixture font missing'
shutil.copyfile(font,source/'UI.ttf');digest=hashlib.sha256(font.read_bytes()).hexdigest()
pack={'schemaVersion':1,'id':'font.proof','name':'Font proof','version':'1.0.0','extends':'base',
      'tokens':{'typography.uiFamily':'asset:ui','typography.numbersFamily':'asset:numbers'},
      'assets':[{'id':key,'type':'font','path':'UI.ttf','sha256':digest} for key in ('ui','numbers')]}
(source/'theme.json').write_text(json.dumps(pack));import_pack(source,Path(os.environ['SMARTPC_THEME_STORE']))
a=ThemeService();b=ThemeService()
a.beginEdit();assert a.selectDraft('font.proof'),a.lastError
assert len(FontRegistry.entries)==1
registration=FontRegistry.entries[digest]['id']
b.beginEdit();assert b.selectDraft('font.proof');assert FontRegistry.entries[digest]['id']==registration
for i in range(100):
    a.selectDraft('base');assert a.selectDraft('font.proof')
    assert FontRegistry.entries[digest]['id']==registration
assert not a.setSection('iconOverrides',{'weather.clear':{'backend':'glyph','glyph':'\U0010ffff','family':'asset:ui'}})
assert a.activeThemeId=='font.proof'
assert not a.setToken('typography.uiFamily','NoSuchFontFamily')
a.cancel();assert b._font_owner in FontRegistry.entries[digest]['owners']
b.cancel();assert len(FontRegistry.entries)<=FontRegistry.idle_capacity
# A cached resolution must detect assets removed after a successful preview.
a.beginEdit();assert a.selectDraft('font.proof');a.cancel()
installed=Path(os.environ['SMARTPC_THEME_STORE'])/'font.proof'/'UI.ttf'
installed.unlink();a.beginEdit();assert not a.selectDraft('font.proof');assert a.activeThemeId=='base'
print('TTF: real load, digest deduplication, shared leases, 100 stable registrations, missing glyph/family and bounded retirement PASS')
