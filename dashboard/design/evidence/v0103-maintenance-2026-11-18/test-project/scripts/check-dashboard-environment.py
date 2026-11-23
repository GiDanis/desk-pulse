#!/usr/bin/env python3
"""Fail before qualification when the selected interpreter differs from the target."""
import importlib.metadata
import json
import platform
import sys


def main():
    machine=platform.machine()
    expected_python=(3,11) if machine in ('aarch64','arm64') else (3,12)
    errors=[];versions={}
    if sys.version_info[:2]!=expected_python:
        errors.append('Python '+'.'.join(map(str,expected_python))+' required for this qualification target')
    for name,expected in [('numpy','2.2.6'),('neat-python','1.1.0')]:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
        if versions[name]!=expected:errors.append(name+' '+expected+' required')
    try:
        from PySide6.QtCore import qVersion
        versions['Qt']=qVersion()
    except ImportError:versions['Qt']=None
    if versions['Qt']!='6.8.2':errors.append('Qt 6.8.2 required')
    print(json.dumps({'status':'failed' if errors else 'passed','executable':sys.executable,
        'python':platform.python_version(),'machine':machine,'versions':versions,'errors':errors},indent=2))
    return bool(errors)


if __name__=='__main__':raise SystemExit(main())
