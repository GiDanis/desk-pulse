"""Offline design study only. No imports from, or writes to, the game runtime.

Run with Python + NumPy + Pillow. Geometry checks are sampled design checks,
not a replacement for a continuous road validator or a physics qualification.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
BUNDLE = ROOT / 'theme-projects/apple-calm/bundle'
TOKENS = json.loads((BUNDLE / 'theme.json').read_text())['tokens']
W, H = 960, 640

def font(size, bold=False):
    return ImageFont.truetype(str(BUNDLE / 'fonts' / ('LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf')), size)

def color(key):
    return TOKENS['colors.' + key]

def txt(d, xy, value, size=24, bold=False, fill=None, anchor=None):
    d.text(xy, value, font=font(size, bold), fill=fill or color('textPrimary'), anchor=anchor)

def frame(subtitle, active=None):
    im = Image.new('RGB', (W, H), color('background'))
    d = ImageDraw.Draw(im)
    txt(d, (24, 18), 'GIOCO', 24, True)
    txt(d, (936, 23), 'CONCEPT · 960×640', 18, fill=color('textSecondary'), anchor='ra')
    if active:
        for i, title in enumerate(('Sessione', 'Allenamento', 'Gestione')):
            x = 24 + i * 312
            selected = i == active - 1
            d.rounded_rectangle((x, 76, x + 288, 122), radius=18,
                                fill=color('surfaceFocused') if selected else color('surface'))
            txt(d, (x + 144, 88), title, 24, selected, color('accent') if selected else None, 'ma')
        txt(d, (24, 145), subtitle, 28, True)
    return im, d

def row(d, y, title, description, value, selected=False):
    d.rounded_rectangle((24, y, 936, y + 92), radius=14,
                        fill=color('surfaceFocused') if selected else color('surface'),
                        outline=color('accent') if selected else None, width=3)
    txt(d, (48, y + 15), title, 26, True)
    txt(d, (48, y + 54), description, 20, fill=color('textSecondary'))
    txt(d, (906, y + 16), value, 25, False, color('accent') if selected else None, 'ra')

def setup_images():
    im, d = frame('Prepara la sessione', 1)
    row(d, 198, 'Modalità', 'Allena un solo pilota e conserva i progressi.', 'Impara')
    row(d, 302, 'Pilota', 'Apri la rosa e scegli chi allenare.', 'Pilota 1', True)
    row(d, 406, 'Circuito', 'Asfalto asciutto · vettura standard.', 'Ovale')
    d.rounded_rectangle((24, 526, 936, 614), radius=14, fill=color('surface'))
    txt(d, (48, 544), 'Avvia allenamento', 26, True)
    txt(d, (48, 579), 'Evoluzione · configurazione da confermare', 20, fill=color('textSecondary'))
    txt(d, (906, 552), '›', 30, fill=color('accent'), anchor='ra')
    im.save(OUT / 'sessione-concept.png')
    im, d = frame('Allenamento', 2)
    row(d, 198, 'Metodo', 'Il modo in cui il pilota modifica la propria rete.', 'Evoluzione', True)
    row(d, 302, 'Scenario', 'Tentativi indipendenti senza avversari.', 'Solo pista')
    row(d, 406, 'Parametri avanzati', 'Popolazione, mutazione, rete e durata dei tentativi.', 'Apri')
    txt(d, (24, 552), 'Progressione automatica: Controllo → Passo', 23, True)
    txt(d, (24, 586), 'I tempi validi si confrontano sullo stesso circuito.', 20, fill=color('textSecondary'))
    im.save(OUT / 'allenamento-concept.png')
    im, d = frame('Parametri avanzati · Evoluzione')
    txt(d, (24, 86), 'Parametri avanzati', 28, True)
    txt(d, (24, 134), 'Evoluzione · modifiche in bozza', 22, fill=color('textSecondary'))
    row(d, 198, 'Popolazione', 'Reti candidate per ogni generazione.', '32', True)
    row(d, 302, 'Mutazione', 'Intensità delle modifiche ai pesi della rete.', '0,15')
    row(d, 406, 'Neuroni nascosti', 'Dimensione dello strato interno della rete.', '16')
    txt(d, (24, 552), '1 di 2', 20, fill=color('textSecondary'))
    txt(d, (936, 552), 'Applica modifiche', 23, True, color('accent'), 'ra')
    txt(d, (24, 590), 'Il percorso precedente resta conservato.', 20, fill=color('textSecondary'))
    im.save(OUT / 'avanzate-concept.png')

def curve(points, samples_per_span=32):
    """Uniform closed cubic B-spline, sampled; control points are meters."""
    p = np.asarray(points, float)
    out = []
    for i in range(len(p)):
        a, b, c, e = (p[(i + j) % len(p)] for j in (-1, 0, 1, 2))
        for t in np.linspace(0, 1, samples_per_span, endpoint=False):
            out.append((a*(1-t)**3+b*(3*t**3-6*t*t+4)+c*(-3*t**3+3*t*t+3*t+1)+e*t**3)/6)
    return np.array(out)

def resample(p, n=384):
    q = np.roll(p, -1, axis=0)
    lengths = np.linalg.norm(q-p, axis=1)
    cumulative = np.r_[0, np.cumsum(lengths)]
    distances = np.linspace(0, cumulative[-1], n, endpoint=False)
    i = np.searchsorted(cumulative, distances, side='right')-1
    f = (distances-cumulative[i])/lengths[i]
    return p[i] + (q[i]-p[i])*f[:, None], float(cumulative[-1])

def crossing_count(a, b=None):
    """Proper segment crossings only. Collinearity/tangencies are not certified."""
    same = b is None
    b = a if same else b
    def cross(u, v):
        return u[0]*v[1]-u[1]*v[0]
    count = 0
    for i in range(len(a)):
        aa, ab = a[i], a[(i+1) % len(a)]
        for j in range(i+1 if same else 0, len(b)):
            if same and (j == i+1 or (i == 0 and j == len(a)-1)):
                continue
            ba, bb = b[j], b[(j+1) % len(b)]
            den = cross(ab-aa, bb-ba)
            if abs(den) < 1e-10:
                continue
            t, u = cross(ba-aa, bb-ba)/den, cross(ba-aa, ab-aa)/den
            count += int(1e-9 < t < 1-1e-9 and 1e-9 < u < 1-1e-9)
    return count

def geometry():
    # Candidate with both turn directions and a broad infield S. Not shipped.
    controls = [(-53,-24),(-22,-28),(18,-27),(45,-23),(57,-8),
                (49,11),(30,16),(18,27),(-7,25),(-25,10),(-48,19),(-60,3)]
    p, length = resample(curve(controls))
    tangents = np.roll(p,-1,axis=0)-np.roll(p,1,axis=0)
    tangents /= np.linalg.norm(tangents,axis=1)[:,None]
    normals = np.column_stack((-tangents[:,1],tangents[:,0]))
    left, right = p + 5*normals, p - 5*normals
    headings = np.arctan2(tangents[:,1],tangents[:,0])
    delta = (np.roll(headings,-1)-headings+math.pi) % (2*math.pi)-math.pi
    curvature = delta/(length/len(p))
    bounds = np.vstack((left,right))
    span = np.ptp(bounds,axis=0)
    # Same drawing viewport as runtime: 912×496, with 24 px total design padding.
    scale = min(888/(span[0]+8), 472/(span[1]+8))
    checks = {'centerline':crossing_count(p), 'left_boundary':crossing_count(left),
              'right_boundary':crossing_count(right), 'between_boundaries':crossing_count(left,right)}
    serial = p.round(6).tolist()
    report = {'status':'offline concept; not a runtime track or physics qualification',
              'method':'closed cubic B-spline → 384 equal-arclength samples, sampled normal offsets',
              'rejected_initial_interpolation':{'method':'Catmull-Rom through same controls',
                 'minimum_sampled_radius_m':5.421452819165047,
                 'reason':'almost equal to 5 m half-road width; insufficient inner-radius design margin'},
              'control_points_m':controls, 'samples':len(p), 'length_m':length,
              'road_width_m':10, 'road_bounds_m':[bounds.min(axis=0).tolist(),bounds.max(axis=0).tolist()],
              'minimum_sampled_radius_m':float(1/np.abs(curvature).max()),
              'turn_directions':int((curvature>0.005).any())+int((curvature<-0.005).any()),
              'proper_crossings':checks, 'display_scale_px_per_m':float(scale),
              'car_pixels':[float(4.4*scale),float(1.8*scale)],
              'geometry_sha256':hashlib.sha256(json.dumps(serial,separators=(',',':')).encode()).hexdigest(),
              'limits':['sampled proper crossings only; no continuous tangency/clearance certification',
                        'spawn, gates, raycasting, physics, learning and native rendering are not implemented here',
                        'no board benchmark or evidence of constant 60 FPS']}
    (OUT / 'geometry-study.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT / 'candidate-centerline.json').write_text(json.dumps({'units':'m','studyOnly':True,'points':serial},indent=2)+'\n')
    im,d = frame('')
    d.rounded_rectangle((24,72,936,568),radius=24,fill=color('surface'))
    center = (bounds.min(axis=0)+bounds.max(axis=0))/2
    def screen(xy):
        z=(xy-center)*scale
        return (480+float(z[0]),320-float(z[1]))
    def area(v):
        q=np.roll(v,-1,axis=0)
        return abs(float(np.sum(v[:,0]*q[:,1]-v[:,1]*q[:,0])))
    outer,inner=sorted((left,right),key=area,reverse=True)
    d.polygon([screen(v) for v in outer],fill='#DCE1E7')
    d.polygon([screen(v) for v in inner],fill=color('surface'))
    for boundary in (left,right):
        d.line([screen(v) for v in np.vstack((boundary,boundary[0]))],fill='#939CA9',width=2)
    # Dashed centerline is a design aid, not a compulsory runtime overlay.
    for i in range(0,len(p),12):
        d.line([screen(p[i]),screen(p[(i+5)%len(p)])],fill='#FFFFFF',width=2)
    for i,c in ((40,'#0066CC'),(47,'#AD2525')):
        pos=p[i]; t=tangents[i]; n=normals[i]
        corners=[pos+t*2.2+n*.9,pos+t*2.2-n*.9,pos-t*2.2-n*.9,pos-t*2.2+n*.9]
        d.polygon([screen(v) for v in corners],fill=c)
    d.rounded_rectangle((24,576,936,624),radius=14,fill=color('surface'))
    txt(d,(48,588),'Circuito Tecnico · studio',23,True)
    txt(d,(912,590),'Asciutto · auto 4,4×1,8 m',20,fill=color('textSecondary'),anchor='ra')
    im.save(OUT/'circuito-tecnico-concept.png')
    return report

if __name__ == '__main__':
    setup_images()
    report=geometry()
    print(json.dumps({k:report[k] for k in ('length_m','minimum_sampled_radius_m','proper_crossings','display_scale_px_per_m','car_pixels')},indent=2))
