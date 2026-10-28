"""Actual QML->Python QObject returns, GC, pending completion and revocation."""
import gc
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
import unittest
from PySide6.QtCore import QCoreApplication,QEvent,QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine,QQmlComponent,QQmlExpression
from theme_api import PublicContextFactory,bootstrap_theme_api
from theme_contexts import _RETURNED_RESULTS


class ResultLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QGuiApplication.instance() or QGuiApplication([])
    def setUp(self):
        self.engine=QQmlEngine();bootstrap_theme_api(self.engine)
        self.factory=PublicContextFactory(dispatch=lambda *_:True)
        self.context=self.factory.create('aquarium.main')
        self.assertTrue(self.factory.updateLegacy(self.context,{'active':True,'interactive':True,'motionMode':'normal','viewportWidth':960,'viewportHeight':640}))
        self.component=QQmlComponent(self.engine)
        self.component.setData(b'''import QtQuick
import SmartPC.ThemeApi 2.13
Item {
 required property AquariumContext context
 property var held:null
 function ask() { held=context.requestAction("aquarium.pause","",{}); return held.accepted }
 function discardMany() { for(let i=0;i<300;i++) {const r=context.requestAction("aquarium.pause","",{});if(!r.accepted)return false} return true }
}''',QUrl())
        self.root=self.component.createWithInitialProperties({'context':self.context})
        self.assertIsNotNone(self.root,self.component.errors())
    def expression(self,source):
        e=QQmlExpression(QQmlEngine.contextForObject(self.root),self.root,source);value=e.evaluate()
        self.assertFalse(e.hasError(),e.error().toString())
        return value[0]
    def collect(self):
        for _ in range(4):
            self.app.processEvents();gc.collect();self.engine.collectGarbage()
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    def tearDown(self):
        self.expression('held=null');self.collect()
        self.factory.release(self.context)
        self.root.deleteLater();self.component.deleteLater();self.engine.deleteLater();self.factory.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);gc.collect()
        self.assertEqual(len(_RETURNED_RESULTS),0)
    def test_qml_held_result_survives_python_and_js_gc_then_is_reclaimed(self):
        self.assertTrue(self.expression('ask()'));self.collect()
        self.assertTrue(self.expression('held && held.accepted'))
        self.assertEqual(self.expression('held.status'),'completed')
        self.assertEqual(len(_RETURNED_RESULTS),1)
        self.expression('held=null');self.collect();self.assertEqual(len(_RETURNED_RESULTS),0)
    def test_discarded_qml_results_do_not_accumulate(self):
        self.assertTrue(self.expression('discardMany()'));self.collect()
        self.assertEqual(len(_RETURNED_RESULTS),0)
        self.assertLessEqual(len(self.factory._history),256)
    def test_pending_result_stays_valid_after_completion_and_context_release(self):
        self.factory._dispatch=None;requests=[]
        self.factory.actionRequested.connect(lambda *args:requests.append(args[-1]))
        self.assertTrue(self.expression('ask()'));self.collect()
        self.assertEqual(self.expression('held.status'),'pending')
        self.assertTrue(self.factory.completeAction(self.context,requests[0],True,''))
        self.factory.release(self.context);self.collect()
        self.assertTrue(self.expression('held && held.accepted'))
        self.assertEqual(self.expression('held.status'),'completed')
    def test_revoked_pending_result_survives_context_disposal(self):
        self.factory._dispatch=None
        self.factory.actionRequested.connect(lambda *_:None)
        self.assertTrue(self.expression('ask()'));self.collect()
        self.factory.release(self.context);self.collect()
        self.assertFalse(self.expression('held.accepted'))
        self.assertEqual(self.expression('held.errorCode'),'api.action.generation')
    def test_python_caller_retains_result_without_a_qml_leak(self):
        result=self.context.requestAction('aquarium.pause','',{})
        self.assertTrue(result.accepted);self.collect()
        self.assertTrue(result.accepted);self.assertIsNone(result.parent())
        self.assertEqual(len(_RETURNED_RESULTS),0)

if __name__=='__main__':unittest.main()
