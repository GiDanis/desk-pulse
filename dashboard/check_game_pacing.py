"""Scene lane ownership/lifecycle and the monotonic presentation schedule."""
import os,time,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QObject,Signal
from PySide6.QtGui import QGuiApplication
from game_presentation import GamePresentationClock
from theme_api import PublicContextFactory

class Source(QObject):
    sceneChanged=Signal()
    def __init__(self):
        super().__init__();self.scene={'cars':[{'id':'a','x':1.}],'sequence':1}

def wait(ms):
    app=QGuiApplication.instance();end=time.monotonic()+ms/1000
    while time.monotonic()<end:app.processEvents();time.sleep(.001)

class PacingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QGuiApplication.instance() or QGuiApplication([])
    def test_scene_lane_retains_static_fields_owns_data_and_recovers_when_visible(self):
        factory=PublicContextFactory();source=Source()
        payload={'active':True,'interactive':True,'game':{'drawing':{'outer':[1,2]},'runState':'running'}}
        context=factory.createLegacy('game.track',payload)
        changed=[];context.gameChanged.connect(lambda:changed.append(True))
        self.assertTrue(factory.bindGameScene(context,source))
        source.scene['cars'][0]['x']=4.;self.assertEqual(context.scene['cars'][0]['x'],1.)
        source.sceneChanged.emit();self.assertEqual(context.scene['cars'][0]['x'],4.)
        self.assertFalse(changed)
        self.assertTrue(factory.updateLegacy(context,payload));self.assertEqual(context.scene['sequence'],1)
        self.assertTrue(factory.updateLegacy(context,{**payload,'active':False,'interactive':False}))
        source.scene={'cars':[{'id':'a','x':8.}],'sequence':2};source.sceneChanged.emit()
        self.assertEqual(context.scene['sequence'],1)
        self.assertTrue(factory.updateLegacy(context,payload));self.assertEqual(context.scene['sequence'],2)
        self.assertFalse(factory.bindGameScene(context,Source()))
        factory.release(context);source.sceneChanged.emit();self.assertFalse(factory._game_sources)
    def test_scene_lane_rejects_wrong_surface_and_preserves_last_valid_frame(self):
        factory=PublicContextFactory();source=Source();wrong=factory.createLegacy('game.menu',{})
        self.assertFalse(factory.bindGameScene(wrong,source))
        context=factory.createLegacy('game.track',{'active':True})
        self.assertTrue(factory.bindGameScene(context,source));old=context.scene
        source.scene={'cars':[{'x':float('nan')}]};source.sceneChanged.emit()
        self.assertEqual(context.scene,old)
        factory.release(context);factory.release(wrong)
    def test_clock_skips_late_deadlines_and_stops_without_backlog(self):
        clock=GamePresentationClock();ticks=[];clock.tick.connect(ticks.append)
        clock.running=True;wait(170)
        self.assertGreaterEqual(len(ticks),3);self.assertLessEqual(len(ticks),6)
        self.assertTrue(all(b>a for a,b in zip(ticks,ticks[1:])))
        time.sleep(.15);self.app.processEvents();count=len(ticks);self.app.processEvents()
        self.assertEqual(len(ticks),count)
        clock.running=False;wait(70);self.assertEqual(len(ticks),count)
        clock.running=True;wait(70);self.assertGreater(len(ticks),count);clock.running=False

if __name__=='__main__':unittest.main()
