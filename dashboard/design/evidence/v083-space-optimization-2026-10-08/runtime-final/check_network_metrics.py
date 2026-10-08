"""Metrics protocol, bounded history and private transactional cache regression."""
from copy import deepcopy
import json
import sqlite3
import tempfile
import unittest
from urllib.parse import parse_qs,urlparse
from check_network import FakeRouter,CONFIG,NOW
from iliadbox import IliadboxClient,NetworkError
from network_core import acquire,empty,demo_snapshot
from network_history import history,counter_rate
from network_metrics import MetricsStore,cap_collect,projected,demo_caps,valid_cap

class MetricsRouter(FakeRouter):
    def __init__(self):
        super().__init__();self.fail_path='';self.delta=0;self.expiry=0
    def __call__(self,method,path,body,token,timeout):
        if self.expiry and '/connection/' in path:
            self.calls.append((method,path));self.expiry-=1
            return {'success':False,'error_code':'auth_required'}
        if self.fail_path and self.fail_path in path:
            self.calls.append((method,path))
            return {'success':False,'error_code':'insufficient_rights'}
        if any(p in path for p in ('/system/','/connection/ftth/','/update/','/standby/','/rrd/','/stats')):
            self.calls.append((method,path));assert method=='GET' and token=='session'
            if '/system/' in path:v={'firmware_version':'test','uptime_val':600,'sensors':[{'id':'temp_t1','name':'T1','value':50}],'fans':[{'id':'fan0_speed','name':'Fan','value':1590}]}
            elif '/ftth/' in path:v={'link':True,'sfp_has_power_report':True,'sfp_pwr_rx':-1823,'sfp_pwr_tx':256,'key':'discard-this-secret'}
            elif '/update/' in path:v={'state':'up_to_date'}
            elif '/standby/' in path:v={'use_planning':False,'planning_mode':'suspend'}
            elif '/stats' in path:v={'rx_good_bytes':2**60+7,'tx_bytes':2**60+9,'rx_bytes_rate':23,'tx_bytes_rate':44}
            else:
                query=parse_qs(urlparse(path).query);start=int(query['date_start'][0]);end=int(query['date_end'][0]);v={'date_start':start,'date_end':end,'data':[{'time':start+i*(end-start)/600,'rate_up':10+i,'rate_down':20+i,'rx_3':30+i,'tx_3':40+i,'temp_t1':50,'fan0_speed':1600} for i in range(601)]}
            return {'success':True,'result':v}
        out=super().__call__(method,path,body,token,timeout)
        if path.endswith('/connection/'):out['result'].update(rate_up=250000,rate_down=1000000,bandwidth_up=1000000000,bandwidth_down=5000000000)
        elif path.endswith('/wifi/ap/'):out['result'][0].update(status={'state':'active','primary_channel':48,'channel_width':'160'})
        elif path.endswith('/stations/'):out['result'][0].update(state='authenticated',signal=-61,conn_duration=300+self.delta,rx_bytes=2**60+self.delta,tx_bytes=2**60+2*self.delta,last_rx={'bitrate':860},last_tx={'bitrate':722},key='discard-this-secret')
        elif path.endswith('/switch/status/'):out['result']=[{'id':3,'rrd_id':'3','link':'up','speed':'2500','duplex':'full','mac_list':[{'mac':'02:00:00:00:00:01'}]},{'id':1,'rrd_id':'1','link':'down','speed':'10','duplex':'half','mac_list':[]}]
        return out

class MetricsTests(unittest.TestCase):
    def setup_source(self):
        r=MetricsRouter();c=IliadboxClient(CONFIG,transport=r);i=acquire(c,empty(c.scope),NOW);return r,c,i
    def test_units_join_whitelist_and_counter_direction(self):
        r,c,i=self.setup_source();caps,_=cap_collect(c,{},i,'router','','state',1,NOW)
        view=projected(caps,'router','','state',1,0,'',NOW)
        self.assertEqual(view['rows'][0]['value'],'8.00 Mbit/s');self.assertEqual(next(x for x in view['rows'] if x['id']=='opt:rx')['value'],'-18.23 dBm')
        self.assertNotIn('discard-this-secret',json.dumps(caps));self.assertNotIn('synthetic-secret',json.dumps(view))
        caps,_=cap_collect(c,caps,i,'wifi','','radios',1,NOW);ap=caps['catalog:radios']['data'][0]['id']
        caps,_=cap_collect(c,caps,i,'wifi',ap,'stations',1,NOW);st=caps['stations:'+ap]['data'][0]
        self.assertEqual(projected(caps,'wifi',ap,'detail',1,0,st['id'],NOW)['rows'][0]['value'],'-61 dB');self.assertEqual(st['hostId'],i['devices'][0]['id']);self.assertIsNone(st['upRate']);self.assertEqual(st['rxBytes'],2**60)
        r.delta=30;caps,_=cap_collect(c,caps,i,'wifi',ap,'detail',1,NOW+30);st=caps['stations:'+ap]['data'][0]
        self.assertEqual(st['upRate'],8);self.assertEqual(st['downRate'],16)
        r.delta=0;caps,_=cap_collect(c,caps,i,'wifi',ap,'detail',1,NOW+60);self.assertIsNone(caps['stations:'+ap]['data'][0]['upRate'])
        caps,_=cap_collect(c,caps,i,'ports','','ports',1,NOW);ports=caps['catalog:ports']['data'];self.assertEqual(ports[1]['speed'],'');self.assertEqual(ports[0]['hosts'][0]['id'],i['devices'][0]['id'])
        caps,_=cap_collect(c,caps,i,'ports',ports[0]['id'],'hosts',1,NOW+30);v=projected(caps,'ports',ports[0]['id'],'hosts',1,0,'',NOW+30)
        self.assertEqual(next(x for x in v['rows'] if x['id']=='rx_good_bytes')['value'],str(2**60+7));self.assertIsNone(c.token)
        self.assertTrue(all(valid_cap(k,v) for k,v in caps.items()))
    def test_optional_error_retains_independent_sources_and_renewal(self):
        r,c,i=self.setup_source();caps,_=cap_collect(c,{},i,'router','','history',24,NOW);before=deepcopy(caps['catalog:fibre']);r.fail_path='/ftth/'
        caps,updates=cap_collect(c,caps,i,'router','','state',1,NOW+700)
        self.assertEqual(caps['catalog:fibre']['data'],before['data']);self.assertEqual(caps['catalog:fibre']['at'],NOW);self.assertEqual(caps['wan']['status'],'active');self.assertNotIn('catalog:fibre',updates)
        r.fail_path='';r.expiry=1;calls=len(r.calls);cap_collect(c,caps,i,'router','','state',1,NOW+800)
        self.assertEqual(sum(path.endswith('/login/session/') for _,path in r.calls[calls:]),2)
        r.expiry=2;calls=len(r.calls)
        with self.assertRaises(NetworkError):cap_collect(c,caps,i,'router','','state',1,NOW+900)
        self.assertEqual(sum(path.endswith('/login/session/') for _,path in r.calls[calls:]),2);self.assertIsNone(c.token)
    def test_history_bounds_holes_order_and_previous_axis(self):
        start=NOW-3600;rows=[{'time':start+i,'rate':None if i==200 else 100000 if i==550 else i%10} for i in range(1000)]
        rows=rows[::-1]+[{'time':start+20,'rate':77}]
        h=history({'date_start':start,'date_end':NOW,'data':rows},[('rate','Test','bit/s',8)],NOW)
        points=h['series'][0]['points'];self.assertLessEqual(len(points),180);self.assertEqual(h['series'][0]['maximum'],800000);self.assertEqual(h['series'][0]['gaps'],1);self.assertTrue(any(p['breakBefore'] for p in points if p['time']>start+200))
        self.assertTrue(all(a['time']<b['time'] for a,b in zip(points,points[1:])))
        for malformed in ({'date_start':start,'date_end':NOW,'data':[{}]}, {'date_start':start,'date_end':NOW+100,'data':[]},{'date_start':start,'date_end':NOW,'data':[rows[0]]*10001}):
            with self.assertRaises(NetworkError):history(malformed,[('rate','Test','bit/s',8)],NOW)
        caps=demo_caps(demo_snapshot(NOW),NOW);v=projected(caps,'router','','history',1,0,'',NOW+4000);self.assertEqual(v['chart']['end'],NOW);self.assertTrue(v['chart']['previous'])
        for args in ((2**60,2**60+30,30,True),(4,2,30,True),(4,8,0,True),(4,8,100,True),(4,8,30,False)):
            self.assertEqual(counter_rate(*args),8 if args[0]==2**60 else None)
    def test_private_cache_nested_corruption_scope_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            st=MetricsStore(temp,'demo');caps=demo_caps(demo_snapshot(NOW),NOW);st.save(caps);loaded=st.load()
            self.assertTrue(all(v['status']=='stale' for v in loaded.values()));self.assertEqual(st.path.stat().st_mode&0o777,0o600);self.assertEqual(st.directory.stat().st_mode&0o777,0o700)
            self.assertEqual(MetricsStore(temp,'a'*24).load(),{})
            bad=deepcopy(caps);bad['catalog:radios']['data'][0]['key']='discard-this-secret'
            with self.assertRaises(NetworkError):st.save(bad)
            self.assertEqual(st.load(),loaded)
            with sqlite3.connect(st.path) as conn:
                value=json.loads(conn.execute("SELECT value FROM metrics WHERE key='catalog:radios'").fetchone()[0]);value['cap']['data'][0]['width']={'invalid':1};conn.execute("UPDATE metrics SET value=? WHERE key='catalog:radios'",(json.dumps(value),))
            with self.assertRaises(NetworkError):st.load()
    def test_old_theme_complete_fallback_group(self):
        from theme_bundle import effective_manifest
        from theme_api_contract import ThemeApiContract
        all_surfaces=set(ThemeApiContract().surfaces);new={'network.router','network.wifi','network.ports'};old={'coverage':{'mode':'complete','surfaces':sorted(all_surfaces-new),'fallbacks':[]}};before=deepcopy(old)
        self.assertEqual(set(effective_manifest(old,all_surfaces)['coverage']['fallbacks']),new);self.assertEqual(old,before)

if __name__=='__main__':unittest.main(verbosity=2)
