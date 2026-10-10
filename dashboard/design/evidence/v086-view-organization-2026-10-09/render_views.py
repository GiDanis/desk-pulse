"""Native 960x640 graphic studies. Synthetic data; no QML or provider calls."""
from pathlib import Path
import importlib.util
import json
from copy import deepcopy

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'v086-graphic-study-2026-10-09'
spec=importlib.util.spec_from_file_location('graphic_base',PREVIOUS/'render_graphic_study.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPen,QColor
PLAN=json.loads((HERE/'view-organization.json').read_text())
PLANS={v['id']:v for v in PLAN['views']}
SMALL=base.small

EXTRA=[
 dict(id='oggi-ora',topic='OGGI',view='Ora',icon='home',page=0,source='Venerdì 9 ottobre · demo',template='now'),
 dict(id='oggi-orologio',topic='OGGI',view='Orologio',icon='home',page=1,source='Venerdì 9 ottobre · demo',template='clock'),
 dict(id='oggi-giornata',topic='OGGI',view='Giornata',icon='home',page=2,source='Evento e meteo · demo',template='day',hero=dict(kind='event',label='Prossimo evento · esempio',teams='Qualifiche F1',main='16:00',status='Oggi · GP di esempio',foot='Programma demo · ora locale',icon='race-car')),
 dict(id='meteo-adesso',topic='METEO',view='Adesso',icon='sun',page=0,source='Località demo · Open-Meteo',hero=dict(kind='number',label='Condizioni correnti · demo',teams='Sereno',main='23°',status='Percepita · 24 °C',foot='Open-Meteo · lettura demo 2 min fa',icon='sun'),tiles=[SMALL('Vento','12 km/h','Direzione NE','wind',38),SMALL('Umidità','48%','Umidità relativa','droplet',58),SMALL('Raffiche','18 km/h','Periodo del provider','wind',38),SMALL('Precipitazioni','0,0 mm','Intervallo del dato','rain',42)]),
 dict(id='meteo-previsioni',topic='METEO',view='Previsioni',icon='sun',page=1,source='Tre giorni · modello demo',template='forecast'),
 dict(id='account-utilizzo',topic='ACCOUNT',view='Utilizzo',icon='account',page=0,source='Codex · lettura demo 2 min fa',template='account'),
]
SCENES=deepcopy(base.SCENES)
for s in SCENES:
    if s['id']=='rete-iliadbox':s['hero'].update(label='Stato router',teams='WAN iliadbox',main='Attiva',status='Uptime · 2 giorni')
    if s['id']=='sport-f1':s['tiles'][0]['title']='Successiva'
    if s['id']=='sport-calcio':s['tiles'][1]['title']='Squadra'
SCENES=EXTRA+SCENES

class StudyBoard(base.Board):
    def header(self):
        s=self.scene
        self.icon(s['icon'],24,13,28);self.text(s['topic'],64,5,340,46,32,bold=True)
        active={'OGGI':0,'METEO':1,'ACCOUNT':2,'SPORT':3,'CASA':4,'RETE':5}[s['topic']]
        for i in range(6):
            self.p.setPen(Qt.PenStyle.NoPen);self.p.setBrush(QColor(self.c['accent'] if i==active else self.c['border']));self.p.drawEllipse(QPointF(430+i*20,28),5 if i==active else 3,5 if i==active else 3)
        self.text('CONCEPT · DEMO',720,8,216,40,21,'muted',align=Qt.AlignmentFlag.AlignRight)
        self.p.setPen(QPen(QColor(self.c['border']),1));self.p.drawLine(24,55,936,55)
        self.text(s['view'],24,70,310,42,32,bold=True)
        self.text(s['source'],350,74,586,34,22,'muted',align=Qt.AlignmentFlag.AlignRight)

    def hero(self,h,x,y,w,height):
        self.card(x,y,w,height);self.icon(h['icon'],x+24,y+22,36)
        self.text(h['label'],x+78,y+14,w-102,60,24,'muted',wrap=True)
        if h['kind']=='traffic':
            self.text('Download · Mbit/s',x+24,y+112,w-48,52,30)
            self.text(h['main'],x+24,y+179,w-48,112,86,role='display')
            self.text('Upload · Mbit/s',x+24,y+312,w-48,46,28)
            self.text('3,1',x+24,y+365,w-48,70,50,role='display')
            self.text(h['foot'],x+24,y+height-62,w-48,48,22,'muted',wrap=True)
            return
        self.text(h['teams'],x+24,y+97,w-48,82,34,bold=True,wrap=True)
        self.text(h['main'],x+24,y+192,w-48,116,PLANS[self.scene['id']]['blocks'][0]['valuePx'],role='display')
        self.text(h['status'],x+24,y+324,w-48,88,27,'accent' if h['kind']=='match' else 'text',wrap=True)
        self.text(h['foot'],x+24,y+height-64,w-48,49,22,'warning' if h['kind']=='inventory' else 'muted',wrap=True)

    def compact(self,title,value,note,x,y,w,h,icon,size=38):
        self.card(x,y,w,h);self.icon(icon,x+20,y+20,28)
        self.text(title,x+60,y+10,w-80,46,25)
        self.text(value,x+20,y+53,w-40,60,size,role='numbers',bold=True)
        self.text(note,x+20,y+h-46,w-40,36,22,'muted')

    def weather(self,x,y,w,h):
        self.card(x,y,w,h);self.icon('sun',x+24,y+22,44)
        self.text('Meteo',x+80,y+18,w-104,54,28,bold=True)
        self.text('23°',x+24,y+110,w-48,116,80,role='display')
        self.text('Sereno',x+24,y+244,w-48,54,34)
        self.text('Percepita · 24 °C',x+24,y+315,w-48,60,27,wrap=True)
        self.text('Open-Meteo · demo\nLetto 2 min fa',x+24,y+h-84,w-48,68,22,'muted',wrap=True)

    def draw(self):
        s=self.scene;self.header();template=s.get('template','focus')
        if template=='now':
            self.text('12:41',24,168,536,224,152,role='display')
            self.card(24,454,536,170);self.icon('calendar',44,474,28)
            self.text('Prossimo evento · demo',84,467,452,42,25,'muted')
            self.text('Qualifiche F1',44,511,496,54,34,bold=True)
            self.text('Oggi · 16:00 · GP di esempio',44,570,496,42,25,'muted')
            self.weather(576,120,360,504)
        elif template=='clock':
            self.text('12:41',24,144,912,302,224,role='numbers',align=Qt.AlignmentFlag.AlignHCenter)
            self.compact('Meteo','23° · Sereno','Open-Meteo · demo',24,476,448,148,'sun',36)
            self.compact('Prossimo evento','Qualifiche F1','Oggi · 16:00 · demo',488,476,448,148,'calendar',30)
        elif template=='day':
            self.hero(s['hero'],24,120,400,504)
            self.tile(SMALL('Meteo oggi','25° / 16°','Massima / minima · sereno','sun',62),440,120,496,244)
            self.tile(SMALL('Prob. pioggia','20%','Massimo del giorno','rain',52),440,380,240,244)
            self.tile(SMALL('Vento','12 km/h','Adesso · NE','wind',38),696,380,240,244)
        elif template=='forecast':
            for i,(day,high,low,desc,rain,icon) in enumerate([('Oggi · 9','25°','16°','Sereno','20%','sun'),('Sab 10','22°','15°','Nuvoloso','40%','cloud'),('Dom 11','20°','14°','Pioggia','80%','rain')]):
                x=24+i*928/3;w=880/3;self.card(x,120,w,504)
                self.text(day,x+20,134,w-40,46,32,bold=True)
                self.icon(icon,x+20,203,48);self.text('Massima',x+86,202,w-106,40,24,'muted')
                self.text(high,x+20,252,w-40,82,62,role='display')
                self.text('Minima · '+low,x+20,342,w-40,50,32)
                self.text(desc,x+20,406,w-40,42,27)
                self.text('Prob. pioggia',x+20,470,w-40,38,24,'muted')
                self.text(rain,x+20,511,w-40,60,48,role='numbers',bold=True)
                self.text('Max giorno · demo',x+20,576,w-40,36,22,'muted')
        elif template=='account':
            for i,(duration,value,reset) in enumerate([('5 ore',42,'Oggi · 16:30'),('7 giorni',73,'Lun 12 · 09:00')]):
                x=24+i*464;self.card(x,120,448,324);self.icon('account',x+22,142,30)
                self.text('Codex · '+duration,x+68,134,356,52,26,bold=True)
                self.text(str(value)+'%',x+22,205,404,100,80,role='display')
                self.text('Utilizzato',x+22,311,404,36,25,'muted')
                self.p.setPen(Qt.PenStyle.NoPen);self.p.setBrush(QColor(self.c['border']));self.p.drawRoundedRect(QRectF(x+22,361,404,10),5,5)
                self.p.setBrush(QColor(self.c['accent']));self.p.drawRoundedRect(QRectF(x+22,361,404*value/100,10),5,5)
                self.text('Reset · '+reset,x+22,387,404,46,25,'muted')
            self.compact('Crediti disponibili','120','Saldo demo riportato',24,460,448,164,'account')
            self.compact('Reset disponibili','2','Conteggio demo riportato',488,460,448,164,'refresh')
        elif s.get('grid'):
            for i,row in enumerate(s['tiles']):self.tile(row,24+i%2*464,120+i//2*260,448,244)
        else:
            self.hero(s['hero'],24,120,400,504)
            if s.get('chart'):
                self.chart(440,120,496,244)
                for i,row in enumerate(s['tiles']):self.tile(row,440+i*256,380,240,244)
            else:
                for i,row in enumerate(s['tiles']):self.tile(row,440+i%2*256,120+i//2*260,240,244)
        self.p.end();name=s['id']+'-'+self.palette
        assert self.image.save(str(HERE/(name+'.png')),'PNG')
        assert self.image.save(str(HERE/(name+'.webp')),'WEBP',90)
        return dict(id=s['id'],palette=self.palette,size=[960,640],png=name+'.png',webp=name+'.webp',textIssues=self.issues,cards=self.regions)

if __name__=='__main__':
    reports=[StudyBoard(s,'focus',palette).draw() for s in SCENES for palette in ['day','night']]
    report={'scope':'Synthetic graphic concepts; not QML/runtime screenshots','renders':reports,'textIssues':sum(len(r['textIssues']) for r in reports)}
    (HERE/'render-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'renders':len(reports),'textIssues':report['textIssues'],'dayWebpBytes':sum((HERE/r['webp']).stat().st_size for r in reports if r['palette']=='day')}))
