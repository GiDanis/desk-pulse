"""Verify the additive icon without changing any previously approved glyph."""
import argparse,json,re,hashlib
from pathlib import Path
from PySide6.QtGui import QGuiApplication,QImage
from PySide6.QtQml import QJSEngine
p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
app=QGuiApplication([])
def metadata(root):
 text=(root/'qml/IconPaths.js').read_text()
 return {key:json.loads(re.search(r'^var '+key+r' = (.*);$',text,re.M).group(1)) for key in ('paths','aliases','names','colors','tile','columns')}
before=metadata(a.previous);after=metadata(a.candidate)
assert after['names']==before['names']+['aquarium']
assert before['colors']==after['colors'] and before['tile']==after['tile'] and before['columns']==after['columns']
for name,path in before['paths'].items():assert after['paths'][name]==path,name
for name,value in before['aliases'].items():assert after['aliases'][name]==value,name
images=[QImage(str(root/'qml/icon-atlas.png')).convertToFormat(QImage.Format_RGBA8888) for root in (a.previous,a.candidate)]
assert all(not image.isNull() for image in images)
checks=0
for c in range(len(before['colors'])):
 for i,name in enumerate(before['names']):
  data=[]
  for meta,image in zip((before,after),images):
   cell=c*len(meta['names'])+i;tile=meta['tile'];crop=image.copy(cell%meta['columns']*tile,cell//meta['columns']*tile,tile,tile)
   data.append(bytes(crop.constBits()))
  assert data[0]==data[1],(name,before['colors'][c]);checks+=1
js=QJSEngine();value=js.evaluate((a.candidate/'qml/Format.js').read_text().replace('.pragma library',''))
assert not value.isError(),value.toString()
assert js.evaluate('familyIcon("aquarium")').toString()=='aquarium'
assert js.evaluate('settingIcon("module.aquarium")').toString()=='aquarium'
assert js.evaluate('settingIcon("modules.aquarium")').toString()=='aquarium'
# New glyph must have visible pixels in every supported palette color.
for c in range(len(after['colors'])):
 cell=c*len(after['names'])+after['names'].index('aquarium');t=after['tile'];crop=images[1].copy(cell%after['columns']*t,cell//after['columns']*t,t,t)
 assert max(bytes(crop.constBits())[3::4])>0
changed=[str(f.relative_to(a.candidate)) for f in a.candidate.rglob('*') if f.is_file() and hashlib.sha256(f.read_bytes()).digest()!=hashlib.sha256((a.previous/f.relative_to(a.candidate)).read_bytes()).digest()]
assert set(changed)=={'bundle.json','theme.json','qml/Format.js','qml/IconPaths.js','qml/icon-atlas.png'},changed
report={'status':'passed','version':'1.6.5','unchangedGlyphs':len(before['names']),'colors':len(before['colors']),'identicalPixelCells':checks,'newGlyph':'aquarium','actualJsMappings':3,'payloadDelta':sorted(changed),'scope':'Existing glyph pixels, aliases and all other payload files unchanged; no panel/optical claim'}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
