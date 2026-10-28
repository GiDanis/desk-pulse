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
parser.add_argument('--batch-size',type=int,choices=(1,4,32),default=1)
parser.add_argument('--track',default='oval-1')
args=parser.parse_args();snapshot=json.loads(args.policy.read_text());policy=Policy(snapshot)
if policy.kind!='dense':raise SystemExit('Solo reti dense con topologia fissa: NEAT resta CPU')
if args.output.exists():raise SystemExit('Scegli una cartella di output nuova')
args.output.mkdir(parents=True)
inputs=policy.inputs;batch=args.batch_size
hidden=policy.hidden;split=(inputs+1)*hidden
a=policy.weights[:split].reshape(inputs+1,hidden).copy()
# Freeze the versioned constant observation into the exported graph's bias.
# This is inference-only; optimizer and original policy artifacts are untouched.
if snapshot.get('inputContract') and inputs>=68:
 a[-1]+=a[67]*snapshot['inputContract']['constantCue'];a[67]=0
a=a.astype(np.float32)
b=policy.weights[split:].reshape(hidden+1,2).astype(np.float32)
initializers=[numpy_helper.from_array(value,name) for name,value in [('w1',a[:-1]),('b1',a[-1]),('w2',b[:-1]),('b2',b[-1])]]
nodes=[helper.make_node('Gemm',['observation','w1','b1'],['h0']),helper.make_node('Tanh',['h0'],['h']),
       helper.make_node('Gemm',['h','w2','b2'],['a0']),helper.make_node('Tanh',['a0'],['action'])]
graph=helper.make_graph(nodes,'SmartPC frozen pilot',[helper.make_tensor_value_info('observation',TensorProto.FLOAT,[batch,inputs])],
                        [helper.make_tensor_value_info('action',TensorProto.FLOAT,[batch,2])],initializers)
model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',13)],producer_name='SmartPC');model.ir_version=8
onnx.checker.check_model(model);onnx.save(model,args.output/'policy.onnx')
vectors=np.random.default_rng(733).uniform(-1,1,(512,inputs)).astype(np.float32)
reference=policy.act(vectors)
options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
session=ort.InferenceSession(str(args.output/'policy.onnx'),options,providers=['CPUExecutionProvider'])
outputs=[];times=[]
for start in range(0,len(vectors),batch):
 started=time.perf_counter();outputs.extend(session.run(None,{'observation':vectors[start:start+batch]})[0]);times.append(time.perf_counter()-started)
error=float(np.max(np.abs(np.asarray(outputs)-reference)))
if error>1e-5:raise SystemExit('Parità ONNX non raggiunta: '+str(error))
(args.output/'vectors.json').write_bytes(canonical({'inputs':vectors.tolist(),'actions':reference.tolist()}))
(args.output/'policy.json').write_bytes(canonical(snapshot))
report={'schema':1,'target':'A733','status':'onnx-cpu-parity-passed','npuQualified':False,'precision':'float32',
        'configuration':configuration(args.track,snapshot['observation']),'inputs':inputs,'batch':batch,'policyHash':hashlib.sha256(canonical(snapshot)).hexdigest(),
        'onnxSha256':hashlib.sha256((args.output/'policy.onnx').read_bytes()).hexdigest(),
        'inputContract':snapshot.get('inputContract'),'vectors':512,'maxActionError':error,'onnxCpuMedianSeconds':float(np.median(times)),
        'requiredNext':'ACUITY A733 NBG compilation, board parity and end-to-end utility gate'}
(args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
