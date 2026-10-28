"""Actual exported alpha/padding and conservative articulated-fish envelope."""
import json,math,unittest
from PySide6.QtGui import QImage
from aquarium_catalog import ROOT,load_catalog


def alpha_rows(image):
    alpha=image.convertToFormat(QImage.Format_Alpha8)
    data=bytes(alpha.constBits());stride=alpha.bytesPerLine();width=alpha.width()
    return [data[y*stride:y*stride+width] for y in range(alpha.height())]


def bounds(image):
    rows=alpha_rows(image);left=image.width();right=bottom=0;top=image.height()
    for y,row in enumerate(rows):
        x=image.width()-len(row.lstrip(b'\0'));end=len(row.rstrip(b'\0'))
        if end:
            left=min(left,x);right=max(right,end);top=min(top,y);bottom=y+1
    assert right>left and bottom>top,'Empty fish artwork'
    return left,top,right,bottom


class ArtworkTests(unittest.TestCase):
    def test_sprites_have_real_alpha_and_no_clipped_frame_edges(self):
        catalog=load_catalog()
        for species in catalog['species']:
            image=QImage(str(ROOT/(species['id']+'-swim.png')))
            self.assertEqual((image.width(),image.height()),(3072,512))
            rows=alpha_rows(image);self.assertEqual(min(map(min,rows)),0);self.assertEqual(max(map(max,rows)),255)
            for frame in range(16):
                box=bounds(image.copy((frame%8)*384,(frame//8)*256,384,256))
                self.assertTrue(0<box[0]<box[2]<384 and 0<box[1]<box[3]<256,(species['id'],frame,box))
    def test_full_articulated_envelope_fits_below_scene_radius(self):
        data=json.loads((ROOT/'catalog.json').read_text())
        for species in data['species']:
            image=QImage(str(ROOT/species['file']));maximum=0
            for part,amplitude in [('body',0),('tail',12),('fin',9)]:
                rect=species[part+'Rect'];box=bounds(image.copy(int(rect['x']),int(rect['y']),int(rect['width']),int(rect['height'])))
                pivot=species.get(part+'Pivot',{'x':0,'y':0});anchor=species.get(part+'Anchor',{'x':0,'y':0})
                vx=380+anchor['x']-500;vy=-30+anchor['y']-320;limit=math.radians(amplitude)
                for x in (box[0],box[2]):
                    for y in (box[1],box[3]):
                        ux=x-pivot['x'];uy=y-pivot['y']
                        stationary=math.atan2(vy*ux-vx*uy,vx*ux+vy*uy)
                        angles=[-limit,limit]+[stationary+k*2*math.pi for k in (-1,0,1) if -limit<=stationary+k*2*math.pi<=limit]
                        maximum=max(maximum,*[math.hypot(vx+ux*math.cos(t)-uy*math.sin(t),vy+ux*math.sin(t)+uy*math.cos(t)) for t in angles])
            # Root rotation preserves radius; facing compression cannot enlarge
            # it. Include every opaque-box corner and all fin/tail angles.
            self.assertLess(maximum/1000,.94,(species['id'],maximum/1000))

if __name__=='__main__':unittest.main()
