"""Synthetic LAN protocol, identity and persistence checks; no router I/O."""
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from iliadbox import IliadboxClient, NetworkError, load_config
from network_core import NetworkStore, acquire, demo_snapshot, display, empty, normalize_host

CONFIG={'router':'192.0.2.1','router_uid':'test-router','api_domain':'test.example','app_id':'test.app','app_token':'synthetic-secret'}
NOW=1790848800

class FakeRouter:
    def __init__(self):
        self.calls=[];self.failure=None;self.hosts=[{'id':'same-mac','reachable':True,'active':True,'primary_name':'Computer','l2ident':{'id':'02:00:00:00:00:01'},'vendor_name':'Discard me','l3connectivities':[{'addr':'192.0.2.30','af':'ipv4','reachable':True},{'addr':'2001:db8::30','af':'ipv6','reachable':True}], 'names':[{'source':'dhcp'}],'last_time_reachable':NOW-60}]
    def __call__(self,method,path,body,token,timeout):
        self.calls.append((method,path));assert timeout<=2.5
        assert method=='GET' or path.endswith(('/login/session/','/login/logout/'))
        if path=='/api_version':return {'uid':CONFIG['router_uid'],'api_version':'15.0','api_base_url':'/api/'}
        if path.endswith('/login/'):
            return {'success':True,'result':{'challenge':'challenge'}}
        if path.endswith('/login/session/'):
            assert body=={'app_id':'test.app','password':hmac.new(CONFIG['app_token'].encode(),b'challenge',hashlib.sha1).hexdigest()}
            assert token is None
            return {'success':True,'result':{'session_token':'session','permissions':{'settings':False}}}
        assert token=='session'
        if self.failure and not path.endswith('/login/logout/'):raise self.failure
        if path.endswith('/lan/browser/interfaces/'):result=[{'name':'pub','host_count':2},{'name':'wifiguest','host_count':None}]
        elif path.endswith('/lan/browser/pub/'):result=deepcopy(self.hosts)
        elif path.endswith('/lan/browser/wifiguest/'):result=None
        elif path.endswith('/wifi/ap/'):result=[{'id':1,'config':{'band':'5g'}}]
        elif path.endswith('/stations/'):result=[{'host':{'interface':'pub','id':'same-mac'},'mac':'02:00:00:00:00:01','state':'associated'}]
        elif path.endswith('/switch/status/'):result=[]
        elif path.endswith('/connection/'):result={'state':'up','media':'ftth'}
        elif path.endswith('/login/logout/'):result=True
        else:raise AssertionError(path)
        return {'success':True,'result':result}

class NetworkTests(unittest.TestCase):
    def test_protocol_quality_and_scope(self):
        router=FakeRouter();client=IliadboxClient(CONFIG,transport=router)
        result=acquire(client,empty(client.scope),NOW,{'state':'configured','interface':'wlan0','address':'192.0.2.20'})
        self.assertIsNone(client.token);self.assertEqual(result['devices'][0]['connection'],'Wi-Fi 5 GHz · AP 1')
        self.assertEqual(result['devices'][0]['vendor'],'');self.assertEqual(len(result['devices'][0]['addresses']),2)
        data=display(result,'active',NOW);self.assertEqual(data['reachableText'],'1')
        self.assertIn('wifiguest: inventario non disponibile',data['coverage']);self.assertIn('1 record / 2',data['coverage'])
        self.assertNotIn('synthetic-secret',json.dumps(data));self.assertNotIn('hostId',json.dumps(data))
        self.assertEqual(data['devices'][0]['lastSeen'],NOW-60)
        self.assertEqual(display(result,'active',NOW+306)['reachableText'],'—')
        self.assertTrue(display(result,'stale',NOW)['devices'][0]['previous'])
        self.assertTrue(display(result,'active',NOW-30)['devices'][0]['previous'])
    def test_identity_does_not_follow_reused_ip(self):
        row=FakeRouter().hosts[0];first=normalize_host(row,'pub','scope',NOW)
        moved=deepcopy(row);moved['l3connectivities'][0]['addr']='192.0.2.99'
        self.assertEqual(first['id'],normalize_host(moved,'pub','scope',NOW)['id'])
        reused=deepcopy(row);reused['id']='other-mac'
        self.assertNotEqual(first['id'],normalize_host(reused,'pub','scope',NOW)['id'])
        self.assertNotEqual(first['id'],normalize_host(row,'wifiguest','scope',NOW)['id'])
        self.assertNotEqual(first['id'],normalize_host(row,'pub','other-router',NOW)['id'])
    def test_invalid_inventory_and_logout(self):
        for rows in [[FakeRouter().hosts[0]]*2,[{'id':'incomplete'}],{'hosts':[]}]:
            router=FakeRouter();router.hosts=rows;client=IliadboxClient(CONFIG,transport=router)
            with self.assertRaises(NetworkError):acquire(client,empty(client.scope),NOW)
            self.assertIsNone(client.token);self.assertTrue(router.calls[-1][1].endswith('/login/logout/'))
    def test_retained_favourite_is_previous(self):
        router=FakeRouter();client=IliadboxClient(CONFIG,transport=router);old=acquire(client,empty(client.scope),NOW)
        identity=old['devices'][0]['id'];old['preferences']['favourites']=[identity];router.hosts=[]
        result=acquire(client,old,NOW+3600);data=display(result,'active',NOW+3600)
        self.assertEqual(data['reachableText'],'0');self.assertTrue(data['favourites'][0]['previous'])
        self.assertEqual(result['devices'][0]['collectedAt'],NOW)
    def test_sqlite_private_preferences_retention_and_corrupt_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            store=NetworkStore(Path(temp)/'state','demo');s=demo_snapshot(NOW);p=s['preferences'];p['aliases'][s['devices'][0]['id']]='Studio'
            store.commit(s,p);restored=store.load();self.assertEqual(restored['preferences'],p)
            self.assertEqual(store.path.stat().st_mode&0o777,0o600);self.assertEqual(store.directory.stat().st_mode&0o777,0o700)
            with store.connection() as conn:self.assertEqual(conn.execute('SELECT cycles FROM history').fetchone()[0],1)
            store.commit(demo_snapshot(NOW+32*86400))
            with store.connection() as conn:self.assertEqual(conn.execute('SELECT count(*) FROM history').fetchone()[0],1)
            self.assertEqual(store.load()['preferences'],p)
            corrupted=demo_snapshot(NOW);corrupted['devices'][0]['addresses']=[{'bad':'endpoint'}];store.commit(corrupted)
            with self.assertRaises(NetworkError):store.load()
            other=NetworkStore(Path(temp)/'state','a'*24);self.assertEqual(other.load()['preferences']['favourites'],[])
    def test_versioned_bundle_fallback_is_additive_and_immutable(self):
        from theme_bundle import effective_manifest
        from theme_api_contract import ThemeApiContract
        surfaces=set(ThemeApiContract().surfaces)
        casa={'casa.overview','casa.devices','casa.detail','settings.casa'}
        network={'network.overview','network.devices','network.detail','settings.network'}
        for missing in [network,casa|network]:
            original={'coverage':{'mode':'complete','surfaces':sorted(surfaces-missing),'fallbacks':[]}}
            before=deepcopy(original);resolved=effective_manifest(original,surfaces)
            self.assertEqual(original,before);self.assertEqual(set(resolved['coverage']['fallbacks']),missing)
        missing={'network.overview','network.devices'}
        value={'coverage':{'mode':'complete','surfaces':sorted(surfaces-missing),'fallbacks':[]}}
        self.assertEqual(effective_manifest(value,surfaces),value)

    def test_config_and_identity_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'app.json';file.write_text(json.dumps(CONFIG));file.chmod(0o644)
            with self.assertRaises(NetworkError):load_config(file)
            file.chmod(0o600);self.assertEqual(load_config(file),CONFIG)
        router=FakeRouter()
        def wrong(*args):
            if args[1]=='/api_version':return {'uid':'replacement-router'}
            return router(*args)
        with self.assertRaises(NetworkError) as caught:acquire(IliadboxClient(CONFIG,transport=wrong),empty(),NOW)
        self.assertEqual(caught.exception.kind,'identity');self.assertFalse(router.calls)
        router=FakeRouter();router.failure=NetworkError('auth','Synthetic revoked')
        client=IliadboxClient(CONFIG,transport=router)
        with self.assertRaises(NetworkError):acquire(client,empty(client.scope),NOW)
        self.assertIsNone(client.token)

if __name__=='__main__':unittest.main(verbosity=2)
