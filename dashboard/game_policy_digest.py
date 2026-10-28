"""Canonical policy hashes with immutable encoder bytes cached once.

Only the declared readout and decision counter vary. This yields the exact
ordinary policy hash without serializing the recurrent encoder each update.
"""
from copy import deepcopy
import hashlib,json


def mutable_weights(policy):
    names=['head.weight','skip.weight','head.bias']
    if policy.get('architecture')=='gru-adapter':names.append('adapter_head.weight')
    if policy.get('readoutMode')=='plastic-actuators-1':
        names.extend(k for k in policy['weights'] if k.startswith(('steer_controller.','pedal_controller.')))
    return names


class ReadoutDigest:
    def __init__(self,policy):
        self.paths=[('weights',name) for name in mutable_weights(policy)]+[('origin','decisions')]
        template=deepcopy(policy);markers=[]
        for i,(section,name) in enumerate(self.paths):
            marker='__smartpc_policy_part_'+str(i)+'__';markers.append(json.dumps(marker).encode())
            if name not in template[section]:raise ValueError('Mutable policy field missing')
            template[section][name]=marker
        encoded=json.dumps(template,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        positions=[]
        for path,marker in zip(self.paths,markers):
            if encoded.count(marker)!=1:raise ValueError('Ambiguous policy digest marker')
            positions.append((encoded.index(marker),marker,path))
        self.parts=[];end=0
        for start,marker,path in sorted(positions):
            self.parts.extend((encoded[end:start],path));end=start+len(marker)
        self.parts.append(encoded[end:])

    def digest(self,values):
        if set(values)!=set(self.paths):raise ValueError('Mutable policy fields changed')
        result=hashlib.sha256()
        for part in self.parts:
            result.update(part if isinstance(part,bytes) else json.dumps(values[part],sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        return result.hexdigest()
