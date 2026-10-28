"""Diagnostic-only 30 Hz display interpolation. Never advances physics or policy."""
import math


class Presenter:
 def __init__(self):self.targets={};self.scene=None;self.epoch=None
 def pose(self,row,now):
  p=self.targets.get(row['id'])
  if not p:return row['x'],row['y'],row['yaw']
  a=min(1.,max(0.,(now-p['at'])/p['duration']))
  return tuple(start+a*(end-start) for start,end in zip(p['from'],p['to']))
 def push(self,scene,now):
  epoch=(scene.get('session'),scene.get('meta',{}).get('generation'),scene.get('meta',{}).get('presentation'))
  if epoch!=self.epoch:self.targets={};self.epoch=epoch
  for row in scene['cars']:
   key=row['id'];target=(row['x'],row['y'],row['yaw']);old=self.targets.get(key)
   if old and target==old['raw']:continue
   current=self.pose(row,now) if old else target
   end=(target[0],target[1],current[2]+(target[2]-current[2]+math.pi)%(2*math.pi)-math.pi)
   gap=max(1/30,min(.5,now-old['at'])) if old else 1/30
   self.targets[key]=dict(at=now,duration=gap,raw=target,**{'from':current,'to':end})
  self.scene=scene
 def frame(self,now):
  if not self.scene:return None
  cars=[]
  for row in self.scene['cars']:
   x,y,yaw=self.pose(row,now);cars.append(dict(row,x=x,y=y,yaw=yaw))
  return {**self.scene,'cars':cars,'meta':{**self.scene['meta'],'framePresentation':'interpolated30'}}
