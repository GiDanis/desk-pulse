"""Revision 2 native concept boards. Geometry fixtures only; no game runtime."""
from pathlib import Path
import importlib.util, json, math
from PIL import Image, ImageDraw

OUT=Path(__file__).resolve().parent
previous=OUT.parent/'v09-game-ux-study-2026-10-10/render_study.py'
spec=importlib.util.spec_from_file_location('game_study_helper',previous)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
S=base.S
WORLD=dict(width=144.,height=72.,road_width=10.,car_length=4.4,car_width=1.8,wheelbase=2.65)
ORIGIN=(48,104); SCALE=6.

# Illustrative future loop; not a generated or collision-qualified circuit.
FUTURE='M20 20 C20 6 44 6 56 18 L84 18 C96 18 98 7 111 7 C129 7 136 25 124 35 L107 48 C100 56 118 58 129 58 C140 64 127 67 114 67 L86 67 C71 67 64 60 54 55 L34 45 C22 40 21 53 12 49 C4 45 7 30 15 25 C18 22 20 24 20 20 Z'

def cubic(p0,p1,p2,p3,n=36):
    return [tuple((1-t)**3*p0[j]+3*(1-t)**2*t*p1[j]+3*(1-t)*t*t*p2[j]+t**3*p3[j] for j in (0,1)) for t in [i/n for i in range(1,n+1)]]

def future_points():
    segments=[('C',(20,6),(44,6),(56,18)),('L',(84,18)),('C',(96,18),(98,7),(111,7)),('C',(129,7),(136,25),(124,35)),('L',(107,48)),('C',(100,56),(118,58),(129,58)),('C',(140,64),(127,67),(114,67)),('L',(86,67)),('C',(71,67),(64,60),(54,55)),('L',(34,45)),('C',(22,40),(21,53),(12,49)),('C',(4,45),(7,30),(15,25)),('C',(18,22),(20,24),(20,20))]
    pts=[(20,20)]
    for seg in segments:
        if seg[0]=='L': pts.append(seg[1])
        else: pts.extend(cubic(pts[-1],*seg[1:]))
    return pts

def oval_points():
    pts=[(36,5),(108,5)]
    pts.extend((108+31*math.cos(a),36+31*math.sin(a)) for a in [math.radians(i) for i in range(-89,91,2)])
    pts.append((36,67))
    pts.extend((36+31*math.cos(a),36+31*math.sin(a)) for a in [math.radians(i) for i in range(91,271,2)])
    pts.append(pts[0]);return pts

def pose_at(points,fraction):
    distances=[math.dist(a,b) for a,b in zip(points,points[1:])];target=sum(distances)*fraction
    for a,b,d in zip(points,points[1:],distances):
        if target<=d:
            t=target/d
            return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))]
        target-=d
    return [*points[0],0]

OVAL_CARS=[[105,5,0],[45,5,0],[108+31*math.cos(math.radians(15)),36+31*math.sin(math.radians(15)),105],[74,67,180]]
FUTURE_CARS=[pose_at(future_points(),f) for f in (.07,.29,.52,.79)]

class Board(base.Board):
    def shell(self,active=False,progress=False):
        self.icon('race-car',24,13)
        self.text(64,11,'GIOCO',32,bold=True,maxw=250)
        if progress:self.text(224,17,'Progressi',24,'sub',maxw=164)
        if active:self.text(392,18,'SIMULAZIONE',22,'sub',maxw=300)
        else:
            for i in range(7):self.rect((420+i*16,23,428+i*16,31),'accent' if i==6 else 'border',4)
        self.text(768,17,'DATI DEMO',20,'sub',maxw=168)
        self.rect((24,55,936,56),'border')
    def world_point(self,p):return (ORIGIN[0]+p[0]*SCALE,ORIGIN[1]+p[1]*SCALE)
    def road(self,future=False):
        points=future_points() if future else oval_points();xy=[self.world_point(p) for p in points]
        native=[(round(x*S),round(y*S)) for x,y in xy]
        self.d.line(native,fill=self.c['sub'],width=round((10*SCALE+2)*S),joint='curve')
        for x,y in native:
            r=round((10*SCALE+2)*S/2);self.d.ellipse((x-r,y-r,x+r,y+r),fill=self.c['sub'])
        self.d.line(native,fill=self.c['border'],width=round(10*SCALE*S),joint='curve')
        for x,y in native:
            r=round(10*SCALE*S/2);self.d.ellipse((x-r,y-r,x+r,y+r),fill=self.c['border'])
        # Bounded structural dashes, distributed by length along the center line.
        offset=0.
        for a,b in zip(xy,xy[1:]):
            length=math.dist(a,b);cursor=0.
            while cursor<length:
                phase=offset%26;step=min(length-cursor, (12-phase) if phase<12 else (26-phase))
                if step<1e-7:step=1e-6
                if phase<12:
                    p1=tuple(a[i]+(b[i]-a[i])*cursor/length for i in (0,1));p2=tuple(a[i]+(b[i]-a[i])*(cursor+step)/length for i in (0,1))
                    self.d.line([(round(x*S),round(y*S)) for x,y in (p1,p2)],fill=self.c['sub'],width=S)
                offset+=step;cursor+=step
        px,py,ang=pose_at(points,.02) if future else [70,5,0]
        x,y=self.world_point((px,py));a=math.radians(ang);tx,ty=math.cos(a),math.sin(a);nx,ny=-ty,tx
        for row in range(8):
            for col in range(2):
                corners=[]
                for u,v in [(col*7-7,row*7.5-30),((col+1)*7-7,row*7.5-30),((col+1)*7-7,(row+1)*7.5-30),(col*7-7,(row+1)*7.5-30)]:
                    corners.append((round((x+tx*u+nx*v)*S),round((y+ty*u+ny*v)*S)))
                self.d.polygon(corners,fill=self.c['text'] if (row+col)%2==0 else self.c['surface'])
    def vehicle(self,pose,number,selected=False,sensors=False):
        x,y=self.world_point(pose[:2]);angle=pose[2]
        if sensors:
            for delta in (-60,-30,0,30,60):
                a=math.radians(angle+delta);ray_length=34.64 if abs(delta)==60 else 58
                self.d.line([(round(x*S),round(y*S)),(round((x+ray_length*math.cos(a))*S),round((y+ray_length*math.sin(a))*S))],fill=self.c['accent'],width=S)
        if selected:
            self.d.ellipse(((x-22)*S,(y-22)*S,(x+22)*S,(y+22)*S),outline=self.c['accent'],width=2*S)
        car=Image.new('RGBA',(48*S,48*S));d=ImageDraw.Draw(car)
        def box(values):return tuple(round(v*S) for v in values)
        col=self.c['accent'] if selected else self.c['sub']
        # Entire silhouette, wheels included: 26.4 x 10.8 px = 4.4 x 1.8 m.
        for xx in (15,30):
            for yy in (18.6,26.4):d.rectangle(box((xx,yy,xx+3,yy+3)),fill=self.c['text'])
        d.rounded_rectangle(box((10.8,19.2,37.2,28.8)),radius=2*S,fill=col)
        d.polygon([tuple(round(v*S) for v in point) for point in [(25,20.6),(28.5,20.6),(29.5,27.4),(25,27.4)]],fill=self.c['surface'])
        d.rectangle(box((18,20.6,21,27.4)),fill=self.c['surface'])
        d.rectangle(box((35,21,36,27)),fill=self.c['surface'])
        car=car.rotate(-angle,resample=Image.Resampling.BICUBIC)
        self.im.paste(car,(round((x-24)*S),round((y-24)*S)),car)
        if selected:
            self.rect((x-18,y-46,x+22,y-19),'surface',8,outline='accent')
            self.text(x-12,y-42,f'#{number}',20,'accent',bold=True,maxw=32)
    def arena(self,state='impara',selected=1,mode='Tutte',future=False):
        self.rect((24,72,936,568),'surface',24)
        self.road(future)
        if state=='pronto':return
        cars=FUTURE_CARS if future else OVAL_CARS
        for i,pose in enumerate(cars,1):
            if (mode!='Tutte' or state=='campione') and i!=selected:continue
            self.vehicle(pose,i,i==selected,mode=='Sensori' and i==selected)
    def hud(self,state='impara',selected=1,mode='Tutte'):
        self.rect((24,576,936,624),'surface',14)
        active=state in ('impara','campione')
        if active:
            self.text(40,588,'Impara · G12' if state=='impara' else 'Pesi fissi',24,bold=True,maxw=180)
            self.text(238,588,f'Auto #{selected}',24,maxw=128)
            self.text(380,589,'4/6 Auto · 2/8 Vista',22,'sub',maxw=258)
            if self.scale<=1:self.text(654,588,'Solo' if mode=='Solo auto' else mode,24,'sub',maxw=96)
        else:
            self.text(40,588,{'pronto':'Pronto','pausa':'Pausa','errore':'Pausa','progressi':'Pausa'}[state],24,bold=True,maxw=156)
            if state!='pronto':self.text(224,589,'2/8 Viste · 4/6 Moduli',22,'sub',maxw=364)
            self.text(652,589,'9 Menu',22,'sub',maxw=96)
        label='5 Pausa' if active else '5 Start' if state=='pronto' else '5 Riprova' if state=='errore' else '5 Dettagli' if state=='progressi' else '5 Riprendi'
        self.rect((760,578,920,622),'focus',12,outline='accent',width=2)
        width=self.d.textlength(label,font=self.font(24))/S
        self.text(760+(160-width)/2,588,label,24,'accent',maxw=144)
    def error_panel(self):
        self.rect((216,180,744,454),'surface',24,outline='border')
        self.icon('warning',240,204,30,color='error')
        self.paragraph(286,207,'Salvataggio non riuscito',434,28,'error',2)
        self.paragraph(240,286,'Sessione in pausa. Il campione precedente è disponibile.',480,24,'sub',3)
        self.text(240,404,'5 Riprova · 7 Indietro',24,maxw=480)
    def progress(self):
        self.rect((24,72,936,568),'surface',24)
        self.text(48,100,'Avanzamento per generazione',28,bold=True,maxw=800)
        self.text(48,149,'Ultima sessione · dati demo',22,'sub')
        x0,y0,x1,y1=116,224,884,492;vals=[7,16,14,30,27,44,52,48,63,65,59,72]
        self.text(48,184,'Avanzamento (%)',22,'sub')
        for value in (0,50,100):
            yy=y1-value/100*(y1-y0);self.rect((x0,yy,x1,yy+1),'border');self.text(52,yy-10,str(value),20,'sub',numeric=True)
        pts=[(x0+i*(x1-x0)/11,y1-v/100*(y1-y0)) for i,v in enumerate(vals)]
        self.d.line([(round(x*S),round(y*S)) for x,y in pts],fill=self.c['accent'],width=3*S)
        for x,y in pts:self.rect((x-4,y-4,x+4,y+4),'accent',4)
        for i in (0,5,11):self.text(pts[i][0]-8,510,str(i+1),20,'sub',numeric=True)
        self.text(432,540,'Generazione',22,'sub')
    def overlay(self,urgent=False):
        if urgent:return super().overlay(True)
        x,y,w,h=272,126,664,498
        self.rect((x,y,x+w,y+h),'surface',24,outline='border')
        self.text(x+24,y+24,'Menu · Gioco',30,bold=True)
        rows=['Modalità: Impara','Salva e termina','Velocità: Osserva','Visualizzazione: Tutte','Nuova sessione','Dettagli']
        for i,row in enumerate(rows):
            yy=y+87+i*54
            if i==0:self.rect((x+16,yy-8,x+w-16,yy+39),'focus',14)
            self.text(x+32,yy,row,25,'accent' if i==0 else 'text',maxw=w-64)
        self.text(x+24,y+h-54,'2 / 8 Seleziona · 5 Conferma · 7 Indietro',22,'sub',maxw=w-48)
    def save(self):
        self.im.resize((960,640),Image.Resampling.LANCZOS).save(OUT/(self.name+'.png'))
        return dict(file=self.name+'.png',size=[960,640],text_within_canvas=all(0<=a<=960 and 0<=c<=960 and 0<=b<=640 and 0<=d<=640 for item in self.boxes for a,b,c,d in [item['box']]),text_fits_assigned_width=all(item['fits_width'] for item in self.boxes),local_title_removed=not any(x['text']=='Auto che impara' for x in self.boxes))

def main():
    fixtures=[('pronto','pronto',1,'Tutte',False,False,1),('impara','impara',1,'Tutte',False,False,1),('pausa','pausa',1,'Tutte',False,False,1),('auto-2','impara',2,'Tutte',False,False,1),('solo-auto','impara',1,'Solo auto',False,False,1),('sensori','impara',1,'Sensori',False,False,1),('campione','campione',1,'Solo auto',False,False,1),('errore','errore',1,'Tutte',False,False,1),('progressi','progressi',1,'Tutte',False,False,1),('menu','pausa',1,'Tutte',False,False,1),('urgente','pausa',1,'Tutte',False,False,1),('notte','impara',1,'Tutte',False,True,1),('testo-110','impara',1,'Tutte',False,False,1.1),('circuito-futuro','impara',1,'Tutte',True,False,1)]
    results=[]
    for name,state,selected,mode,future,night,scale in fixtures:
        b=Board(name,night,scale);b.shell(state in ('impara','campione'),state=='progressi')
        if state=='progressi':b.progress()
        else:b.arena(state,selected,mode,future)
        b.hud(state,selected,mode)
        if state=='errore':b.error_panel()
        if name in ('menu','urgente'):b.overlay(name=='urgente')
        results.append(b.save())
    diag=3.5*25.4;panelw=diag*3/math.sqrt(13);panelh=diag*2/math.sqrt(13)
    report=dict(scope='Offline native 960x640 concepts only. No simulation, board profiling or game implementation.',revision=2,boards=results,world=WORLD,uniform_scale_px_per_m=SCALE,arena=[24,72,912,496],drawable=[44,92,872,456],oval_pixels=[864,432],car_pixels=[26.4,10.8],hud=[24,576,912,48],arena_percent_display=round(912*496/(960*640)*100,2),arena_percent_content=round(496/(496+48)*100,2),arena_area_gain_percent=round((912*496/(624*504)-1)*100,2),oval_bbox_area_factor=round(864*432/(568*252),3),nominal_panel_mm=[round(panelw,2),round(panelh,2)],nominal_car_length_mm=round(panelw*26.4/960,2),body_road_width_ratio=round(10/1.8,3),future_track_status='Illustrative curve fixture, same physical scale; not generated or collision-qualified.',manual_review='pending',interactive_review='pending',runtime_gates='S1–S5 open')
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'track-fixtures.json').write_text(json.dumps(dict(world=WORLD,ovalCars=OVAL_CARS,futureCars=FUTURE_CARS,futurePath=FUTURE),indent=2)+'\n')
    assert all(all(item[k] for k in ('text_within_canvas','text_fits_assigned_width','local_title_removed')) for item in results),results
    print(json.dumps(dict(boards=len(results),geometry=report['arena'],car_pixels=report['car_pixels'],all_text_fits=True)))
if __name__=='__main__':main()
