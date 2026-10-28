"""Execute the renderer's actual JS in QJSEngine, not a Python approximation."""
import json
from pathlib import Path
import unittest
from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine

class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        self.engine=QJSEngine();code=(Path(__file__).parent/'presentations/aquarium/AquariumMotion.js').read_text().replace('.pragma library','')
        result=self.engine.evaluate(code);self.assertFalse(result.isError(),result.toString())
    def run_js(self,code):
        result=self.engine.evaluate(code);self.assertFalse(result.isError(),result.toString());return result.toVariant()
    def test_seed_reproducibility(self):self.assertTrue(self.run_js('(function(){var a=rng(42),b=rng(42);for(var i=0;i<100;i++)if(a()!==b())return false;return true})()'))
    def test_curve_is_contained_for_many_seeds(self):
        self.assertTrue(self.run_js('''(function(){for(var seed=1;seed<101;seed++){var c=segment({x:100,y:200},{x:-1,y:0},{x:80,y:100,width:600,height:350},rng(seed));for(var j=0;j<=200;j++){var p=sample(c,c.length*j/200);if(p.x<80-1e-8 || p.x>680+1e-8 || p.y<100-1e-8 || p.y>450+1e-8)return false}}return true})()'''))
    def test_arc_length_not_uniform_parameter_speed(self):
        result=self.run_js('''(function(){var c=segment({x:100,y:200},{x:1,y:.4},{x:80,y:100,width:700,height:400},rng(7));var last=sample(c,0),min=1e9,max=0;for(var i=1;i<=100;i++){var p=sample(c,c.length*i/100),d=Math.hypot(p.x-last.x,p.y-last.y);min=Math.min(min,d);max=Math.max(max,d);last=p}return max/min})()''')
        self.assertLess(result,1.06)
    def test_endpoints_and_finite_tangents(self):self.assertTrue(self.run_js('''(function(){var c=segment({x:120,y:180},{x:0,y:0},{x:80,y:100,width:650,height:400},rng(44)),p=sample(c,1e10),e=c.p[3];return Math.abs(p.x-e.x)<1e-8 && Math.abs(p.y-e.y)<1e-8 && isFinite(p.dx) && isFinite(p.dy)})()'''))
if __name__=='__main__':unittest.main()
