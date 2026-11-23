"""Contract and pack tests, with real temporary files and extension registration."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from theme_core import ROOT, ThemeCatalog, ThemeError, contained
from theme_pack import import_pack, export_pack


class ThemeContractTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.store=Path(self.directory.name)/'themes';self.catalog=ThemeCatalog(self.store)
    def tearDown(self):self.directory.cleanup()
    def test_complete_presets(self):
        for identifier in ('base','functional'):
            for variant in ('day','night'):
                for mode in ('normal','reduced','off'):
                    result=self.catalog.resolve(identifier,variant=variant,motion_mode=mode)
                    self.assertEqual(set(result['tokens']),set(self.catalog.contract))
                    required = {content for row in self.catalog.presentations.values() if row.get('fallback')
                                for content in row['contentIds']}
                    self.assertEqual(set(result['presentations']), required)
        self.assertNotEqual(self.catalog.resolve('base')['presentations'],self.catalog.resolve('functional')['presentations'])
    def test_zero_and_typo(self):
        self.assertEqual(self.catalog.resolve('base',{'tokens':{'shape.radiusCard':0}})['tokens']['shape.radiusCard'],0)
        with self.assertRaises(ThemeError):self.catalog.resolve('base',{'tokens':{'color.surface':'#123456'}})
    def test_invalid_tokens(self):
        for key,value in [('shape.radiusCard',True),('shape.radiusCard',25),('colors.accent','#fff'),('typography.textScale',float('nan')),('metrics.listRows',0)]:
            with self.subTest(key=key,value=value),self.assertRaises(ThemeError):self.catalog.resolve('base',{'tokens':{key:value}})
    def test_effective_clock_bound(self):
        with self.assertRaises(ThemeError):self.catalog.resolve("base",{"tokens":{"typography.size152":190,"typography.textScale":1.1}})

    def test_contrast(self):
        with self.assertRaisesRegex(ThemeError,'contrasto'):self.catalog.resolve('base',{'tokens':{'colors.textPrimary':'#1c2d38'}})
    def test_snapshot_isolation(self):
        a=self.catalog.resolve('base');a['tokens']['shape.radiusCard']=999
        self.assertEqual(self.catalog.resolve('base')['tokens']['shape.radiusCard'],13)
    def test_cycle_and_unknown_parent(self):
        self.catalog.packs['cycle']={'id':'cycle','extends':'cycle','version':'1.0.0'}
        with self.assertRaisesRegex(ThemeError,'ciclo'):self.catalog.resolve('cycle')
        with self.assertRaises(ThemeError):self.catalog.resolve('missing')
    def test_capabilities_and_components(self):
        for overrides in ({'presentations':{'home.now':'missing'}},{'presentations':{'home.now':'builtin.weather.now'}},{'motion':{'navigate.family':{'recipe':'bad'}}},{'scene':{'renderer':'missing'}},{'iconSetId':'missing'}):
            with self.subTest(overrides=overrides),self.assertRaises(ThemeError):self.catalog.resolve('base',overrides)
    def test_import_export_and_duplicates(self):
        source=Path(self.directory.name)/'third';source.mkdir()
        pack={'schemaVersion':1,'id':'third','name':'Terzo tema','version':'1.0.0','extends':'base','tokens':{'shape.radiusCard':0},'motion':{'navigate.family':{'recipe':'builtin.fade'}}}
        (source/'theme.json').write_text(json.dumps(pack))
        self.assertEqual(import_pack(source,self.store),'third');catalog=ThemeCatalog(self.store)
        self.assertEqual(catalog.resolve('third')['tokens']['shape.radiusCard'],0)
        with self.assertRaises(ThemeError):import_pack(source,self.store)
        destination=Path(self.directory.name)/'export'
        export_pack(catalog,'third',destination,new_id='exported',overrides={'tokens':{'shape.radiusRow':0}})
        import_pack(destination,self.store);self.assertEqual(ThemeCatalog(self.store).resolve('exported')['tokens']['shape.radiusRow'],0)
    def test_extension_without_resolver_changes(self):
        root=Path(self.directory.name)/'application';shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('__pycache__','design','fixtures'))
        extension=root/'extensions/proof';extension.mkdir(parents=True)
        (extension/'View.qml').write_text('import QtQuick\nItem { required property var context }\n')
        (extension/'manifest.json').write_text(json.dumps({'apiVersion':1,'presentations':[{'id':'proof.home','file':'extensions/proof/View.qml','contentIds':['home.now'],'apiVersion':1}],'tokens':{'ext.proof.meter':{'alias':'proofMeter','type':'int','default':1,'minimum':0,'maximum':2}}}))
        catalog=ThemeCatalog(self.store,root=root);catalog.reload()
        result=catalog.resolve('base',{'presentations':{'home.now':'proof.home'},'tokens':{'ext.proof.meter':2}})
        self.assertEqual(result['tokens']['ext.proof.meter'],2)
    def test_asset_escape(self):
        with self.assertRaises(ThemeError):contained(self.store,'../secret')
        source=Path(self.directory.name)/'escape';source.mkdir()
        pack={'schemaVersion':1,'id':'escape','name':'Escape','version':'1.0.0','extends':'base','assets':[{'id':'font','type':'font','path':'../secret'}]}
        (source/'theme.json').write_text(json.dumps(pack))
        with self.assertRaises(ThemeError):import_pack(source,self.store)
        self.assertFalse((self.store/'escape').exists())
    def test_broken_user_pack_falls_back(self):
        invalid=self.store/'bad';invalid.mkdir(parents=True);(invalid/'theme.json').write_text('{')
        catalog=ThemeCatalog(self.store);self.assertTrue(catalog.errors);self.assertIn('base',catalog.packs)
    def test_facade_contract(self):
        facades={name:(ROOT/('themes/'+name+'.qml')).read_text() for name in ('StyleFacade','NotificationStyle')}
        # Application extensions declare their additional typed facade in their own module.
        for spec in json.loads((ROOT/'themes/token-contract.json').read_text())['tokens'].values():
            self.assertIn('readonly property '+spec['type']+' '+spec['alias']+':',facades[spec.get('facade','StyleFacade')])

    def test_notification_inheritance_and_overrides(self):
        result=self.catalog.resolve('functional',variant='night')
        self.assertEqual(result['tokens']['notifications.small.surface'],result['tokens']['colors.bannerSurface'])
        self.assertEqual(result['tokens']['notifications.detail.titleSize'],result['tokens']['typography.size45'])
        result=self.catalog.resolve('base',{'tokens':{'notifications.large.titleSize':60}})
        self.assertEqual(result['tokens']['notifications.large.titleSize'],60)
        self.assertEqual(result['tokens']['typography.size44'],44)
        for values in ({'notifications.small.anchor':'somewhere'}, {'notifications.small.insetX':100}, {'notifications.small.titleColor':'#29423f'}):
            with self.subTest(values=values),self.assertRaises(ThemeError):self.catalog.resolve('base',{'tokens':values})

    def test_standalone_old_pack_gets_notification_fallbacks(self):
        old=deepcopy(self.catalog.packs['base']);old['id']='standalone';old['presentations']={key:value for key,value in old['presentations'].items() if not key.startswith('alerts.')}
        self.catalog.packs['standalone']=old;self.catalog.directories['standalone']=self.catalog.directories['base']
        result=self.catalog.resolve('standalone')
        self.assertEqual(set(result['presentations']), set(self.catalog.resolve('base')['presentations']))

    def test_notification_template_envelope(self):
        self.catalog.resolve('base',{'tokens':{'notifications.large.titleSize':72,'notifications.large.bodySize':44,'typography.textScale':1.1}})
        with self.assertRaises(ThemeError):
            self.catalog.resolve('base',{'tokens':{'notifications.large.titleSize':72,'notifications.large.padding':64,'notifications.large.gap':40,'typography.textScale':1.1}})
        with self.assertRaises(ThemeError):
            self.catalog.resolve('base',{'tokens':{'notifications.detail.height':32}})
        with self.assertRaises(ThemeError):
            self.catalog.resolve('base',{'tokens':{'notifications.inbox.focusedSurface':'#ffffff'}})

    def test_legacy_notification_recipe_aliases(self):
        legacy=deepcopy(self.catalog.recipes['builtin.fade']);legacy['id']='legacy.banner';legacy['events']=['banner.enter','banner.exit']
        self.catalog.recipes[legacy['id']]=legacy
        override={'motion':{'banner.enter':{'recipe':legacy['id'],'durationMs':120,'distancePx':20,'easing':'outCubic'}}}
        result=self.catalog.resolve('base',override)
        self.assertEqual(result['motion']['banner.small.enter']['recipe'],legacy['id'])
        # Exported resolved motion contains explicit aliases: it remains valid.
        self.catalog.resolve('base',{'motion':result['motion']})

if __name__=='__main__':unittest.main(verbosity=2)
