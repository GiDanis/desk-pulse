"""Render graphic concepts, not application screens. Offline, fixed 960 x 640."""
from pathlib import Path
import json
import math
import os
import re
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPen, QColor, QFont, QFontDatabase, QFontMetricsF, QPainterPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BUNDLE = ROOT / 'theme-projects/apple-calm/bundle'
APP = QGuiApplication([])
FONTS = {}
for role, name in [('ui','Cantarell-VF.otf'), ('numbers','LiberationSans-Regular.ttf'), ('display','LiberationSans-Bold.ttf')]:
    font_id = QFontDatabase.addApplicationFont(str(BUNDLE / 'fonts' / name))
    assert font_id >= 0, name
    FONTS[role] = QFontDatabase.applicationFontFamilies(font_id)[0]
THEME = json.loads((BUNDLE / 'theme.json').read_text())
ICON_JS = (BUNDLE / 'qml/IconPaths.js').read_text()
ICON_NAMES = json.loads(re.search(r'var names = (\[.*?\]);', ICON_JS).group(1))
ICON_COLORS = json.loads(re.search(r'var colors = (\[.*?\]);', ICON_JS).group(1))
ATLAS = QImage(str(BUNDLE / 'qml/icon-atlas.png'))
assert not ATLAS.isNull()

def small(title, value, note, icon='info', size=46, previous=False):
    return dict(title=title, value=value, note=note, icon=icon, size=size, previous=previous)

SCENES = [
 dict(id='sport-calcio',topic='SPORT',view='Calcio',icon='trophy',page=0,source='Sport · dati dimostrativi',hero=dict(kind='match',label='Serie A · partita di esempio',main='2 – 1',teams='Inter — Roma',status='Secondo tempo · 67′',foot='Feed demo · rilevato 15 s fa',icon='football'),tiles=[small('Prossima','Dom · 18:00','Lazio — Inter','calendar',34),small('La mia squadra','4ª','14 punti · Serie A','football',62),small('Ultimo esito','3 – 0','Milan — Inter · conclusa','flag',48),small('Altre partite','2 live','Feed demo qualificato','football',42)]),
 dict(id='sport-f1',topic='SPORT',view='Formula 1',icon='trophy',page=1,source='Motorsport · dati dimostrativi',hero=dict(kind='event',label='GP di esempio · Formula 1',main='16:00',teams='Qualifiche',status='Sabato · ora locale',foot='In programma · live non verificato',icon='race-car'),tiles=[small('Gara','Dom · 15:00','Orario locale','calendar',34),small('Prossimo GP','Catalunya','Calendario dimostrativo','flag',33),small('Ultima sessione','Pilota A','Prove libere · P1','race-car',34),small('Campionato','250 pt','Pilota B · leader','trophy',44)]),
 dict(id='sport-motogp',topic='SPORT',view='MotoGP',icon='trophy',page=2,source='Motorsport · dati dimostrativi',hero=dict(kind='event',label='GP di esempio · classe MotoGP',main='12 / 24',teams='Gara in corso',status='Giro corrente · timing demo',foot='Diretta verificata nel dato simulato',icon='motorcycle'),tiles=[small('In testa','Pilota C','Posizione 1 · MotoGP','motorcycle',34),small('Distacco','+0,8 s','Pilota D · P2','flag',46),small('Ultima sessione','Sprint','Risultati di ieri','calendar',42),small('Mondiale','Pilota E','Classifica della stagione','trophy',34)]),
 dict(id='casa-preferiti',topic='CASA',view='Preferiti',icon='connected-home',page=0,source='Tuya · lettura demo · 2 min fa',grid=True,tiles=[small('Sensore soggiorno','22,4 °C','Umidità 48% · cloud online','thermometer',58),small('Lampada studio','Accesa','Stato riportato · sola lettura','lightbulb',52),small('Presa PC','48 W','Potenza istantanea riportata','plug',58),small('Sensore ingresso','Dato precedente','Movimento: ultima osservazione','motion',34,True)]),
 dict(id='casa-ambiente',topic='CASA',view='Ambiente',icon='connected-home',page=1,source='Tuya · sensori demo · 2 min fa',hero=dict(kind='number',label='Temperatura · sensore soggiorno',main='22,4°',teams='Soggiorno',status='Disponibile secondo cloud',foot='Misura del sensore · 2 min fa',icon='thermometer'),tiles=[small('Umidità','48%','Sensore soggiorno','droplet',58),small('Studio','20,8°','Temperatura del sensore','thermometer',58),small('Ingresso','Nessun moto','Stato riportato dal sensore','motion',31),small('Sensori letti','3','Letture demo disponibili','source',62)]),
 dict(id='casa-dispositivi',topic='CASA',view='Dispositivi',icon='connected-home',page=2,source='Tuya · catalogo dimostrativo',hero=dict(kind='number',label='Catalogo Casa',main='4',teams='Dispositivi riportati',status='3 cloud online · 1 precedente',foot='Disponibilità secondo cloud',icon='connected-home'),tiles=[small('Preferiti','4','Dispositivi scelti','star',62),small('Luci','1','Lampada nel catalogo','lightbulb',62),small('Prese','1','Presa nel catalogo','plug',62),small('Sensori','2','Due dispositivi sensore','thermometer',62)]),
 dict(id='rete-traffico',topic='RETE',view='Traffico',icon='network',page=0,source='iliadbox · lettura demo · 15 s fa',hero=dict(kind='traffic',label='Traffico WAN',main='42,8',teams='Download · Mbit/s',status='Upload · 3,1 Mbit/s',foot='Traffico aggregato · non speed test',icon='network'),chart=True,tiles=[small('Stato WAN','Attiva','Secondo iliadbox','router',42),small('Capacità box','1 Gbit/s','Riportata · non misurata','ethernet',38)]),
 dict(id='rete-iliadbox',topic='RETE',view='iliadbox',icon='network',page=1,source='iliadbox · catalogo demo · 2 min fa',hero=dict(kind='number',label='Uptime router',main='2 giorni',teams='WAN attiva',status='Stato riportato da iliadbox',foot='Catalogo demo · letto 2 min fa',icon='router'),tiles=[small('Sensore T1','51 °C','Sensore box · non Orange Pi','thermometer',56),small('Wi-Fi','2 radio','Catalogo riportato','wifi',43),small('Ethernet','3 porte','Una con link up · demo','ethernet',43),small('Firmware','Demo','Versione riportata dalla box','info',43)]),
 dict(id='rete-dispositivi',topic='RETE',view='Dispositivi',icon='network',page=2,source='Inventario router · dati dimostrativi',hero=dict(kind='inventory',label='Inventario router',main='12',teams='Record riportati',status='8 raggiungibili secondo box',foot='Copertura parziale · demo',icon='network'),tiles=[small('PC studio','Raggiungibile','Secondo box · preferito','display',30),small('Stampante','Non raggiung.','Secondo box · preferita','network',29),small('NAS','Raggiungibile','Record del router','network',30),small('PC portatile','Precedente','Presenza non verificata','display',32,True)]),
]

class Board:
    def __init__(self, scene, mode, palette):
        self.scene, self.mode, self.palette = scene, mode, palette
        self.image = QImage(960,640,QImage.Format.Format_ARGB32_Premultiplied)
        tokens = dict(THEME['tokens'])
        tokens.update(THEME['palettes'].get(palette,{}))
        self.c = {key:tokens['colors.'+value] for key,value in [('bg','background'),('card','surface'),('text','textPrimary'),('muted','textSecondary'),('border','border'),('accent','accent')]}
        self.c['warning'] = tokens['semantic.warningOnCard']
        self.image.fill(QColor(self.c['bg']))
        self.p = QPainter(self.image)
        self.p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.issues=[]
        self.regions=[]

    def text(self, text, x, y, w, h, size=26, color='text', role='ui', bold=False, align=Qt.AlignmentFlag.AlignLeft, wrap=False):
        rect=QRectF(x,y,w,h)
        f=QFont(FONTS[role]);f.setPixelSize(size);f.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
        self.p.setFont(f);self.p.setPen(QColor(self.c[color]))
        flags=align | Qt.AlignmentFlag.AlignVCenter
        if wrap:flags|=Qt.TextFlag.TextWordWrap
        bounds=QFontMetricsF(f).boundingRect(rect,int(flags),text)
        if bounds.width()>w+1 or bounds.height()>h+1:self.issues.append(dict(text=text,allocated=[w,h],needed=[bounds.width(),bounds.height()]))
        self.p.drawText(rect,int(flags),text)

    def icon(self,name,x,y,size=32):
        cell=ICON_COLORS.index(self.c['accent'].upper())*len(ICON_NAMES)+ICON_NAMES.index(name)
        self.p.drawImage(QRectF(x,y,size,size),ATLAS,QRectF(cell%25*48,cell//25*48,48,48))

    def card(self,x,y,w,h):
        self.p.setPen(QPen(QColor(self.c['border']),1));self.p.setBrush(QColor(self.c['card']))
        self.p.drawRoundedRect(QRectF(x+.5,y+.5,w-1,h-1),24,24)
        self.regions.append([x,y,w,h])

    def tile(self,row,x,y,w,h):
        self.card(x,y,w,h);self.icon(row['icon'],x+20,y+22,28)
        self.text(row['title'],x+60,y+12,w-80,64,25,wrap=True)
        self.text(row['value'],x+20,y+84,w-40,h-162,row['size'],color='warning' if row['previous'] else 'text',role='numbers',bold=True,wrap=True)
        self.text(row['note'],x+20,y+h-74,w-40,62,23,color='warning' if row['previous'] else 'muted',wrap=True)

    def hero(self,hero,x,y,w,h):
        self.card(x,y,w,h);self.icon(hero['icon'],x+24,y+22,36)
        self.text(hero['label'],x+78,y+14,w-102,60,24,'muted',wrap=True)
        self.text(hero['teams'],x+24,y+97,w-48,82,34,bold=True,wrap=True)
        self.text(hero['main'],x+24,y+192,w-48,116,86 if len(hero['main'])<7 else 68,role='display')
        self.text(hero['status'],x+24,y+324,w-48,88,27,'accent' if hero['kind']=='match' else 'text',wrap=True)
        self.text(hero['foot'],x+24,y+h-64,w-48,49,22,'warning' if hero['kind']=='inventory' else 'muted',wrap=True)

    def chart(self,x,y,w,h):
        self.card(x,y,w,h);self.icon('history',x+20,y+20,28)
        self.text('WAN · ultima ora',x+60,y+14,w-80,40,25)
        self.text('↓ Download',x+94,y+56,160,34,22,'accent')
        self.text('↑ Upload',x+280,y+56,150,34,22,'muted')
        gx,gy,gw,gh=x+70,y+105,w-94,94
        for v in [0,25,50]:
            yy=gy+gh-v/50*gh
            self.p.setPen(QPen(QColor(self.c['border']),1));self.p.drawLine(QPointF(gx,yy),QPointF(gx+gw,yy))
            self.text(str(v),x+16,yy-14,42,28,20,'muted',align=Qt.AlignmentFlag.AlignRight)
        down=[12,16,15,29,24,28,42,37,40,32,45,42.8]
        up=[1.2,1.5,1.3,2.4,1.8,2.3,3.1,2.8,2.9,2.6,3.4,3.1]
        for vals,c in [(down,'accent'),(up,'muted')]:
            path=QPainterPath()
            for i,v in enumerate(vals):
                point=QPointF(gx+i/(len(vals)-1)*gw,gy+gh-v/50*gh)
                if i==0:path.moveTo(point)
                else:path.lineTo(point)
            self.p.setBrush(Qt.BrushStyle.NoBrush);self.p.setPen(QPen(QColor(self.c[c]),2.5));self.p.drawPath(path)
        self.text('Mbit/s',x+16,y+60,64,28,19,'muted')
        self.text('−60 min',gx,y+h-37,100,28,20,'muted')
        self.text('Adesso',gx+gw-100,y+h-37,100,28,20,'muted',align=Qt.AlignmentFlag.AlignRight)

    def draw(self):
        s=self.scene
        self.icon(s['icon'],24,13,28);self.text(s['topic'],64,5,350,46,32,bold=True)
        for i in range(6):
            self.p.setPen(Qt.PenStyle.NoPen);self.p.setBrush(QColor(self.c['accent'] if i=={'SPORT':3,'CASA':4,'RETE':5}[s['topic']] else self.c['border']));self.p.drawEllipse(QPointF(430+i*20,28),5 if i=={'SPORT':3,'CASA':4,'RETE':5}[s['topic']] else 3,5 if i=={'SPORT':3,'CASA':4,'RETE':5}[s['topic']] else 3)
        self.text('CONCEPT · DEMO',720,8,216,40,21,'muted',align=Qt.AlignmentFlag.AlignRight)
        self.p.setPen(QPen(QColor(self.c['border']),1));self.p.drawLine(24,55,936,55)
        self.text(s['view'],24,70,310,42,32,bold=True)
        self.text(s['source'],350,74,586,34,22,'muted',align=Qt.AlignmentFlag.AlignRight)
        for i in range(3):
            self.p.setPen(Qt.PenStyle.NoPen);self.p.setBrush(QColor(self.c['accent'] if i==s['page'] else self.c['border']));self.p.drawEllipse(QPointF(945,326+i*20),4 if i==s['page'] else 3,4 if i==s['page'] else 3)
        if s.get('grid'):
            for i,row in enumerate(s['tiles']):self.tile(row,24+(i%2)*464,120+(i//2)*260,448,244)
        elif self.mode=='mosaic':
            h=s['hero'];lead=small(h['teams'],h['main'],h['status'],h['icon'],66)
            if s.get('chart'):
                self.tile(lead,24,120,448,244)
                self.tile(s['tiles'][0],488,120,448,244)
                self.tile(s['tiles'][1],24,380,448,244)
                self.chart(488,380,448,244)
            else:
                rows=[lead]+s['tiles'][:3]
                for i,row in enumerate(rows):self.tile(row,24+(i%2)*464,120+(i//2)*260,448,244)
        else:
            self.hero(s['hero'],24,120,400,504)
            if s.get('chart'):
                self.chart(440,120,496,244)
                for i,row in enumerate(s['tiles']):self.tile(row,440+i*256,380,240,244)
            else:
                for i,row in enumerate(s['tiles']):self.tile(row,440+(i%2)*256,120+(i//2)*260,240,244)
        self.p.end()
        name=s['id']+'-'+self.mode+'-'+self.palette
        assert self.image.save(str(HERE/(name+'.png')),'PNG')
        assert self.image.save(str(HERE/(name+'.webp')),'WEBP',90)
        return dict(id=s['id'],layout=self.mode,palette=self.palette,png=name+'.png',webp=name+'.webp',size=[960,640],textIssues=self.issues,cards=self.regions)

if __name__=='__main__':
    reports=[Board(s,mode,palette).draw() for s in SCENES for mode in ['focus','mosaic'] for palette in ['day','night']]
    (HERE/'scene-data.json').write_text(json.dumps(SCENES,ensure_ascii=False,indent=2)+'\n')
    report={'scope':'Offline graphic concepts with synthetic data; not QML application screenshots','canvas':[960,640],'fonts':FONTS,'existingIconAtlasReused':True,'renders':reports,'textIssues':sum(len(r['textIssues']) for r in reports)}
    (HERE/'render-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'renders':len(reports),'textIssues':report['textIssues'],'webpBytes':sum((HERE/r['webp']).stat().st_size for r in reports)},indent=2))
