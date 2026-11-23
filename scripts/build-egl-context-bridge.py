#!/usr/bin/env python3
"""Build the EGL query bridge on the target architecture, outside system libraries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1]/'dashboard/egl_context_bridge.c')
p.add_argument('--output', type=Path, required=True)
p.add_argument('--cc', default='cc')
a = p.parse_args()
a.output.parent.mkdir(parents=True, exist_ok=True)
temporary = a.output.with_name(a.output.name + '.building')
try:
    subprocess.run([a.cc, '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Wl,-z,relro,-z,now', '-o', str(temporary), str(a.source), '-ldl', '-pthread'], check=True)
    exports = {r.split()[-1] for r in subprocess.check_output(['nm','-D','--defined-only',str(temporary)],text=True).splitlines()}
    if exports != {'glGetString', 'glGetIntegerv'}:
        raise RuntimeError('Unexpected bridge exports: ' + str(exports))
    temporary.replace(a.output)
finally:
    temporary.unlink(missing_ok=True)
print(json.dumps({'sourceSha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  'binarySha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),
                  'exports':sorted(exports),'binary':str(a.output)}))
