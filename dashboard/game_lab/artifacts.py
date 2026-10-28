"""Immutable laboratory inputs and atomic reports, outside the GUI runtime."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_report(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    temporary.replace(path)


def freeze_dataset(source,destination):
    """Include only published complete episodes, never an in-flight NPZ.

    A private copy permits collectors to append or replace their own files
    while an experiment keeps exactly the same inputs throughout BC and RL.
    Existing snapshots are verified, not silently refreshed.
    """
    source=Path(source);destination=Path(destination)
    if destination.exists():
        manifest=json.loads((destination/'dataset-manifest.json').read_text())
        for name,sha in manifest['files'].items():
            if digest(destination/name)!=sha:raise ValueError('Dataset snapshot changed: '+name)
        return manifest
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='dataset-',dir=destination.parent))
    try:
        names=set()
        for report in sorted(source.glob('collection-train-*.json')):
            data=json.loads(report.read_text())
            for row in data['rows']:names.add(row['file'])
            shutil.copy2(report,temporary/report.name)
        if not names:raise ValueError('No published training episodes')
        for name in sorted(names):
            if Path(name).name!=name or not name.startswith('train-') or not name.endswith('.npz'):
                raise ValueError('Invalid dataset member')
            shutil.copy2(source/name,temporary/name)
        files={p.name:digest(p) for p in sorted(temporary.iterdir())}
        sha=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        manifest=dict(version='frozen-causal-dataset-1',hash=sha,files=files,episodes=len(names))
        atomic_report(temporary/'dataset-manifest.json',manifest)
        os.replace(temporary,destination)
        return manifest
    finally:
        if temporary.exists():shutil.rmtree(temporary)
