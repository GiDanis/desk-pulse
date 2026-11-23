"""Regression coverage of versioned profiles and the actual settings controller."""
from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from PySide6.QtCore import QCoreApplication
from game_store import GameStore,validate_profile,default_profile
from game_direct_bootstrap import direct_profile
from game_racing_presets import PROFILE_KEYS
from game_modes import MODES


def menu_value(service,key,value):
    from game_settings import OPTIONS
    assert service.settingsAction(key,1),service.snapshot['settings']
    for _ in range(len(OPTIONS[key])+1):
        if service._settings.edit['value']==value:
            service.settingsKey(5)
            assert service._settings.value(key)==value
            return
        service.settingsKey(6)
    raise AssertionError((key,value))


def menu_prepare(service,name,mode):
    """Use selector rows and keypad edits, including a dirty recipe-bearing draft."""
    service.openSettings()
    assert service.settingsAction('section:session',1)
    if service._settings.draft['mode']=='gara':menu_value(service,'mode','impara')
    assert service.settingsAction('driver',1)
    driver=next(d for d in service._store.drivers() if d['name']==name)
    assert service.settingsAction('pick:'+driver['id'],1)
    menu_value(service,'mode',mode)
    return driver


class MenuChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QCoreApplication.instance() or QCoreApplication([])

    def test_current_and_archived_profiles_preserve_every_field(self):
        for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
            current=direct_profile(41,method)
            for p in (current,{k:v for k,v in current.items() if k not in PROFILE_KEYS}):
                with self.subTest(method=method,keys=tuple(p)):
                    before=json.dumps(p,sort_keys=True);validated=validate_profile(p)
                    self.assertEqual(validated,p);self.assertIsNot(validated,p)
                    self.assertEqual(json.dumps(p,sort_keys=True),before)
        self.assertEqual(validate_profile(default_profile()),default_profile())

    def test_bad_metadata_is_rejected_with_a_specific_cause(self):
        p=direct_profile(2,'residual_ppo')
        cases=[({**p,'futureField':1},'futureField'),({k:v for k,v in p.items() if k!='seed'},'seed'),
            ({**p,'racingObjective':'valid-time-99'},'racingObjective'),
            ({**p,'racingAnchor':[]},'racingAnchor'),({**p,'raceValidationEvery':True},'raceValidationEvery'),
            ({**p,'raceValidationEvery':4.},'raceValidationEvery'),({**p,'raceValidationEvery':0},'raceValidationEvery'),
            ({**p,'racingBackup':3},'SAC o TD3'),({**p,'racingObjective':'legacy'},'racingObjective'),
            ({**p,'controlMode':'residual'},'guida'),({**p,'algorithm':[]},'algorithm')]
        for bad,label in cases:
            with self.subTest(label=label,bad=bad):
                with self.assertRaisesRegex(ValueError,label):validate_profile(bad)
        for value in (float('nan'),float('inf'),True,'4'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,'racingHorizon'):validate_profile({**p,'racingHorizon':value})
        off=direct_profile(3,'residual_sac')
        with self.assertRaisesRegex(ValueError,'PPO'):validate_profile({**off,'racingHorizon':4.})
        self.assertEqual(validate_profile({**off,'racingBackup':3}),{**off,'racingBackup':3})
        legacy=default_profile();legacy['racingObjective']='valid-time-1'
        with self.assertRaisesRegex(ValueError,'incompatibile'):validate_profile(legacy)

    def test_all_twenty_menu_combinations_preserve_storage(self):
        from game import GameService
        with tempfile.TemporaryDirectory() as root:
            service=GameService(root)
            try:
                def database():
                    with service._store.connect() as db:
                        return {t:[tuple(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')]
                            for t in ('drivers','history','profile_paths','driver_paths','timed_qualifications')}
                original=database();maestro=service._store.drivers()[0]['id']
                for name in ('Crono','Memoria','Linea','Tattico'):
                    for mode in MODES:
                        with self.subTest(name=name,mode=mode):
                            service._selected=maestro;service._mode='impara';service._refresh();service._settings.open(True)
                            driver=menu_prepare(service,name,mode)
                            self.assertTrue(service._settings.dirty)
                            self.assertTrue(service._settings.apply('apply'),service.snapshot['message'])
                            self.assertEqual(service.snapshot['selectedDriverId'],driver['id'])
                            self.assertEqual(service.snapshot['mode'],mode)
                            self.assertEqual(database(),original)
                            self.assertIsNone(service._process)
            finally:service.close()

    def test_cancel_and_unchanged_draft_and_maestro_have_explicit_outcomes(self):
        from game import GameService
        with tempfile.TemporaryDirectory() as root:
            service=GameService(root)
            try:
                before=deepcopy(service._store.drivers());selected=service._selected
                service.openSettings();self.assertFalse(service._settings.dirty)
                self.assertTrue(service._settings.apply('apply'))
                menu_prepare(service,'Memoria','impara_infinito')
                service._settings.open(True)  # explicit discard in the controller
                self.assertEqual(service._selected,selected);self.assertEqual(service._store.drivers(),before)
                menu_prepare(service,'Maestro','impara')
                row=next(r for r in service.snapshot['settings']['rows'] if r['id']=='start')
                self.assertFalse(row['enabled']);self.assertIn('riferimento',row['description'])
                for mode in ('qualifica','gara'):
                    menu_value(service,'mode',mode)
                    self.assertTrue(next(r for r in service.snapshot['settings']['rows'] if r['id']=='start')['enabled'])
            finally:service.close()


if __name__=='__main__':unittest.main()
