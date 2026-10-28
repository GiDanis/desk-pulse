"""Static, shared low/high polygon meshes; no Python work during animation."""
import math,struct
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick3D import QQuick3DGeometry
QUALITY='low'
INVENTORY={}
class Mesh(QQuick3DGeometry):
    def upload(self,name,vertices,indices):
        self.setVertexData(QByteArray(struct.pack('<'+'f'*len(vertices),*vertices)));self.setStride(24)
        A=QQuick3DGeometry.Attribute
        self.addAttribute(A.PositionSemantic,0,A.F32Type);self.addAttribute(A.NormalSemantic,12,A.F32Type)
        self.setIndexData(QByteArray(struct.pack('<'+'I'*len(indices),*indices)));self.addAttribute(A.IndexSemantic,0,A.U32Type)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        xyz=[vertices[i:i+3] for i in range(0,len(vertices),6)]
        self.setBounds(QVector3D(*(min(p[k] for p in xyz) for k in range(3))),QVector3D(*(max(p[k] for p in xyz) for k in range(3))))
        INVENTORY[name]={'vertices':len(vertices)//6,'triangles':len(indices)//3,'bufferBytes':len(vertices)*4+len(indices)*4};self.update()
def sphere(rx,ry,rz,rings,slices):
    v=[];idx=[]
    for i in range(rings+1):
        theta=math.pi*i/rings
        for j in range(slices+1):
            phi=2*math.pi*j/slices;x=rx*math.cos(theta);y=ry*math.sin(theta)*math.cos(phi);z=rz*math.sin(theta)*math.sin(phi)
            normal=[x/rx**2,y/ry**2,z/rz**2];length=math.sqrt(sum(t*t for t in normal));v.extend((x,y,z,*(t/length for t in normal)))
    for i in range(rings):
        for j in range(slices):
            a=i*(slices+1)+j;b=a+slices+1
            idx.extend((a,b,a+1,a+1,b,b+1))
    # Front faces must follow the same orientation as the outward normals.
    a,b,c=(v[k*6:k*6+3] for k in idx[6:9]);ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)];cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
    if sum(cross[k]*a[k] for k in range(3))<0:
        for i in range(0,len(idx),3):idx[i+1],idx[i+2]=idx[i+2],idx[i+1]
    return v,idx
class Body(Mesh):
    def __init__(self,parent=None):
        super().__init__(parent);self.upload('body',*sphere(40,19,11,32 if QUALITY=='high' else 12,48 if QUALITY=='high' else 20))
class Eye(Mesh):
    def __init__(self,parent=None):super().__init__(parent);self.upload('eye',*sphere(1,1,1,6,8))
def extruded(points,thickness):
    v=[];idx=[]
    def tri(a,b,c):
        u=[b[k]-a[k] for k in range(3)];w=[c[k]-a[k] for k in range(3)];n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];length=math.sqrt(sum(x*x for x in n));n=[x/length for x in n];base=len(v)//6
        for p in (a,b,c):v.extend((*p,*n))
        idx.extend((base,base+1,base+2))
    top=[(x,y,thickness/2) for x,y in points];bottom=[(x,y,-thickness/2) for x,y in points]
    for i in range(1,len(points)-1):tri(top[0],top[i],top[i+1]);tri(bottom[0],bottom[i+1],bottom[i])
    for i in range(len(points)):
        j=(i+1)%len(points);tri(bottom[i],bottom[j],top[j]);tri(bottom[i],top[j],top[i])
    return v,idx
class Tail(Mesh):
    def __init__(self,parent=None):super().__init__(parent);self.upload('tail',*extruded([(0,0),(-29,20),(-23,0),(-29,-20)],1.6))
class Fin(Mesh):
    def __init__(self,parent=None):super().__init__(parent);self.upload('fin',*extruded([(0,0),(-18,10),(-23,-5)],1.2))
def register(quality):
    global QUALITY
    QUALITY=quality
    for cls,name in ((Body,'BodyGeometry'),(Eye,'EyeGeometry'),(Tail,'TailGeometry'),(Fin,'FinGeometry')):qmlRegisterType(cls,'AquariumBench',1,0,name)
