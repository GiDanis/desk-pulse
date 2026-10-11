#!/usr/bin/env python3
"""Export a frozen dense pilot for offline A733 conversion; no NPU claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dashboard'))
import numpy as np
import onnx
from onnx import helper, numpy_helper, TensorProto
import onnxruntime as ort
from game_catalog import OBSERVATION_SIZE, configuration
from game_learning import Policy
from game_store import canonical

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('policy',type=Path);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();snapshot=json.loads(args.policy.read_text());policy=Policy(snapshot)
if policy.kind!='dense':raise SystemExit('Solo reti dense con topologia fissa: NEAT resta CPU')
if args.output.exists():raise SystemExit('Scegli una cartella di output nuova')
args.output.mkdir(parents=True)
hidden=policy.hidden;split=(OBSERVATION_SIZE+1)*hidden
a=policy.weights[:split].reshape(OBSERVATION_SIZE+1,hidden).astype(np.float32)
b=policy.weights[split:].reshape(hidden+1,2).astype(np.float32)
initializers=[numpy_helper.from_array(value,name) for name,value in [('w1',a[:-1]),('b1',a[-1]),('w2',b[:-1]),('b2',b[-1])]]
nodes=[helper.make_node('Gemm',['observation','w1','b1'],['h0']),helper.make_node('Tanh',['h0'],['h']),
       helper.make_node('Gemm',['h','w2','b2'],['a0']),helper.make_node('Tanh',['a0'],['action'])]
graph=helper.make_graph(nodes,'SmartPC frozen pilot',[helper.make_tensor_value_info('observation',TensorProto.FLOAT,[1,OBSERVATION_SIZE])],
                        [helper.make_tensor_value_info('action',TensorProto.FLOAT,[1,2])],initializers)
model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',13)],producer_name='SmartPC');model.ir_version=8
onnx.checker.check_model(model);onnx.save(model,args.output/'policy.onnx')
vectors=np.random.default_rng(733).uniform(-1,1,(512,OBSERVATION_SIZE)).astype(np.float32)
reference=policy.act(vectors)
session=ort.InferenceSession(str(args.output/'policy.onnx'),providers=['CPUExecutionProvider'])
outputs=[];times=[]
for row in vectors:
 started=time.perf_counter();outputs.append(session.run(None,{'observation':row[None]})[0][0]);times.append(time.perf_counter()-started)
error=float(np.max(np.abs(np.asarray(outputs)-reference)))
if error>1e-5:raise SystemExit('Parità ONNX non raggiunta: '+str(error))
(args.output/'vectors.json').write_bytes(canonical({'inputs':vectors.tolist(),'actions':reference.tolist()}))
(args.output/'policy.json').write_bytes(canonical(snapshot))
report={'schema':1,'target':'A733','status':'onnx-cpu-parity-passed','npuQualified':False,'precision':'float32',
        'configuration':configuration(),'policyHash':hashlib.sha256(canonical(snapshot)).hexdigest(),
        'onnxSha256':hashlib.sha256((args.output/'policy.onnx').read_bytes()).hexdigest(),
        'vectors':512,'maxActionError':error,'onnxCpuMedianSeconds':float(np.median(times)),
        'requiredNext':'ACUITY A733 NBG compilation, board parity and end-to-end utility gate'}
(args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
