"""Optional prebuilt float64 sensor kernel with transparent NumPy fallback."""
import ctypes
from pathlib import Path
import numpy as np

try:
    _library=ctypes.CDLL(str(Path(__file__).with_name('libsmartpc_game_native.so')))
except OSError:
    _library=None

if _library is not None:
    _array=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
    _library.smartpc_polygon_rays.argtypes=[_array]*6+[ctypes.c_size_t]*2+[ctypes.c_double,_array]
    _library.smartpc_polygon_rays.restype=None
    _library.smartpc_oval_rays.argtypes=[_array,_array,ctypes.c_size_t]+[ctypes.c_double]*4+[_array]
    _library.smartpc_oval_rays.restype=None
    _indices=np.ctypeslib.ndpointer(dtype=np.int64,flags='C_CONTIGUOUS')
    _library.smartpc_neat.argtypes=[_array,_indices,_indices,_indices,_array,_array,_array,
                                  ctypes.c_size_t,_indices,ctypes.c_size_t,_array]
    _library.smartpc_neat.restype=None


def available():return _library is not None


def rays(track,states,angles,limit):
    if _library is None:return None
    direction_angle=(states[:,2,None]+np.asarray(angles)).ravel()
    directions=np.ascontiguousarray(np.column_stack((np.cos(direction_angle),np.sin(direction_angle))))
    origins=np.ascontiguousarray(np.repeat(states[:,:2],len(angles),axis=0))
    out=np.empty(len(origins),dtype=np.float64)
    if track.oval:
        from game_catalog import TRACK
        _library.smartpc_oval_rays(origins,directions,len(out),TRACK.half_straight,TRACK.radius,TRACK.road_width,float(limit),out)
    else:
        _library.smartpc_polygon_rays(origins,directions,track.boundaries,track.boundary_delta,
                                    track.boundary_lo,track.boundary_hi,len(out),len(track.boundaries),float(limit),out)
    return out.reshape(len(states),len(angles))


class SparsePopulation:
    """Derived sparse program, same ordered sums and tanh as NEAT-Python 1.1."""
    def __init__(self,networks,inputs):
        self.supported=_library is not None;self.inputs=inputs;self.count=len(networks)
        dest=[];starts=[0];sources=[];weights=[];bias=[];response=[];outputs=[];input_slots=[];size=0
        for network in networks:
            keys=set(network.output_nodes)
            for key,activation,aggregation,b,r,links in network.node_evals:
                if activation.__name__!='tanh_activation' or aggregation.__name__!='sum_aggregation':self.supported=False
                keys.add(key);keys.update(k for k,_ in links if k>=0)
            mapping={k:size+inputs+i for i,k in enumerate(sorted(keys))}
            mapping.update({-i-1:size+i for i in range(inputs)})
            input_slots.extend(range(size,size+inputs));outputs.extend(mapping[k] for k in network.output_nodes)
            for key,activation,aggregation,b,r,links in network.node_evals:
                dest.append(mapping[key]);bias.append(b);response.append(r)
                for key,weight in links:sources.append(mapping[key]);weights.append(weight)
                starts.append(len(sources))
            size+=inputs+len(keys)
        self.values=np.zeros(size)
        self.input_slots=np.asarray(input_slots,dtype=np.int64)
        self.destination=np.asarray(dest,dtype=np.int64);self.starts=np.asarray(starts,dtype=np.int64)
        self.sources=np.asarray(sources,dtype=np.int64);self.outputs=np.asarray(outputs,dtype=np.int64)
        self.weights=np.asarray(weights,dtype=np.float64);self.bias=np.asarray(bias,dtype=np.float64)
        self.response=np.asarray(response,dtype=np.float64);self.result=np.empty((self.count,2))

    def act(self,observations):
        if not self.supported:return None
        self.values[:]=0.;self.values[self.input_slots]=np.asarray(observations).ravel()
        _library.smartpc_neat(self.values,self.destination,self.starts,self.sources,self.weights,
                              self.bias,self.response,len(self.destination),self.outputs,len(self.outputs),self.result)
        return self.result.copy()
