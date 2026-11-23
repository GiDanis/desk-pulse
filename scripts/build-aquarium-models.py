#!/usr/bin/env python3
"""Original parametric fish: editable source, one coloured/skinned mesh per type.

No external authoring runtime or generated code is loaded on the board.
Rebuild deterministically with the Python standard library.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1] / 'dashboard/assets/aquarium/calm-3d-v1'
PROFILES = [
    dict(id='teal', name='Neon Calm', description='Corpo affusolato, riflessi turchesi e una linea luminosa lungo i fianchi.', radiusY=14, radiusZ=9, tail=18, dorsal=12, size=105, speed=30, frequency=1.2, color=[.18,.65,.70], accent=[.60,.88,.78], pattern='neon'),
    dict(id='gold', name='Fantasia dorata', description='Forme morbide e pinne ampie, con sfumature ambra e crema.', radiusY=23, radiusZ=15, tail=28, dorsal=21, size=150, speed=21, frequency=.8, color=[.95,.53,.18], accent=[1,.83,.48], pattern='gold'),
    dict(id='angel', name='Angelo perla', description='Sagoma alta, pinne a vela e bande scure su un corpo color perla.', radiusY=29, radiusZ=8, tail=21, dorsal=43, size=144, speed=19, frequency=.7, color=[.80,.85,.79], accent=[.86,.73,.45], pattern='bands'),
    dict(id='clown', name='Corallo', description='Corpo arancio corallo, fasce avorio e bordi scuri sulle pinne.', radiusY=19, radiusZ=12, tail=20, dorsal=14, size=117, speed=25, frequency=1, color=[.97,.38,.13], accent=[1,.77,.42], pattern='clown'),
]


def mesh(p):
    vertices, indices = [], []
    def vertex(pos, normal, color):
        x=pos[0]
        if x >= 0: joints=(0,1,2,0);weights=(1,0,0,0)
        elif x >= -30:
            t=-x/30;joints=(0,1,2,0);weights=(1-t,t,0,0)
        else:
            t=min(1,(-x-30)/23);joints=(0,1,2,0);weights=(0,1-t,t,0)
        n=math.sqrt(sum(c*c for c in normal)) or 1
        vertices.append((*pos,*(c/n for c in normal),*color,1,*joints,*weights))
        return len(vertices)-1
    def sphere(center, radii, color, rings=12, slices=20, body=False):
        base=len(vertices)
        for i in range(rings+1):
            a=math.pi*i/rings
            for j in range(slices+1):
                b=2*math.pi*j/slices
                q=(radii[0]*math.cos(a),radii[1]*math.sin(a)*math.cos(b),radii[2]*math.sin(a)*math.sin(b))
                c=list(color)
                if body:
                    shade=.86+.14*(q[1]/radii[1]+1)/2
                    c=[v*shade for v in c]
                    pattern=p['pattern']
                    if pattern=='neon' and abs(q[1]-1)<3.3:c=[.47,.95,.91]
                    if pattern=='neon' and q[1]<-3 and q[0]<5:c=[.85,.25,.18]
                    if pattern=='bands' and any(abs(q[0]-band)<3 for band in (-18,1,22)):c=[.18,.25,.28]
                    if pattern=='clown':
                        distance=min(abs(q[0]-band) for band in (-22,0,24))
                        if distance<4:c=[.97,.93,.80]
                        elif distance<5.6:c=[.13,.19,.20]
                    if pattern=='gold' and q[1]<-2:c=[v*.5+w*.5 for v,w in zip(c,p['accent'])]
                vertex(tuple(q[k]+center[k] for k in range(3)),tuple(q[k]/radii[k]**2 for k in range(3)),c)
        for i in range(rings):
            for j in range(slices):
                v=base+i*(slices+1)+j;w=v+slices+1
                indices.extend((v,w,v+1,v+1,w,w+1))
    def fin(root,edge,color):
        # Fan surfaces with thickness and coloured rays, not flat image planes.
        for side in (-1,1):
            for i in range(len(edge)-1):
                a=vertex((root[0],root[1],root[2]+side*.65),(0,0,side),color)
                shade=.73 if i%3==0 else 1
                c=[v*shade for v in p['accent']]
                b=vertex((edge[i][0],edge[i][1],edge[i][2]+side*.45),(0,0,side),c)
                d=vertex((edge[i+1][0],edge[i+1][1],edge[i+1][2]+side*.45),(0,0,side),c)
                cross=(edge[i][0]-root[0])*(edge[i+1][1]-root[1])-(edge[i][1]-root[1])*(edge[i+1][0]-root[0])
                indices.extend((a,b,d) if cross*side>=0 else (a,d,b))
    sphere((0,0,0),(38,p['radiusY'],p['radiusZ']),p['color'],rings=24,slices=32,body=True)
    for side in (-1,1):
        sphere((25,6,side*p['radiusZ']*.72),(4.8,4.8,2.6),[.98,.91,.69],8,12)
        sphere((26,6.3,side*(p['radiusZ']*.72+2)),(2.5,2.8,1.1),[.035,.075,.085],8,12)
        sphere((26.6,7.5,side*(p['radiusZ']*.72+2.9)),(.8,.8,.35),[1,1,.95],5,8)
    t=p['tail']
    edge=[(-64+5*abs(math.sin(i*math.pi/12)),t*math.cos(i*math.pi/12),0) for i in range(13)]
    fin((-34,0,0),edge,p['color'])
    h=p['radiusY'];d=p['dorsal']
    fin((3,h*.55,0),[(-25+49*i/12,h*.8+d*math.sin(math.pi*i/12),0) for i in range(13)],p['color'])
    fin((-7,-h*.6,0),[(-30+44*i/10,-h*.7-d*.65*math.sin(math.pi*i/10),0) for i in range(11)],p['color'])
    for side in (-1,1):
        fin((10,-3,side*p['radiusZ']*.7),[(4-22*i/8,-8-10*math.sin(i*math.pi/16),side*(p['radiusZ']*.7+8*math.sin(i*math.pi/16))) for i in range(9)],p['accent'])
    data=b''.join(struct.pack('<10f4i4f',*v) for v in vertices)
    idx=struct.pack('<'+'I'*len(indices),*indices)
    return b'FISHMESH'+struct.pack('<II',len(vertices),len(indices))+data+idx, len(indices)//3


def main():
    ROOT.mkdir(parents=True,exist_ok=True);species=[];files={}
    for p in PROFILES:
        data,triangles=mesh(p);file=p['id']+'-'+hashlib.sha256(data).hexdigest()[:16]+'.fishmesh';(ROOT/file).write_bytes(data);files[file]=hashlib.sha256(data).hexdigest()
        species.append(dict(id=p['id'],name=p['name'],description=p['description'],mesh=file,rigProfile='swim-skin-v1',triangles=triangles,referenceSize=p['size'],speed=p['speed'],tailFrequency=p['frequency'],variants=[{'id':'original','name':'Originale','tint':'#ffffff'},{'id':'pearl','name':'Perla','tint':'#d6e9ff'}]))
    catalog={'schemaVersion':2,'id':'calm-3d-v1','revision':1,'license':'Original SmartPC procedural artwork; repository LICENSE applies.','files':files,'species':species}
    (ROOT/'catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({p['id']:p['triangles'] for p in species}))
if __name__=='__main__':main()
