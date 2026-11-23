"""Authoring bridge failures, provenance and atomic/idempotent inbox staging."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from theme_authoring import check_project,contrast_suggestion,write_kit
from theme_core import ROOT,ThemeCatalog,ThemeError
from theme_probe import payload_digest,receiver
from theme_transfer import BoardTransport,install_local


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=self.root/'data/themes';self.source=self.root/'source';self.source.mkdir()
        self.pack={'schemaVersion':1,'id':'authoring.test','name':'Authoring','version':'1.0.0','extends':'base','tokens':{}}
        self.write()
    def tearDown(self):self.tmp.cleanup()
    def write(self):
        (self.source/'theme.json').write_text(json.dumps(self.pack))
    def check(self,**kwargs):return check_project(self.source,store=self.store,**kwargs)
    def test_read_only_and_scoped_result(self):
        result=self.check()
        self.assertEqual(result['status'],'valid',result['issues'])
        self.assertFalse(self.store.exists())
        self.assertEqual(result['verification']['boardRuntime'],'notVerified')
        self.assertEqual(result['verification']['qtResources'],'notVerified')
        self.assertEqual(len(result['coverage']),2)
        catalog = ThemeCatalog()
        expected = {content for row in catalog.presentations.values() if row.get('fallback')
                    for content in row['contentIds']}
        self.assertTrue(all(set(row['presentations']) == expected for row in result['coverage']))
    def test_aggregate_token_and_unknown_field_errors(self):
        self.pack['tokens']={'color.typo':'#123456','shape.radiusRow':25,'typography.textScale':True}
        self.pack['imaginedEngine']=True;self.write()
        result=self.check()
        self.assertEqual(result['status'],'invalid')
        self.assertEqual(len(result['issues']),4)
        self.assertIn('/tokens/shape.radiusRow',[i['pointer'] for i in result['issues']])
    def test_duplicate_json_rejected(self):
        (self.source/'theme.json').write_text('{"id":"a","id":"b"}')
        self.assertEqual(self.check()['status'],'invalid')
    def test_missing_motion_fields_reported_from_contract(self):
        self.pack['motion']={'navigate.family':{'durationMs':100}};self.write()
        missing=[i for i in self.check()['issues'] if i['code']=='motion.required']
        self.assertEqual(len(missing),3)
        self.assertIn('/motion/navigate.family/recipe',[i['pointer'] for i in missing])
    def test_nonfinite_and_bad_shapes_no_traceback(self):
        for value in (None,[],{'assets':[None]}, {'motion':{'foo':[]}}, {'palettes':{'day':[]}}, {'schemaVersion':True}):
            candidate={**self.pack,**value} if isinstance(value,dict) else value
            (self.source/'theme.json').write_text(json.dumps(candidate))
            self.assertEqual(self.check()['status'],'invalid',candidate)
    def test_contrast_provenance_and_nonmutating_suggestion(self):
        self.pack['palettes']={'day':{'colors.textSecondary':'#242424'}};self.write()
        before=(self.source/'theme.json').read_bytes()
        result=self.check()
        failures=[i for i in result['issues'] if i['code']=='contrast.minimum']
        # Inherited semantic roles can now derive a readable foreground; the
        # explicitly authored secondary color must still expose its real failures.
        self.assertGreaterEqual(len(failures),5)
        self.assertTrue(all(i['variant']=='day' for i in failures))
        self.assertTrue(all(i['pointer']=='/palettes/day/colors.textSecondary' for i in failures))
        self.assertEqual(before,(self.source/'theme.json').read_bytes())
        candidate=contrast_suggestion('#7a7a7a','#242424',4.5)
        self.assertEqual(candidate['value'],'#8b8b8b')
        self.assertTrue(candidate['requiresRevalidation'])
    def test_parent_error_points_to_parent(self):
        # A resolver error caused by an inherited/default foreground names the
        # actual defining file instead of inventing a child JSON field.
        parent=self.store/'authoring.parent';parent.mkdir(parents=True)
        (parent/'theme.json').write_text(json.dumps({**self.pack,'id':'authoring.parent','tokens':{'colors.textPrimary':'#ddeeff'}}))
        self.pack.update(extends='authoring.parent',tokens={'colors.surface':'#ddeeff'});self.write()
        failures=[i for i in self.check()['issues'] if i['code']=='contrast.minimum']
        self.assertTrue(any(i['file']==str(parent/'theme.json') and i['pointer']=='/tokens/colors.textPrimary' for i in failures))
    def test_assets_escape_hash_and_symlink(self):
        asset={'id':'data','type':'data','path':'../outside.txt','sha256':'0'*64}
        (self.root/'outside.txt').write_text('secret fixture')
        self.pack['assets']=[asset];self.write();self.assertEqual(self.check()['status'],'invalid')
        asset['path']='data.txt';(self.source/'data.txt').write_text('data');self.write()
        self.assertEqual(self.check()['status'],'invalid')
        asset['sha256']=hashlib.sha256(b'data').hexdigest();self.write()
        self.assertEqual(self.check()['status'],'valid')
        (self.source/'data.txt').unlink();(self.source/'data.txt').symlink_to(self.root/'outside.txt')
        with self.assertRaises(ThemeError):install_local(self.source,self.store,ROOT)
    def test_local_install_is_received_idempotent_not_imported(self):
        receipt=install_local(self.source,self.store,ROOT)
        self.assertEqual(receipt['status'],'received')
        self.assertFalse(receipt['idempotent'])
        self.assertFalse(self.store.exists())
        again=install_local(self.source,self.store,ROOT)
        self.assertTrue(again['idempotent'])
        self.assertEqual(receipt['digest'],again['digest'])
        self.assertNotIn(self.pack['id'],ThemeCatalog(self.store).packs)
        self.assertFalse(list((self.store.parent/'theme-imports').glob('.receive-*')))
    def test_conflict_preserves_received_files(self):
        first=install_local(self.source,self.store,ROOT);destination=Path(first['destination'])
        digest=payload_digest(destination)
        self.pack['tokens']={'shape.radiusCard':2};self.write()
        with self.assertRaisesRegex(ValueError,'conflitto'):install_local(self.source,self.store,ROOT)
        self.assertEqual(payload_digest(destination),digest)
    def test_publish_failure_does_not_expose_partial_pack(self):
        with patch('theme_transfer.receiver',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):install_local(self.source,self.store,ROOT)
        inbox=self.store.parent/'theme-imports'
        self.assertFalse((inbox/self.pack['id']).exists())
        self.assertFalse(list(inbox.glob('.receive-*')))
    def test_transfer_staging_ignored_by_existing_import_discovery(self):
        result=receiver({'operation':'receive.begin','ticket':'.receive-test','files':['theme.json','assets/x.dat'],'bytes':10},ROOT,self.store)
        (Path(result['path'])/'theme.json').write_text(json.dumps(self.pack))
        inbox=self.store.parent/'theme-imports'
        discover=[p for p in inbox.iterdir() if p.is_dir() and (p/'theme.json').is_file()]
        self.assertEqual(discover,[])
        receiver({'operation':'receive.abort','ticket':'.receive-test'},ROOT,self.store)
    def test_manifest_stays_revalidated_after_copy(self):
        def verify(path):
            result=check_project(path,store=self.store)
            if result['status']!='valid':raise ThemeError('staging','candidate invalid')
        self.pack['tokens']={'colors.textPrimary':'#1c2d38'};self.write()
        with self.assertRaises(ThemeError):install_local(self.source,self.store,ROOT,verify=verify)
        self.assertFalse((self.store.parent/'theme-imports'/self.pack['id']).exists())
    def test_known_light_semantic_risk(self):
        for role in ('background','surface','surfaceFocused','backgroundOverlay','bannerSurface'):
            self.pack['tokens']['colors.'+role]='#ecebe4'
        self.pack['tokens'].update({'colors.textPrimary':'#181818','colors.textSecondary':'#333333','colors.accent':'#993300'})
        self.write()
        self.assertTrue(any(i['code']=='semantic.contrast' for i in self.check()['issues']))
    def test_profile_mismatch_and_font(self):
        profile={'profileVersion':1,'registryFingerprint':'wrong','fontFamilies':[]}
        self.assertEqual(self.check(profile=profile)['status'],'invalid')
        from theme_authoring import registry_fingerprint
        profile.update(registryFingerprint=registry_fingerprint(ThemeCatalog()),qtVersion='test')
        self.pack['tokens']={'typography.uiFamily':'Missing Font'};self.write()
        self.assertTrue(any(i['phase']=='profile' for i in self.check(profile=profile)['issues']))
    def test_kit_uses_live_extension_contract(self):
        destination=self.root/'kit';write_kit(destination)
        contract=json.loads((destination/'token-contract.json').read_text())['tokens']
        self.assertIn('ext.summary.clockInset',contract)
        schema=json.loads((destination/'theme-pack.schema.json').read_text())
        self.assertEqual(set(contract),set(schema['properties']['tokens']['properties']))
        self.assertIn('schema 1',(destination/'PROMPT.md').read_text())
        with self.assertRaises(ThemeError):write_kit(destination)
    def test_cli_store_before_after_and_legacy(self):
        for args in (['--store',str(self.store),'check',str(self.source)],['check',str(self.source),'--store',str(self.store)]):
            result=subprocess.run([sys.executable,str(ROOT/'theme_pack.py'),*args,'--format','json'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'valid')
        result=subprocess.run([sys.executable,str(ROOT/'theme_pack.py'),'list'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
    def test_requested_missing_qt_does_not_pass(self):
        result=self.check(qt=True,qt_python=str(self.root/'python-missing'))
        self.assertEqual(result['status'],'notVerified')
        self.assertEqual(result['verification']['qtResources'],'notVerified')
    def test_corrupted_manifest_digest_and_insufficient_space(self):
        ticket='.receive-digest'
        receiver({'operation':'receive.begin','ticket':ticket,'files':['theme.json'],'bytes':1},ROOT,self.store)
        payload=self.store.parent/'theme-imports'/ticket/'payload'
        (payload/'theme.json').write_text(json.dumps(self.pack))
        with self.assertRaisesRegex(ValueError,'hash payload'):
            receiver({'operation':'receive.publish','ticket':ticket,'digest':'0'*64},ROOT,self.store)
        self.assertFalse((payload.parent.parent/self.pack['id']).exists())
        receiver({'operation':'receive.abort','ticket':ticket},ROOT,self.store)
        with patch('theme_probe.shutil.disk_usage') as usage:
            usage.return_value.free=0
            with self.assertRaisesRegex(ValueError,'spazio'):
                receiver({'operation':'receive.begin','ticket':'.receive-space','files':['theme.json'],'bytes':1},ROOT,self.store)
        receiver({'operation':'receive.abort','ticket':'.receive-space'},ROOT,self.store)
    def test_invalid_ssh_destinations_rejected(self):
        for value in ('-oProxyCommand=evil','host; echo x','host\nother','$(command)'):
            with self.assertRaises(ThemeError):BoardTransport(value)


if __name__=='__main__':unittest.main(verbosity=2)
