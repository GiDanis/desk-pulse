#!/usr/bin/env python3
"""Curated, reproducible planar approximations; no production state writes."""
import hashlib
import json
from pathlib import Path
import numpy as np


def spline(control, samples=768):
    p=np.array(control,dtype=float);out=[]
    for i in range(len(p)):
        a,b,c,d=p[(i-1)%len(p)],p[i],p[(i+1)%len(p)],p[(i+2)%len(p)]
        for t in np.linspace(0,1,24,endpoint=False):
            out.append(((1-t)**3*a+(3*t**3-6*t*t+4)*b+(-3*t**3+3*t*t+3*t+1)*c+t**3*d)/6)
    q=np.array(out);lengths=np.linalg.norm(np.roll(q,-1,axis=0)-q,axis=1)
    distances=np.r_[0,np.cumsum(lengths)];q=np.vstack((q,q[0]))
    return np.column_stack([np.interp(np.linspace(0,distances[-1],samples,endpoint=False),distances,q[:,j]) for j in range(2)])


def save(identity,name,points,length,width,source,note):
    points=points-points.mean(axis=0)
    points*=length/np.linalg.norm(np.roll(points,-1,axis=0)-points,axis=1).sum()
    # Start chosen on the lower straight; straight clearance checked by tests.
    lower=np.where(points[:,1]<np.percentile(points[:,1],30))[0]
    start=int(lower[np.argmin(abs(points[lower,0]))])
    ds=np.r_[0,np.cumsum(np.linalg.norm(np.roll(points,-1,axis=0)-points,axis=1))]
    spec={'id':identity,'name':name,'revision':1,'road_width':width,'units':'m',
          'centerline':points.tolist(),'startDistance':float(ds[start]),
          'source':source,'approximation':note,'publishedLength':length}
    spec['geometryHash']=hashlib.sha256(json.dumps(spec['centerline'],separators=(',',':')).encode()).hexdigest()
    path=Path(__file__).with_name('game-tracks')/(identity+'.json')
    path.write_text(json.dumps(spec,separators=(',',':'))+'\n')
    from game_catalog import _track_data
    from game_geometry import get_track
    _track_data.cache_clear();get_track.cache_clear()
    spec['drawing']=get_track(identity).render()
    path.write_text(json.dumps(spec,separators=(',',':'))+'\n')
    _track_data.cache_clear();get_track.cache_clear()


def main():
    # Mallory's one-mile oval is simplified to a capsule, not a survey replica.
    length=1609.344;r=80.;a=(length-2*np.pi*r)/4
    p=[]
    for x in np.linspace(-a,a,200,endpoint=False):p.append((x,-r))
    for q in np.linspace(-np.pi/2,np.pi/2,184,endpoint=False):p.append((a+r*np.cos(q),r*np.sin(q)))
    for x in np.linspace(a,-a,200,endpoint=False):p.append((x,r))
    for q in np.linspace(np.pi/2,3*np.pi/2,184,endpoint=False):p.append((-a+r*np.cos(q),r*np.sin(q)))
    save('mallory-oval-1','Mallory · Ovale',np.array(p),length,12.,
         'https://www.malloryparkcircuit.com/wp-content/uploads/2014/03/Mallory-Park-Map.pdf',
         'Ovale semplificato: sviluppo ufficiale di un miglio; raggio e larghezza 12 m di progetto. Piano, senza banking.')
    # Hand-traced short route (black) from the official technical plan.
    control=[(464,400),(596,400),(735,374),(750,362),(754,320),(745,314),
             (697,319),(675,328),(655,347),(636,352),(500,345),(482,340),
             (464,319),(452,313),(438,309),(279,318),(264,316),(141,293),
             (131,297),(118,318),(109,353),(102,444),(105,460),(120,469),
             (145,469),(164,461),(171,443),(170,431),(147,388),(142,374),
             (145,361),(157,353),(198,347),(208,351),(222,375),(229,389),(239,394)]
    points=spline([(x,-y) for x,y in control])
    # Smooth the hand-traced plan at metric resolution: promotional corner
    # clusters must not create bends tighter than the standard car can steer.
    for _ in range(60):points=(np.roll(points,1,axis=0)+2*points+np.roll(points,-1,axis=0))/4
    save('varano-short-1','Varano · Corto',points,1640.,12.,
         'https://www.autodromovarano.it/wp-content/uploads/2024/04/pista_1640_19.pdf',
         'Ricostruzione planare approssimata della mappa, calibrata a 1640 m; carreggiata uniforme 12 m, fonte 10–12 m. Altimetria esclusa; rettifili/raggi non da rilievo.')


if __name__=='__main__':main()
