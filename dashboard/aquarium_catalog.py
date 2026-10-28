"""Validated local artwork catalogue. No Qt, network, or mutable user data."""
from __future__ import annotations
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).parent / 'assets' / 'aquarium' / 'calm-v1'


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Valore numerico Acquario non valido')
    return value


def load_catalog(root=ROOT):
    root = Path(root).resolve()
    raw = (root / 'catalog.json').read_bytes()
    data = json.loads(raw)
    if type(data.get('schemaVersion')) is not int or data.get('schemaVersion') != 1 or not isinstance(data.get('files'), dict):
        raise ValueError('Catalogo Acquario non compatibile')
    resolved = {}
    for relative, digest in data['files'].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Risorsa Acquario fuori dal pacchetto o assente')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Risorsa Acquario modificata: ' + relative)
        resolved[relative] = path.as_uri()
    species = data.get('species')
    if not isinstance(species, list) or not 1 <= len(species) <= 8:
        raise ValueError('Numero di specie non valido')
    ids = set()
    for row in species:
        if not isinstance(row.get('id'), str) or not row['id'] or row['id'] in ids:
            raise ValueError('Identità delle specie non valida')
        ids.add(row['id'])
        # Only inspect paths already admitted by the manifest, including
        # symlink resolution. Never open an arbitrary catalogue field first.
        if row['file'] not in resolved or row['spriteFile'] not in resolved:
            raise ValueError('Texture Acquario non dichiarata nel manifest')
        image_path = root / row['file']
        header = image_path.read_bytes()[:24]
        if header[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', header[16:24]) != (row['atlasWidth'], row['atlasHeight']):
            raise ValueError('Dimensioni reali della texture diverse dal catalogo')
        row['atlasUrl'] = resolved[row.pop('file')]
        row['spriteUrl'] = resolved[row.pop('spriteFile')]
        width = number(row['atlasWidth'], 1, 8192)
        height = number(row['atlasHeight'], 1, 8192)
        for key in ('bodyRect', 'tailRect', 'finRect', 'referenceRect'):
            rect = row[key]
            for name in ('x', 'y', 'width', 'height'):
                number(rect[name], 0, 8192)
            if rect['width'] <= 0 or rect['height'] <= 0 or rect['x'] + rect['width'] > width or rect['y'] + rect['height'] > height:
                raise ValueError('Parte fuori dalla texture')
        for key in ('tailAnchor', 'tailPivot', 'finAnchor', 'finPivot'):
            for coord in ('x', 'y'):
                number(row[key][coord], 0, max(width, height))
        number(row['referenceSize'], 50, 180)
        number(row['speed'], 5, 80)
        number(row['tailFrequency'], .1, 5)
    data['backgroundUrl'] = resolved[data['background']]
    data['assetRevision'] = hashlib.sha256(raw).hexdigest()
    return data
