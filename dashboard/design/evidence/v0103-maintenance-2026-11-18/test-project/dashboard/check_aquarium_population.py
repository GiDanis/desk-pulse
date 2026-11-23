"""Focused persistence/calendar tests with a fake clock; never touches user data."""
import json
from pathlib import Path
import tempfile
import unittest
from aquarium_catalog import load_3d_catalog
from aquarium_store import AquariumStore
from aquarium_rotation import DAY


class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'aquarium.sqlite';self.now=1793260800
        self.catalog=load_3d_catalog();self.store=AquariumStore(self.path,self.catalog,clock=lambda:self.now)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def save(self,fish,days=7,**other):
        args=dict(name='Luna',variant='pearl',days=days,nextSpecies='');args.update(other)
        self.store.command('save',fish['id'],args)
    def test_reopen_preserves_identity_and_name(self):
        fish=self.store.active()[0];self.save(fish);ids=[r['id'] for r in self.store.active()]
        self.store.close();self.store=AquariumStore(self.path,self.catalog,clock=lambda:self.now)
        self.assertEqual(ids,[r['id'] for r in self.store.active()]);self.assertEqual('Luna',self.store.active()[0]['name'])
    def test_calendar_offline_single_replacement_no_phantom_history(self):
        fish=self.store.active()[0];self.save(fish);self.now+=32*DAY
        self.store.reconcile();self.store.reconcile();state=self.store.snapshot();self.assertEqual(1,len(state['pending']))
        operation=state['pending'][0]['operationId'];self.assertEqual(fish['id'],self.store.active()[0]['id'])
        self.store.prepared(operation);self.store.prepared(operation);state=self.store.snapshot()
        self.assertEqual(7,len(state['history']));self.assertEqual(self.now+7*DAY,self.store.active()[0]['due'])
        self.assertEqual(1,sum(r['ended'] is not None for r in state['history']))
    def test_exact_deadline_and_clock_rollback(self):
        fish=self.store.active()[0];self.save(fish,1);self.now+=DAY-1;self.store.reconcile();self.assertFalse(self.store.snapshot()['pending'])
        self.now-=2*DAY;self.assertFalse(self.store.reconcile());self.assertFalse(self.store.snapshot()['clockHealthy'])
        self.now+=2*DAY+1;self.store.reconcile();self.assertTrue(self.store.snapshot()['pending'])
    def test_pending_commit_waits_for_healthy_clock(self):
        fish=self.store.active()[0];self.save(fish,1);self.now+=DAY;self.store.reconcile()
        operation=self.store.snapshot()['pending'][0]['operationId'];correct=self.now
        self.now-=2*DAY;self.store.prepared(operation)
        self.assertEqual(fish['id'],self.store.active()[0]['id'])
        self.now=correct;self.store.prepared(operation)
        self.assertNotEqual(fish['id'],self.store.active()[0]['id'])

    def test_empty_pool_keeps_current(self):
        fish=self.store.active()[0];self.save(fish,1)
        for s in list(self.store.catalog):self.store.command('pool',s,{})
        self.now+=2*DAY;self.store.reconcile();self.assertFalse(self.store.snapshot()['pending']);self.assertEqual(fish['id'],self.store.active()[0]['id'])
    def test_fixed_and_simultaneous_reservations(self):
        self.now+=100*DAY;self.store.reconcile();self.assertFalse(self.store.snapshot()['pending'])
        for fish in self.store.active()[:2]:self.save(fish,1)
        self.now+=DAY;self.store.reconcile()
        pending=list(self.store.db.execute('SELECT * FROM pending'));self.assertEqual(2,len(pending));self.assertEqual(2,len({r['slot'] for r in pending}))
    def test_remove_add_and_capacity_preserve_archive(self):
        fish=self.store.active()[0]
        with self.assertRaises(ValueError):self.store.command('add','',{'species':'clown'})
        self.store.command('remove',fish['id'],{});self.store.command('add','',{'species':'clown'})
        p=self.store.snapshot()['pending'][0];self.store.prepared(p['operationId'])
        self.assertEqual(6,len(self.store.active()));self.assertIsNotNone(self.store.db.execute('SELECT * FROM fish WHERE id=?',(fish['id'],)).fetchone())
    def test_cancel_pending_on_policy_edit_and_stale_revision(self):
        fish=self.store.active()[0];self.save(fish,1);self.now+=DAY;self.store.reconcile();p=self.store.snapshot()['pending'][0]
        self.save(fish,0);self.store.prepared(p['operationId']);self.assertEqual(fish['id'],self.store.active()[0]['id'])
        with self.assertRaises(ValueError):self.store.command('remove',fish['id'],{},revision=0)
    def test_commit_survives_reopen_and_shown_is_idempotent(self):
        fish=self.store.active()[0];self.store.command('replace',fish['id'],{'species':'angel'});p=self.store.snapshot()['pending'][0]
        self.store.close();self.store=AquariumStore(self.path,self.catalog,clock=lambda:self.now);self.store.prepared(p['operationId'])
        new=self.store.active()[0];self.assertIsNone(new['shown']);self.store.shown(new['visitId']);self.now+=10;self.store.shown(new['visitId'])
        self.assertEqual(self.now-10,self.store.active()[0]['shown']);self.assertEqual(7,len(self.store.snapshot()['history']))
    def test_invalid_update_rolls_back(self):
        fish=self.store.active()[0];before=self.store.snapshot()
        for args in ({'days':True},{'days':-1},{'variant':'absent'},{'name':''}):
            with self.assertRaises(ValueError):self.save(fish,**args)
            self.assertEqual(before,self.store.snapshot())
    def test_extend_catalog_with_data_only(self):
        extra=json.loads(json.dumps(self.catalog));row=dict(extra['species'][0]);row['id']='new-fish';row['name']='Nuovo tipo';extra['species'].append(row)
        self.store.close();self.store=AquariumStore(self.path,extra,clock=lambda:self.now)
        fish=self.store.active()[0];self.store.command('replace',fish['id'],{'species':'new-fish'});p=self.store.snapshot()['pending'][0];self.store.prepared(p['operationId'])
        self.assertEqual('new-fish',self.store.active()[0]['species'])

    def test_current_visit_keeps_its_asset_profile_after_catalog_update(self):
        from PySide6.QtCore import QCoreApplication
        from aquarium_population import AquariumPopulation
        app=QCoreApplication.instance() or QCoreApplication([])
        original=self.store.active()[0];old=self.catalog['species'][0]['assetUrl']
        updated=json.loads(json.dumps(self.catalog));updated['species'][0]['assetUrl']='file:///new-pack/teal.fishmesh'
        self.store.close();self.store=AquariumStore(self.path,updated,clock=lambda:self.now)
        population=AquariumPopulation(path=self.path);population.catalog=updated;population.state=self.store.snapshot()
        self.assertEqual(old,population.scene('running','test')['fish'][0]['assetUrl'])
        self.store.command('replace',original['id'],{'species':'teal'});self.store.prepared(self.store.snapshot()['pending'][0]['operationId'])
        population.state=self.store.snapshot()
        self.assertEqual('file:///new-pack/teal.fishmesh',population.scene('running','test')['fish'][0]['assetUrl'])
        population.close()

    def test_request_replay_does_not_apply_twice(self):
        fish=self.store.active()[0];revision=self.store.meta('revision')
        args=dict(name='Luna',variant='pearl',days=7,nextSpecies='')
        self.store.command('save',fish['id'],args,'same-request',revision)
        saved=self.store.snapshot()
        self.store.command('save',fish['id'],args,'same-request',revision)
        self.assertEqual(saved,self.store.snapshot())

    def test_history_pages_and_saved_species_profile(self):
        for _ in range(102):
            fish=self.store.active()[0];self.store.command('replace',fish['id'],{'species':'angel'})
            self.store.prepared(self.store.snapshot()['pending'][0]['operationId']);self.now+=1
        first=self.store.snapshot();second=self.store.snapshot(100)
        self.assertEqual(108,first['historyCount']);self.assertEqual(8,len(second['history']))
        self.assertFalse({r['id'] for r in first['history']} & {r['id'] for r in second['history']})
        self.assertIn('speciesProfile',first['history'][0]['label'])

if __name__=='__main__':unittest.main()
