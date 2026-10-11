"""Offline concept boards only. No dashboard services, simulation or NPU calls."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json, math, re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
FONTS = ROOT / 'theme-projects/apple-calm/bundle/fonts'
ART = ROOT / 'theme-projects/apple-calm/bundle/qml'
S = 2
DAY = dict(bg='#F3F4F6', surface='#FFFFFF', focus='#E7F0FF', border='#CDD2DA', text='#1D1D1F', sub='#5D626C', accent='#0066CC', error='#AD2525')
NIGHT = dict(bg='#111216', surface='#202228', focus='#293B54', border='#505663', text='#F5F5F7', sub='#ADB2BD', accent='#79B8FF', error='#FF9696')
source = (ART/'IconPaths.js').read_text()
NAMES = json.loads(re.search(r'var names = (.*?);', source).group(1))
COLORS = json.loads(re.search(r'var colors = (.*?);', source).group(1))
ATLAS = Image.open(ART/'icon-atlas.png').convert('RGBA')

class Board:
    def __init__(self, name, night=False, scale=1):
        self.name, self.c, self.scale = name, NIGHT if night else DAY, scale
        self.im = Image.new('RGB', (960*S,640*S), self.c['bg'])
        self.d = ImageDraw.Draw(self.im)
        self.boxes = []
    def font(self, size, numeric=False, bold=False):
        file = 'LiberationSans-Bold.ttf' if numeric and bold else 'LiberationSans-Regular.ttf' if numeric else 'Cantarell-VF.otf'
        f = ImageFont.truetype(str(FONTS/file), round(size*S*self.scale))
        if bold and not numeric:
            try: f.set_variation_by_axes([600])
            except ValueError: pass
        return f
    def rect(self, xy, color, radius=0, outline=None, width=1):
        box = tuple(round(v*S) for v in xy)
        if radius:
            self.d.rounded_rectangle(box, round(radius*S), fill=self.c.get(color,color), outline=self.c.get(outline,outline), width=width*S)
        else:
            self.d.rectangle(box, fill=self.c.get(color,color), outline=self.c.get(outline,outline), width=width*S)
    def text(self, x,y,txt,size=24,color='text',bold=False,numeric=False,maxw=None):
        f=self.font(size,numeric,bold)
        bbox=self.d.textbbox((x*S,y*S),txt,font=f,anchor='lt')
        width=self.d.textlength(txt,font=f)/S
        self.boxes.append(dict(text=txt,box=[round(v/S,2) for v in bbox],fits_width=maxw is None or width<=maxw+.1))
        self.d.text((x*S,y*S),txt,font=f,fill=self.c.get(color,color),anchor='lt')
    def paragraph(self,x,y,txt,width,size=24,color='sub',max_lines=3):
        f=self.font(size); lines=[]; line=''
        for word in txt.split():
            candidate=(line+' '+word).strip()
            if line and self.d.textlength(candidate,font=f)>width*S:
                lines.append(line); line=word
            else: line=candidate
        if line: lines.append(line)
        assert len(lines)<=max_lines, (txt, lines)
        for i,line in enumerate(lines): self.text(x,y+i*round(size*self.scale*1.25),line,size,color,maxw=width)
    def icon(self,symbol,x,y,size=28,color='accent'):
        index=COLORS.index(self.c[color])+0
        cell=index*len(NAMES)+NAMES.index(symbol)
        a=(cell%25)*48; b=(cell//25)*48
        tile=ATLAS.crop((a,b,a+48,b+48)).resize((size*S,size*S),Image.Resampling.LANCZOS)
        self.im.paste(tile,(x*S,y*S),tile)
    def shell(self,title='Auto che impara'):
        self.icon('race-car',24,13)
        self.text(64,11,'GIOCO',32,bold=True,maxw=290)
        for i in range(7): self.rect((420+i*16,23,428+i*16,31),'accent' if i==6 else 'border',4)
        self.text(678,17,'CONCEPT · DATI DEMO',20,'sub',maxw=258)
        self.rect((24,55,936,56),'border')
        self.text(24,76,title,32,bold=True,maxw=850)
        for i in range(2): self.rect((939,352+i*16,945,358+i*16),'accent' if (title=='Progressi')==bool(i) else 'border',3)
    def button(self,label,x=688,y=548,w=224):
        self.rect((x,y,x+w,y+52),'focus',14,outline='accent',width=2)
        width=self.d.textlength(label,font=self.font(26))/S
        self.text(x+(w-width)/2,y+14,label,26,'accent',maxw=w-16)
    def car(self,x,y,angle=0,lead=False,label=None):
        car=Image.new('RGBA',(42*S,42*S)); d=ImageDraw.Draw(car)
        color=self.c['accent'] if lead else self.c['sub']
        d.rounded_rectangle((7*S,12*S,35*S,29*S),4*S,fill=color)
        d.rectangle((24*S,15*S,27*S,26*S),fill=self.c['surface'])
        d.rectangle((12*S,15*S,18*S,26*S),fill=self.c['surface'])
        car=car.rotate(-angle,resample=Image.Resampling.BICUBIC)
        self.im.paste(car,(round((x-21)*S),round((y-21)*S)),car)
        if label: self.text(x-14,y-51,label,22,'accent',bold=True,maxw=45)
    def track(self,xy=(52,234,620,486),cars=True,champion=False):
        x,y,x2,y2=xy; h=y2-y; w=x2-x; lane=56
        self.rect(xy,'border',h/2,outline='sub')
        self.rect((x+lane,y+lane,x2-lane,y2-lane),'surface',(h-2*lane)/2,outline='sub')
        cy=(y+y2)/2; r=(h-lane)/2; left=x+h/2; right=x2-h/2
        for start in range(int(left),int(right),27):
            for yy in (y+lane/2,y2-lane/2): self.rect((start,yy,start+12,yy+1),'sub')
        for center,initial in ((left,90),(right,-90)):
            box=((center-r)*S,(cy-r)*S,(center+r)*S,(cy+r)*S)
            for deg in range(initial,initial+180,16): self.d.arc(box,deg,deg+7,fill=self.c['sub'],width=2*S)
        finish=(left+right)/2-30
        for row in range(7):
            for col in range(2): self.rect((finish+col*7,y+row*8,finish+(col+1)*7,y+(row+1)*8),'text' if (row+col)%2==0 else 'surface')
        if cars:
            self.car(right-40,y+lane/2,lead=True,label='#1')
            if not champion:
                self.car(left+45,y+lane/2)
                self.car(right+30,y2-lane/2,180)
                self.car(left-r+4,cy+20,-75)
    def arena(self,cars=True,champion=False):
        self.rect((24,120,648,624),'surface',24)
        self.text(48,145,'Ovale',30,bold=True)
        self.text(48,188,'Pista fissa · vista dall’alto',22,'sub',maxw=550)
        self.track(cars=cars,champion=champion)
        self.rect((48,541,62,555),'accent',4)
        self.text(76,537, 'Campione osservato · #1' if champion else 'Auto osservata · #1' if cars else 'Ovale pronto · nessuna sessione',24,maxw=540)
        self.text(48,582,'Modello salvato · pesi fissi' if champion else '32 tentativi · 4 mostrati' if cars else 'Apprendimento locale · avvio manuale',22,'sub',maxw=576)
    def sidebar(self,state):
        self.rect((664,120,936,624),'surface',24)
        titles={'pronto':'Pronto','impara':'Impara','pausa':'In pausa','campione':'Campione','errore':'In pausa'}
        self.text(688,147,titles[state],28,bold=True,maxw=224)
        if state=='pronto':
            self.paragraph(688,201,'L’auto migliora per tentativi. Premi Start.',224)
            self.text(688,342,'Campione',24,'sub')
            self.paragraph(688,382,'Nessun salvataggio',224,24,'text',2)
        elif state=='impara':
            self.text(688,214,'Generazione',24,'sub',maxw=224)
            self.text(688,258,'12',64,bold=True,numeric=True)
            self.text(688,376,'Avanzamento',24,'sub',maxw=224)
            self.text(688,420,'72%',60,bold=True,numeric=True)
        elif state=='pausa':
            self.paragraph(688,201,'Sessione ferma. Riprendi quando vuoi.',224)
            self.text(688,341,'Campione salvato',24,'sub',maxw=224)
            self.text(688,385,'Gen. 12',40,numeric=True,maxw=224)
        elif state=='campione':
            self.paragraph(688,201,'Modello salvato. Pesi fissi.',224)
            self.text(688,341,'Giro migliore',24,'sub',maxw=224)
            self.text(688,385,'18,4 s',54,bold=True,numeric=True,maxw=224)
        else:
            self.paragraph(688,201,'Salvataggio non riuscito.',224,24,'error')
            self.paragraph(688,338,'Il campione precedente è disponibile.',224)
        self.button({'pronto':'5 Start','impara':'5 Pausa','pausa':'5 Riprendi','campione':'5 Pausa','errore':'5 Riprova'}[state])
    def chart(self):
        self.rect((24,120,648,624),'surface',24)
        self.text(48,148,'Avanzamento per generazione',28,bold=True,maxw=576)
        self.text(48,198,'Sessione in pausa · dati demo',22,'sub')
        values=[7,16,14,30,27,44,52,48,63,65,59,72]
        x0,y0,x1,y1=110,288,604,524
        self.text(48,244,'Avanzamento (%)',22,'sub')
        for v in (0,50,100):
            y=y1-v/100*(y1-y0)
            self.rect((x0,y,x1,y+1),'border')
            self.text(52,y-9,str(v),20,'sub',numeric=True)
        pts=[(x0+i*(x1-x0)/(len(values)-1),y1-v/100*(y1-y0)) for i,v in enumerate(values)]
        self.d.line([(round(x*S),round(y*S)) for x,y in pts],fill=self.c['accent'],width=3*S)
        for x,y in pts: self.rect((x-4,y-4,x+4,y+4),'accent',4)
        for i in (0,5,11): self.text(pts[i][0]-7,543,str(i+1),20,'sub',numeric=True)
        self.text(250,578,'Generazione',22,'sub')
        self.rect((664,120,936,624),'surface',24)
        self.text(688,148,'Riepilogo',28,bold=True,maxw=224)
        self.text(688,218,'Giri validi',24,'sub'); self.text(688,262,'—',64,numeric=True)
        self.text(688,375,'Campione salvato',24,'sub',maxw=224); self.text(688,420,'Gen. 12',40,numeric=True,maxw=224)
        self.button('5 Dettagli')
    def overlay(self,urgent=False):
        x,y,w,h=(184,168,592,356) if urgent else (272,126,664,498)
        self.rect((x,y,x+w,y+h),'surface',24,outline='border')
        if urgent:
            self.icon('warning',x+24,y+24,32,color='error')
            self.text(x+70,y+28,'Avviso urgente · DEMO',28,bold=True,maxw=w-94)
            self.paragraph(x+24,y+109,'Il gioco è in pausa. Questo è un esempio di interruzione del sistema.',w-48,26,max_lines=3)
            self.text(x+24,y+238,'Nessun evento reale in corso',22,'sub')
            self.button('7 Chiudi',x+24,y+h-76,220)
        else:
            self.text(x+24,y+24,'Menu · Gioco',30,bold=True)
            rows=['Modalità: Impara','Salva e termina','Velocità: Osserva','Mostra sensori: No','Nuova sessione','Dettagli']
            for i,row in enumerate(rows):
                yy=y+87+i*54
                if i==0: self.rect((x+16,yy-8,x+w-16,yy+39),'focus',14)
                self.text(x+32,yy,row,25,'accent' if i==0 else 'text',maxw=w-64)
            self.text(x+24,y+h-54,'2 / 8 Seleziona · 5 Conferma · 7 Indietro',22,'sub',maxw=w-48)
    def save(self):
        self.im.resize((960,640),Image.Resampling.LANCZOS).save(OUT/(self.name+'.png'))
        return dict(file=self.name+'.png',size=[960,640],scale=self.scale,text_boxes=len(self.boxes),text_within_canvas=all(0<=a<=960 and 0<=c<=960 and 0<=b<=640 and 0<=d<=640 for item in self.boxes for a,b,c,d in [item['box']]),text_fits_assigned_width=all(item['fits_width'] for item in self.boxes))

def contrast(a,b):
    def luminance(color):
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        vals=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v,w in zip(vals,(.2126,.7152,.0722)))
    hi,lo=sorted((luminance(a),luminance(b)),reverse=True)
    return round((hi+.05)/(lo+.05),2)

def main():
    result=[]
    for state in ('pronto','impara','pausa','campione','errore'):
        b=Board(state);b.shell();b.arena(cars=state!='pronto',champion=state=='campione');b.sidebar(state);result.append(b.save())
    b=Board('progressi');b.shell('Progressi');b.chart();result.append(b.save())
    for name in ('menu','urgente'):
        b=Board(name);b.shell();b.arena();b.sidebar('pausa');b.overlay(name=='urgente');result.append(b.save())
    for name,night,scale in [('notte',True,1),('testo-110',False,1.1)]:
        b=Board(name,night,scale);b.shell();b.arena();b.sidebar('impara');result.append(b.save())
    b=Board('pista-ampia');b.shell();b.rect((24,120,936,504),'surface',24);b.text(48,145,'Ovale',30,bold=True);b.text(48,188,'Pista fissa · vista dall’alto',22,'sub');b.track((72,254,888,474));b.rect((24,520,936,624),'surface',24);b.text(48,545,'Impara',28,bold=True);b.text(48,585,'32 tentativi · 4 mostrati',22,'sub');b.text(384,548,'Generazione 12',24,maxw=278);b.text(384,585,'Avanzamento 72%',24,'sub',maxw=278);b.button('5 Pausa',688,548);result.append(b.save())
    contrasts={name:{f'{role}/surface':contrast(c[role],c['surface']) for role in ('text','sub','accent','error')} for name,c in [('day',DAY),('night',NIGHT)]}
    for name,c in [('day',DAY),('night',NIGHT)]:
        contrasts[name]['accent/focus']=contrast(c['accent'],c['focus'])
        contrasts[name]['text/background']=contrast(c['text'],c['bg'])
    report=dict(scope='Offline concept only; no simulation, Qt runtime, physical panel or NPU performance verification.',data='Invented fixtures, visibly marked CONCEPT / DATI DEMO.',boards=result,contrast_ratios=contrasts,geometry='Native 960x640; recommended cards 624x504 and 272x504; 16px gap; 24px margins.',manual_visual_review='pending',interactive_review='pending',runtime_gates='S1–S5 open')
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert all(r['text_within_canvas'] and r['text_fits_assigned_width'] for r in result), result
    print(json.dumps(dict(boards=len(result),all_text_fits=True,contrasts=contrasts),ensure_ascii=False))

if __name__=='__main__':main()
