"""Private, normalized read-only router metrics and independent source states."""
from copy import deepcopy
from contextlib import closing
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from iliadbox import NetworkError
from network_core import text, stamp
from network_history import number, history, counter_rate

FAST_INTERVAL = 30  # Board-proven conservative rate, additional I/O only in view.


def opaque(scope, kind, raw):
    return hashlib.sha256((scope+':'+kind+':'+str(raw)).encode()).hexdigest()[:24]


def rate(value):
    v=number(value)
    if v is None:return 'Non disponibile'
    if v>=1e9:return f'{v/1e9:.2f} Gbit/s'
    if v>=1e6:return f'{v/1e6:.2f} Mbit/s'
    return f'{v/1000:.1f} kbit/s'


def scalar(value, unit='', scale=1):
    n=number(value,negative=unit in ('dBm','dB','°C'))
    return f'{n*scale:g} {unit}'.strip() if n is not None else 'Non disponibile'


def valid_cap(key, cap):
    """Validate the complete persisted whitelist before accepting any capability."""
    def obj(v, fields):
        return isinstance(v,dict) and set(v)==set(fields.split())
    def string(v):return isinstance(v,str) and len(v)<=256
    def num(v, negative=False):return v is None or number(v,negative=negative) is not None
    def items(v, maximum, fields, check):
        return isinstance(v,list) and len(v)<=maximum and all(obj(r,fields) and check(r) for r in v)
    def simple(v):
        if v is None or type(v) is bool:return True
        if isinstance(v,str):return len(v)<=256
        if type(v) in (int,float):return number(v,negative=True) is not None
        if isinstance(v,list):return len(v)<=256 and all(simple(x) for x in v)
        return isinstance(v,dict) and len(v)<=32 and all(string(k) and simple(x) for k,x in v.items())
    if not obj(cap,'status at error data') or cap['status'] not in ('active','stale','error','unavailable') or not string(cap['error']) or number(cap['at']) is None or cap['at']>4102444800:return False
    v=cap['data']
    if not simple(v):return False
    if key=='wan':return isinstance(v,dict) and set(v)<=set('state media rate_up rate_down bandwidth_up bandwidth_down'.split()) and all(string(x) if k in ('state','media') else num(x) for k,x in v.items())
    if key=='catalog:system':return obj(v,'firmware uptime sensors fans') and string(v['firmware']) and num(v['uptime']) and all(items(v[k],n,'id name value',lambda x:string(x['id']) and string(x['name']) and num(x['value'])) for k,n in [('sensors',32),('fans',16)])
    if key=='catalog:fibre':return isinstance(v,dict) and set(v)<=set('link sfp_has_power_report sfp_pwr_rx sfp_pwr_tx'.split()) and all(type(x) is bool if k in ('link','sfp_has_power_report') else num(x,True) for k,x in v.items())
    if key=='catalog:update':return obj(v,'state') and string(v['state'])
    if key=='catalog:planning':return obj(v,'enabled mode') and (v['enabled'] is None or type(v['enabled']) is bool) and string(v['mode'])
    if key=='catalog:radios':return items(v,8,'id raw_id name band channel width state',lambda x:all(string(y) for y in x.values()) and bool(re.fullmatch(r'[a-f0-9]{24}',x['id'])))
    if key=='catalog:ports':return items(v,16,'id raw_id rrd_id name link speed duplex hosts macCount',lambda x:all(string(x[k]) for k in ('id','raw_id','rrd_id','name','link','speed','duplex')) and type(x['macCount']) is int and 0<=x['macCount']<=256 and items(x['hosts'],256,'id name',lambda h:all(string(y) for y in h.values())))
    if re.fullmatch(r'stations:[a-f0-9]{24}',key):return items(v,256,'id name hostId state signal rxLink txLink duration rxBytes txBytes upRate downRate',lambda x:all(string(x[k]) for k in ('id','name','hostId','state')) and num(x['signal'],True) and all(num(x[k]) for k in ('rxLink','txLink','duration','upRate','downRate')) and all(x[k] is None or type(x[k]) is int and x[k]>=0 for k in ('rxBytes','txBytes')))
    if re.fullmatch(r'port:[a-f0-9]{24}',key):return obj(v,'rx_good_bytes tx_bytes rx_bytes_rate tx_bytes_rate') and all(num(x) for x in v.values())
    if re.fullmatch(r'history:(net|temp|switch):(1|24)',key):
        if not obj(v,'start end resolution series rawPoints') or not all(num(v[k]) and v[k] is not None for k in ('start','end','resolution')) or not 0<v['start']<=v['end']<=4102444800 or type(v['rawPoints']) is not int or not 0<=v['rawPoints']<=10000:return False
        def series(x):
            return all(string(x[k]) for k in ('id','label','unit')) and num(x['minimum'],True) and num(x['maximum'],True) and type(x['gaps']) is int and 0<=x['gaps']<=10000 and items(x['points'],180,'id time value breakBefore',lambda p:string(p['id']) and num(p['time']) and p['time'] is not None and v['start']<=p['time']<=v['end'] and num(p['value'],True) and type(p['breakBefore']) is bool) and all(a['time']<b['time'] for a,b in zip(x['points'],x['points'][1:]))
        return items(v['series'],32,'id label unit points minimum maximum gaps',series)
    return False


class MetricsStore:
    def __init__(self,directory,scope):
        if not re.fullmatch(r'[a-f0-9]{24}|demo',scope):raise NetworkError('storage','Scope metriche non valido.')
        self.directory=Path(directory);self.scope=scope;self.path=self.directory/(scope+'.sqlite3')

    def _connect(self):
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700);self.directory.chmod(0o700)
        c=sqlite3.connect(self.path,timeout=1);self.path.chmod(0o600)
        c.execute('CREATE TABLE IF NOT EXISTS metrics (key TEXT PRIMARY KEY, value TEXT NOT NULL, used REAL NOT NULL)')
        return c

    def save(self, caps):
        try:
            with closing(self._connect()) as c, c:
                for key,cap in caps.items():
                    if not valid_cap(key,cap):raise ValueError('invalid capability')
                    value=json.dumps({'version':1,'scope':self.scope,'cap':cap},allow_nan=False)
                    if len(value.encode())>4*1024*1024:raise ValueError('oversize')
                    c.execute('INSERT OR REPLACE INTO metrics VALUES(?,?,?)',(key,value,time.time()))
                for catalog,prefix in (('catalog:radios','stations:'),('catalog:ports','port:')):
                    if catalog in caps:
                        allowed={prefix+r['id'] for r in caps[catalog]['data']}
                        retired=[(k,) for k, in c.execute('SELECT key FROM metrics WHERE key LIKE ?',(prefix+'%',)).fetchall() if k not in allowed]
                        c.executemany('DELETE FROM metrics WHERE key=?',retired)
                # Bound history independently of fixed capability snapshots.
                old=c.execute("SELECT key FROM metrics WHERE key LIKE 'history:%' ORDER BY used DESC").fetchall()[24:]
                c.executemany('DELETE FROM metrics WHERE key=?',old)
                while c.execute('SELECT coalesce(sum(length(value)),0) FROM metrics').fetchone()[0]>8*1024*1024:
                    row=c.execute("SELECT key FROM metrics WHERE key LIKE 'history:%' ORDER BY used LIMIT 1").fetchone()
                    if not row:raise ValueError('oversize cache')
                    c.execute('DELETE FROM metrics WHERE key=?',row)
        except (OSError,sqlite3.Error,ValueError):raise NetworkError('storage','Archivio metriche non scrivibile; dati non confermati.') from None

    def load(self):
        try:
            c=self._connect()
            try:rows=c.execute('SELECT key,value FROM metrics').fetchall()
            finally:c.close()
            if len(rows)>300 or sum(len(v) for _,v in rows)>8*1024*1024:raise ValueError('oversize')
            caps={}
            for key,value in rows:
                v=json.loads(value)
                cap=v.get('cap')
                if v.get('version')!=1 or v.get('scope')!=self.scope or not valid_cap(key,cap):raise ValueError('shape')
                cap['status']='stale';cap['error']='';caps[key]=cap
            return caps
        except (OSError,sqlite3.Error,ValueError,TypeError,AttributeError):raise NetworkError('storage','Archivio metriche non leggibile; inventario conservato.') from None


def cap_collect(client, caps, inventory, route, entity, section, hours, now):
    """One client/session in the existing service's single worker."""
    result=deepcopy(caps);updates={}
    client.deadline=time.monotonic()+20
    hosts=inventory['devices'];by_host={(h['interface'],h['hostId']):h for h in hosts if h['present']}
    def get(key,path,normalize,ttl=FAST_INTERVAL,force=False):
        old=result.get(key,{})
        if not force and key.startswith('catalog:') and old.get('status')=='active' and 0<=now-old.get('at',0)<600:return old['data']
        try:
            raw=client.get(path)
            if raw is None:raise NetworkError('unavailable','Fonte metriche non disponibile.')
            data=normalize(raw)
            cap={'status':'active','at':now,'error':'','data':data};result[key]=cap;updates[key]=cap
            return data
        except NetworkError as e:
            if e.kind in ('auth','identity','tls','cancelled'):raise
            result[key]={'status':'error' if e.kind!='unavailable' else 'unavailable','at':old.get('at',0),'error':str(e),'data':old.get('data',{})}
            return None
    def obj(raw):
        if not isinstance(raw,dict):raise NetworkError('invalid','Oggetto metriche non valido.')
        return raw
    def listing(raw,limit):
        if not isinstance(raw,list) or len(raw)>limit or any(not isinstance(r,dict) for r in raw):raise NetworkError('invalid','Elenco metriche non valido.')
        return raw
    def wan(raw):
        r=obj(raw)
        return {**{k:text(r.get(k)) for k in ('state','media')},**{k:number(r.get(k)) for k in ('rate_up','rate_down','bandwidth_up','bandwidth_down')}}
    def system(raw):
        r=obj(raw)
        return {'firmware':text(r.get('firmware_version')),'uptime':number(r.get('uptime_val')),'sensors':[{'id':text(s.get('id')),'name':text(s.get('name')),'value':number(s.get('value'))} for s in listing(r.get('sensors',[]),32)],'fans':[{'id':text(s.get('id')),'name':text(s.get('name')),'value':number(s.get('value'))} for s in listing(r.get('fans',[]),16)]}
    def radios(raw):
        rows=[]
        for r in listing(raw,8):
            rid=str(r.get('id',''));cfg=r.get('config',{});st=r.get('status',{})
            if not rid or not isinstance(cfg,dict) or not isinstance(st,dict):raise NetworkError('invalid','Radio non valida.')
            rows.append({'id':opaque(client.scope,'ap',rid),'raw_id':rid,'name':text(r.get('name')) or 'Radio '+rid,'band':{'2d4g':'2,4 GHz','5g':'5 GHz','6g':'6 GHz'}.get(cfg.get('band'),'Banda non disponibile'),'channel':scalar(st.get('primary_channel')),'width':text(str(st.get('channel_width',''))),'state':text(st.get('state'))})
        return rows
    def ports(raw):
        rows=[]
        for r in listing(raw,16):
            rid=str(r.get('id',''))
            if not rid:raise NetworkError('invalid','Porta non valida.')
            matches=[]
            for entry in listing(r.get('mac_list',[]),256):
                mac=text(entry.get('mac')).upper();found=[h for h in hosts if h['present'] and h['mac']==mac]
                if len(found)==1:matches.append({'id':found[0]['id'],'name':text(found[0]['name'])})
            rows.append({'id':opaque(client.scope,'port',rid),'raw_id':rid,'rrd_id':text(str(r.get('rrd_id',''))),'name':text(r.get('name')) or 'Porta '+rid,'link':text(r.get('link')),'speed':text(str(r.get('speed',''))) if r.get('link')=='up' else '', 'duplex':text(r.get('duplex')),'hosts':matches,'macCount':len(r.get('mac_list',[]))})
        return rows
    try:
        client.open()
        if route=='router':
            get('wan','/connection/',wan)
            if caps.get('catalog:system',{}).get('status')!='active' or not 0<=now-caps['catalog:system']['at']<600 or section=='history':
                get('catalog:system','/system/',system)
            get('catalog:fibre','/connection/ftth/',lambda r:{k:obj(r).get(k) for k in ('link','sfp_has_power_report','sfp_pwr_rx','sfp_pwr_tx') if type(r.get(k)) in (bool,int)})
            get('catalog:update','/update/',lambda r:{'state':text(obj(r).get('state'))})
            # Planning is technical; no unqualified timestamp conversion.
            get('catalog:planning','/standby/status',lambda r:{'enabled':obj(r).get('use_planning') if type(r.get('use_planning')) is bool else None,'mode':text(r.get('planning_mode'))})
        elif route=='wifi':
            radios_data=get('catalog:radios','/wifi/ap/',radios) or []
            selected=next((r for r in radios_data if r['id']==entity),None)
            if selected and section in ('stations','detail'):
                key='stations:'+entity;previous=caps.get(key,{})
                def stations(raw):
                    rows=[];old_rows=previous.get('data',[]) if isinstance(previous.get('data'),list) else []
                    for r in listing(raw,256):
                        host=r.get('host',{});mac=text(r.get('mac')).upper();h=by_host.get((host.get('interface','pub'),host.get('id'))) if isinstance(host,dict) else None
                        linked=bool(h and h['mac']==mac);sid=opaque(client.scope,'station:'+entity,mac)
                        old=next((s for s in old_rows if s.get('id')==sid),{})
                        duration=number(r.get('conn_duration'));same=old.get('state') in ('authenticated','associated') and previous.get('status')=='active' and old.get('duration') is not None and duration is not None and duration>=old['duration'] and r.get('state') in ('authenticated','associated')
                        rx=r.get('rx_bytes');tx=r.get('tx_bytes');rx=rx if type(rx) is int and rx>=0 else None;tx=tx if type(tx) is int and tx>=0 else None
                        rows.append({'id':sid,'name':text(h['name']) if linked else text(r.get('hostname')) or 'Stazione senza record LAN','hostId':h['id'] if linked else '', 'state':text(r.get('state')),'signal':number(r.get('signal'),negative=True),'rxLink':number(r.get('last_rx',{}).get('bitrate')) if isinstance(r.get('last_rx'),dict) else None,'txLink':number(r.get('last_tx',{}).get('bitrate')) if isinstance(r.get('last_tx'),dict) else None,'duration':duration,'rxBytes':rx,'txBytes':tx,'upRate':counter_rate(old.get('rxBytes'),rx,now-previous.get('at',now),same),'downRate':counter_rate(old.get('txBytes'),tx,now-previous.get('at',now),same)})
                    return rows
                get(key,'/wifi/ap/'+quote(selected['raw_id'],safe='')+'/stations/',stations)
        elif route=='ports':
            # Switch status refreshed with the selected stats (two data GET).
            p=get('catalog:ports','/switch/status/',ports,force=True) or []
            selected=next((p for p in p if p['id']==entity),None)
            if selected and section!='history':get('port:'+entity,'/switch/port/'+quote(selected['raw_id'],safe='')+'/stats',lambda r:{k:number(obj(r).get(k)) for k in ('rx_good_bytes','tx_bytes','rx_bytes_rate','tx_bytes_rate')})
        if section=='history' and route in ('router','ports'):
            dbs=('net','temp') if route=='router' else ('switch',)
            for db in dbs:
                key=f'history:{db}:{hours}'
                if caps.get(key,{}).get('status')=='active' and 0<=now-caps[key]['at']<60:continue
                fields=[('rate_down','Download WAN','bit/s',8),('rate_up','Upload WAN','bit/s',8)] if db=='net' else [('temp_t1','Sensore T1','°C',1),('temp_cpub','CPU B router','°C',1),('fan0_speed','Ventola router','RPM',1)] if db=='temp' else [(direction+'_'+p['rrd_id'],('RX' if direction=='rx' else 'TX')+' porta '+p['raw_id'],'bit/s',8) for p in result.get('catalog:ports',{}).get('data',[]) for direction in ('rx','tx') if re.fullmatch(r'\d{1,3}',p['rrd_id'])]
                path='/rrd/?'+urlencode({'db':db,'date_start':int(now-hours*3600),'date_end':int(now)})
                get(key,path,lambda r,fields=fields:history(r,fields,now))
        for catalog,prefix in (('catalog:radios','stations:'),('catalog:ports','port:')):
            data=result.get(catalog,{}).get('data',[])
            if isinstance(data,list):
                allowed={prefix+r['id'] for r in data}
                for key in list(result):
                    if key.startswith(prefix) and key not in allowed:result.pop(key,None);updates.pop(key,None)
        return result,updates
    finally:client.close()


def projected(caps, route, entity, section, hours, metric, station, now):
    """Only a selected view's typed, bounded whitelist is published."""
    rows=[];states=[];series=[];chart={};entities=[]
    def source(key,ttl=FAST_INTERVAL+5):
        c=caps.get(key,{})
        current=c.get('status')=='active' and 0<=now-c.get('at',0)<=ttl
        states.append(c.get('error') or ('Fonte precedente · '+stamp(c.get('at')) if c.get('at') and not current else ''))
        return c.get('data',{}),current,c.get('at',0)
    def row(key,title,value,detail='',target='',current=True):
        rows.append({'id':key,'title':text(title),'value':text(str(value),160),'detail':text(detail,220),'targetId':target,'previous':not current})
    def caprows(key,func,ttl=635):
        data,current,at=source(key,ttl)
        if isinstance(data,dict):func(data,current,at)
    title={'router':'iliadbox / Internet','wifi':'Wi-Fi','ports':'Porte Ethernet'}.get(route,'Rete')
    summary='';selected=''
    if route=='router':
        def w(r,f,a):
            nonlocal summary
            summary=text(r.get('media')).upper()+' · '+text(r.get('state'))
            row('wan:down','Traffico download WAN',rate(number(r.get('rate_down'))*8 if number(r.get('rate_down')) is not None else None),stamp(a),current=f)
            row('wan:up','Traffico upload WAN',rate(number(r.get('rate_up'))*8 if number(r.get('rate_up')) is not None else None),stamp(a),current=f)
            row('bw:down','Capacità download riportata',rate(r.get('bandwidth_down')),'Non è uno speed test',current=f)
            row('bw:up','Capacità upload riportata',rate(r.get('bandwidth_up')),'Non è uno speed test',current=f)
        caprows('wan',w,35)
        def s(r,f,a):
            row('firmware','Firmware',r.get('firmware') or 'Non disponibile',stamp(a),current=f);row('uptime','Uptime router',scalar(r.get('uptime'),'s'),stamp(a),current=f)
            for item in r.get('sensors',[])[:32]+r.get('fans',[])[:16]:
                if isinstance(item,dict):row(text(item.get('id')),text(item.get('name')),scalar(item.get('value'),'RPM' if 'fan' in text(item.get('id')) else '°C'),'Sensore iliadbox, non Orange Pi',current=f)
        caprows('catalog:system',s)
        def fibre(r,f,a):
            report=r.get('sfp_has_power_report') is True
            row('opt:rx','Potenza ottica RX',scalar(r.get('sfp_pwr_rx'),'dBm',.01) if report else 'Non disponibile',stamp(a),current=f)
            row('opt:tx','Potenza ottica TX',scalar(r.get('sfp_pwr_tx'),'dBm',.01) if report else 'Non disponibile',stamp(a),current=f)
        caprows('catalog:fibre',fibre)
        caprows('catalog:update',lambda r,f,a:row('update','Aggiornamento firmware',text(r.get('state')) or 'Non disponibile',stamp(a),current=f))
        caprows('catalog:planning',lambda r,f,a:row('planning','Programma standby','Non disponibile' if r.get('enabled') is None else 'Attivo' if r['enabled'] else 'Non attivo',text(r.get('mode')),current=f))
    elif route=='wifi':
        data,current,at=source('catalog:radios',635)
        entities=data if isinstance(data,list) else []
        r=next((r for r in entities if r.get('id')==entity),None)
        selected=r.get('name','') if r else 'Radio non selezionata / precedente'
        if section=='radios':
            for r in entities[:8]:row(r['id'],r['name'],r['band'],r['state']+' · canale '+r['channel']+' · '+r['width']+' MHz',r['id'],current)
        elif r:
            summary=r['band']+' · canale '+r['channel']+' · '+r['width']+' MHz'
            data,current,at=source('stations:'+entity)
            st=data if isinstance(data,list) else []
            if section=='stations':
                for s in st[:256]:row(s['id'],s['name'],scalar(s.get('signal'),'dB'),'Segnale riportato · '+s['state'],s['id'],current)
                summary+=' · '+str(len(st))+' associazioni (non host unici)'
            else:
                s=next((s for s in st if s.get('id')==station),None)
                if s:
                    selected=s['name'];row('signal','Segnale riportato',scalar(s.get('signal'),'dB'),'Nessuna percentuale dedotta',current=current)
                    for k,label in [('rxLink','Link RX box'),('txLink','Link TX box')]:row(k,label,scalar(s.get(k),'Mbit/s',.1),'Velocità fisica, non Internet',current=current)
                    row('duration','Durata associazione',scalar(s.get('duration'),'s'),'Non è uptime del dispositivo',current=current)
                    row('up','Verso la box (delta RX)',rate(s.get('upRate')),'Traffico LAN · baseline/reset qualificati',current=current)
                    row('down','Dalla box (delta TX)',rate(s.get('downRate')),'Traffico LAN · non consumo Internet',current=current)
                    for k,label in [('rxBytes','Byte ricevuti dalla box'),('txBytes','Byte inviati dalla box')]:row(k,label,str(s[k]) if type(s.get(k)) is int else 'Non disponibile','Contatore associazione',current=current)
                    if s.get('hostId'):row('lan','Apri dispositivo LAN','DETTAGLIO','Associazione host ID + MAC',s['hostId'],current)
    elif route=='ports':
        data,current,at=source('catalog:ports',35);entities=data if isinstance(data,list) else []
        p=next((p for p in entities if p.get('id')==entity),None);selected=p.get('name','') if p else 'Porta non selezionata / precedente'
        if section=='ports':
            for p in entities[:16]:row(p['id'],p['name'],p['link']+(' · '+p['speed']+' Mbit/s' if p['speed'] else ''),str(p['macCount'])+' MAC · '+p['duplex'],p['id'],current)
        elif p:
            summary=p['link']+(' · '+p['speed']+' Mbit/s' if p['speed'] else '')+' · traffico condiviso'
            data,fresh,a=source('port:'+entity)
            if isinstance(data,dict):
                for key,label in [('rx_bytes_rate','Rate RX porta'),('tx_bytes_rate','Rate TX porta')]:row(key,label,rate(number(data.get(key))*8 if number(data.get(key)) is not None and p['link']=='up' else None),'Aggregato · lato switch · '+stamp(a),current=fresh and current)
                for key,label in [('rx_good_bytes','Byte RX validi porta'),('tx_bytes','Byte TX porta')]:row(key,label,str(data[key]) if type(data.get(key)) is int else 'Non disponibile','Contatori, non consumo per host',current=fresh and current)
            for h in p['hosts'][:256]:row(h['id'],h['name'],'DETTAGLIO','Visto da porta; possibile switch a valle',h['id'],current)
    if section=='history' and route in ('router','ports'):
        db='switch' if route=='ports' else 'net' if metric==0 else 'temp'
        data,current,at=source(f'history:{db}:{hours}',65)
        if isinstance(data,dict) and isinstance(data.get('series'),list):
            chosen=data['series'][:2] if db=='net' else [s for s in data['series'] if (s['unit']=='RPM' if metric==2 else s['unit']=='°C')][:2] if db=='temp' else [s for s in data['series'] if s['id'] in ('rx_'+p['rrd_id'],'tx_'+p['rrd_id'])] if p else []
            series=[{'id':s['id'],'label':s['label'],'unit':s['unit'],'points':s['points'][:180],'gaps':s['gaps']} for s in chosen[:2]]
            chart={k:data.get(k) for k in ('start','end','resolution','rawPoints')}
            chart.update(series=series,previous=not current,period=stamp(data.get('start'))+' → '+stamp(data.get('end')),unit=series[0]['unit'] if series else '',message='Dati precedenti' if not current else 'Fonte RRD · buchi conservati')
    if not rows:row('unavailable','Dati non disponibili','—','La fonte non ha fornito dati per questa selezione',current=False)
    if section!='history' and len(rows)<256:
        row('metrics.refresh','Aggiorna queste metriche','AGGIORNA','Richiesta manuale · limite 30 secondi','metrics.refresh')
    return {'title':title,'summary':summary,'selectedLabel':selected,'rows':rows[:256],'entities':[{'id':e.get('id',''),'name':e.get('name','')} for e in entities[:16]],'chart':chart,'sourceText':' · '.join(dict.fromkeys(s for s in states if s)) or 'Letture iliadbox · sola consultazione','hasChart':any(p['value'] is not None for s in series for p in s['points']),'section':section}


def demo_caps(inventory, now):
    """Synthetic TEST-NET UI data, never collected or persisted on the router."""
    caps={}
    def add(key,data):caps[key]={'status':'active','at':now,'error':'','data':data}
    add('wan',{'state':'up','media':'ftth','rate_down':1500000,'rate_up':240000,'bandwidth_down':5000000000,'bandwidth_up':900000000})
    add('catalog:system',{'firmware':'Demo','uptime':86400,'sensors':[{'id':'temp_t1','name':'Sensore router','value':51}],'fans':[{'id':'fan0_speed','name':'Ventola router','value':1590}]})
    add('catalog:fibre',{'link':True,'sfp_has_power_report':True,'sfp_pwr_rx':-1823,'sfp_pwr_tx':256})
    add('catalog:update',{'state':'up_to_date'});add('catalog:planning',{'enabled':False,'mode':'suspend'})
    radios=[{'id':opaque('demo','ap',i),'raw_id':str(i),'name':'Radio '+str(i),'band':'2,4 GHz' if i==0 else '5 GHz','channel':'6' if i==0 else '48','width':'20' if i==0 else '160','state':'active'} for i in range(2)]
    add('catalog:radios',radios)
    for r in radios:
        add('stations:'+r['id'],[{'id':opaque('demo','station:'+r['id'],h['id']),'name':h['name'],'hostId':h['id'],'state':'authenticated','signal':-61,'rxLink':860,'txLink':722,'duration':3600,'rxBytes':12345678,'txBytes':23456789,'upRate':120000,'downRate':340000} for h in inventory['devices'][:3]])
    ports=[{'id':opaque('demo','port',i),'raw_id':str(i),'rrd_id':str(i),'name':'Porta '+str(i),'link':'up' if i!=1 else 'down','speed':'2500' if i==3 else '100' if i==2 else '','duplex':'full','macCount':3 if i==3 else 0,'hosts':[{'id':h['id'],'name':h['name']} for h in inventory['devices'][:3]] if i==3 else []} for i in (1,2,3)]
    add('catalog:ports',ports)
    for p in ports:add('port:'+p['id'],{'rx_good_bytes':123456789123456789,'tx_bytes':23456789,'rx_bytes_rate':3500,'tx_bytes_rate':3200})
    for hours in (1,24):
        for db in ('net','temp','switch'):
            fields=[('rate_down','Download WAN','bit/s',8),('rate_up','Upload WAN','bit/s',8)] if db=='net' else [('temp_t1','Sensore T1','°C',1),('fan0_speed','Ventola','RPM',1)] if db=='temp' else [(direction+'_'+p['rrd_id'],direction.upper()+' '+p['name'],'bit/s',8) for p in ports for direction in ('rx','tx')]
            points=[{'time':now-hours*3600+i*hours*60,**{field:None if i==18 else 48+i%6 if unit=='°C' else 1500+i*3 if unit=='RPM' else 10000+i*130 for field,_,unit,_ in fields}} for i in range(61)]
            add(f'history:{db}:{hours}',history({'date_start':now-hours*3600,'date_end':now,'data':points},fields,now))
    return caps
