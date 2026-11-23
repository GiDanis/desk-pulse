"""Regression probes for the GUI identity, idle helper and durable acknowledgements."""
import json
from pathlib import Path
import tempfile
import time
import unittest

from PySide6.QtCore import QCoreApplication, QObject, Property, Signal, Slot, QUrl
from PySide6.QtQml import QQmlEngine, QQmlComponent
from aquarium_catalog import load_3d_catalog
from aquarium_store import AquariumStore
from game_metadata import MetadataReader
from game_store import GameStore
from soak import gui_identity

APP=QCoreApplication.instance() or QCoreApplication([])

def pump_until(test,seconds=12):
    end=time.monotonic()+seconds
    while not test() and time.monotonic()<end:
        APP.processEvents();time.sleep(.005)
    assert test(),'Qt deadline exceeded'


class Receipt(QObject):
    changed=Signal()
    def __init__(self,parent):super().__init__(parent);self.value='pending'
    @Property(bool,notify=changed)
    def accepted(self):return self.value!='failed'
    @Property(str,notify=changed)
    def status(self):return self.value
    def finish(self,value):self.value=value;self.changed.emit()


class Sender(QObject):
    def __init__(self):super().__init__();self.results=[]
    @Slot(str,str,'QVariantMap',result=QObject)
    def requestAction(self,action,target,args):
        result=Receipt(self);self.results.append(result);return result


class MaintenanceTests(unittest.TestCase):
    def test_gui_identity_rejects_wrong_pid_reuse_dead_and_stale(self):
        with tempfile.TemporaryDirectory() as folder:
            proc=Path(folder)
            def process(pid,parent,start,script):
                root=proc/str(pid);root.mkdir(exist_ok=True)
                fields=['0']*22;fields[0]='S';fields[1]=str(parent);fields[19]=str(start)
                (root/'stat').write_text(str(pid)+' (python helper) '+' '.join(fields))
                (root/'cmdline').write_bytes(b'python\0'+script.encode()+b'\0')
            process(10,1,1,'/opt/smartpc/dashboard/theme_supervisor.py')
            process(11,10,2,'/opt/smartpc/dashboard/app.py')
            h={'pid':11,'processStart':'2','time':100,'ready':True,'pending':None}
            self.assertEqual((11,'2'),gui_identity(10,h,proc=proc,now=101))
            for delta in ({'pid':10,'processStart':'1'},{'processStart':'99'},
                          {'ready':False},{'time':90},{'time':110}):
                with self.assertRaises(ValueError):gui_identity(10,{**h,**delta},proc=proc,now=101)
            process(11,1,2,'/opt/smartpc/dashboard/app.py')
            with self.assertRaises(ValueError):gui_identity(10,h,proc=proc,now=101)
            (proc/'11/stat').unlink()
            with self.assertRaises(FileNotFoundError):gui_identity(10,h,proc=proc,now=101)

    def test_fixed_population_has_no_idle_writes_and_keeps_clock_guard(self):
        now=[1794960000.0]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fish.sqlite';catalog=load_3d_catalog()
            store=AquariumStore(path,catalog,clock=lambda:now[0])
            for _ in range(3):
                now[0]+=60;before=store.db.total_changes;store.reconcile()
                self.assertEqual(before,store.db.total_changes)
            latest=now[0];now[0]-=300
            self.assertFalse(store.reconcile());self.assertFalse(store.snapshot()['clockHealthy'])
            now[0]=latest;store.close()
            store=AquariumStore(path,catalog,clock=lambda:now[0]-300)
            self.assertFalse(store.reconcile());store.close()

    def test_ack_waits_for_commit_retries_and_bounds_failure(self):
        engine=QQmlEngine();sender=Sender()
        component=QQmlComponent(engine,QUrl.fromLocalFile(str(Path(__file__).parent/'presentations/aquarium/AquariumAcknowledgement.qml')))
        obj=component.createWithInitialProperties({'ctx':sender,'action':'aquarium.prepared','target':'one'})
        self.assertIsNotNone(obj,[e.toString() for e in component.errors()])
        obj.tick();self.assertFalse(obj.property('committed'));self.assertEqual(1,len(sender.results))
        obj.tick();self.assertEqual(1,len(sender.results),'no duplicate while pending')
        sender.results[-1].finish('failed');obj.tick();obj.setProperty('retryAt',0);obj.tick()
        self.assertEqual(2,len(sender.results));sender.results[-1].finish('completed')
        self.assertTrue(obj.tick());self.assertTrue(obj.property('committed'))
        obj.setProperty('target','two');self.assertFalse(obj.property('committed'))
        for _ in range(3):
            obj.setProperty('retryAt',0);obj.tick();sender.results[-1].finish('failed');obj.tick()
        self.assertTrue(obj.property('blocked'));self.assertTrue(obj.property('errorText'))
        count=len(sender.results);obj.tick();self.assertEqual(count,len(sender.results))
        obj.setProperty('target','three');self.assertFalse(obj.property('blocked'))
        obj.deleteLater();APP.processEvents()

    def test_idle_reader_releases_and_reopens_without_changing_drivers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);GameStore(root);results=[]
            reader=MetadataReader(root,results.append,idle_timeout_ms=30)
            try:
                reader.request(1,'','oval-1','impara')
                pump_until(lambda:bool(results));self.assertNotIn('error',results[-1],results[-1])
                before=json.dumps(results[-1]['drivers'],sort_keys=True)
                pump_until(lambda:reader.process is None)
                self.assertFalse(reader.closed)
                reader.request(2,'','oval-1','impara')
                pump_until(lambda:len(results)==2)
                self.assertNotIn('error',results[-1],results[-1]);self.assertEqual(2,results[-1]['ticket'])
                self.assertEqual(before,json.dumps(results[-1]['drivers'],sort_keys=True))
            finally:reader.close()


if __name__=='__main__':unittest.main()
