"""Portable trusted-code theme bundles: deterministic build and atomic revisions.

Payload files are inventoried, bounded and checked before publication. QML
runtime compatibility is a distinct preflight result, never inferred from JSON.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time
import unicodedata
import zipfile

from theme_core import ROOT, ID, ThemeCatalog, ThemeError, read_json
from theme_resources import ResourceResolver, canonical_file, relative_path

MAX_FILES = 256
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PAYLOAD_BYTES = 24 * 1024 * 1024
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_BYTES = 24 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
REQUIRED = {'bundle.json', 'theme.json', 'visual-registry.json'}
ALLOWED_SUFFIXES = {'.json', '.qml', '.qmltypes', '.js', '.mjs', '.ttf', '.otf', '.woff', '.woff2',
                    '.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif', '.txt', '.md', '.license'}
DATA_SUFFIXES = {'.json', '.txt', '.qmltypes'}
NON_VISUAL_CODE_SUFFIXES = {
    '.so', '.dll', '.dylib', '.exe', '.elf', '.com', '.o', '.a', '.pyd', '.sys', '.drv',
    '.msi', '.msp', '.deb', '.rpm', '.apk', '.appimage', '.run', '.whl', '.jar', '.class',
    '.py', '.pyc', '.pyo', '.sh', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.desktop',
    '.ps1', '.psm1', '.vbs', '.scr', '.wsf', '.wsh', '.ahk', '.pl', '.rb', '.php', '.lua',
    '.c', '.cc', '.cpp', '.h', '.hpp', '.rs', '.go', '.java', '.ts', '.tsx', '.jsx', '.wasm',
}
REGISTRY_FIELDS = {'registryVersion', 'presentations', 'recipes', 'iconRenderers', 'sceneRenderers', 'iconSets'}
MANIFEST_FIELDS = {'bundleFormat', 'id', 'version', 'name', 'engineApi', 'contextApis', 'targetProfile',
                   'qtMinimum', 'qtModules', 'coverage', 'adjustments', 'trust', 'resources', 'extendedTokens', 'layout', 'retention'}
CONTEXT_APIS = {'page': 2, 'notification': 1, 'shell': 1, 'overlay': 1, 'scene': 1, 'icon': 1, 'motion': 1}
RESOURCE_TYPES = {'qml', 'js', 'font', 'image', 'data', 'license', 'preview'}
DEFAULT_SHELL_LAYOUT = {
    'header': {'x': 0, 'y': 0, 'width': 960, 'height': 90},
    'content': {'x': 44, 'y': 90, 'width': 872, 'height': 455},
    'guide': {'x': 44, 'y': 558, 'width': 872, 'height': 56},
    'sceneSafeRegions': [
        {'x': 0, 'y': 90, 'width': 32, 'height': 455},
        {'x': 928, 'y': 90, 'width': 32, 'height': 455},
    ],
}


def validate_layout(layout):
    """Validate author geometry before it can influence app-owned hosts.

    Rectangles use physical viewport coordinates; individual page contexts use
    a local (0, 0) viewport with the selected content rectangle's dimensions.
    Zero-sized header/guide regions allow a shell to integrate those visuals.
    """
    require(isinstance(layout, dict) and set(layout) == set(DEFAULT_SHELL_LAYOUT),
            'layout', 'header/content/guide/sceneSafeRegions richiesti senza campi extra')
    def rectangle(value, path, positive=False):
        require(isinstance(value, dict) and set(value) == {'x', 'y', 'width', 'height'},
                path, 'rettangolo x/y/width/height richiesto')
        for name, maximum in (('x', 960), ('y', 640), ('width', 960), ('height', 640)):
            number = value[name]
            require(type(number) in (int, float) and 0 <= number <= maximum and math.isfinite(number),
                    path + '.' + name, 'numero finito non negativo entro viewport richiesto')
        require(value['x'] + value['width'] <= 960 and value['y'] + value['height'] <= 640,
                path, 'rettangolo fuori dal viewport 960×640')
        if positive:
            require(value['width'] > 0 and value['height'] > 0, path, 'area contenuto positiva richiesta')
    for name in ('header', 'content', 'guide'):
        rectangle(layout[name], 'layout.' + name, name == 'content')
    regions = layout['sceneSafeRegions']
    require(isinstance(regions, list) and len(regions) <= 64,
            'layout.sceneSafeRegions', 'lista di massimo 64 rettangoli richiesta')
    for index, region in enumerate(regions):
        rectangle(region, 'layout.sceneSafeRegions.' + str(index))
    return deepcopy(layout)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def require(condition, path, message):
    if not condition:
        raise ThemeError(path, message)


def semver(value):
    require(isinstance(value, str) and bool(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value)),
            'version', 'versione semantica canonica richiesta')
    return tuple(int(v) for v in value.split('.'))


def revision_key(identity):
    require(isinstance(identity, dict), 'revision', 'identità richiesta')
    require(isinstance(identity.get('id'), str) and bool(ID.fullmatch(identity['id'])) and not identity['id'].startswith('builtin.'),
            'revision.id', 'ID non valido/riservato')
    semver(identity.get('version'))
    require(isinstance(identity.get('digest'), str) and bool(re.fullmatch(r'[0-9a-f]{64}', identity['digest'])),
            'revision.digest', 'digest SHA256 richiesto')
    return identity['id'] + '@' + identity['version'] + '#' + identity['digest']


def sync_directory(path):
    descriptor = os.open(str(path), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(canonical_bytes(value) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def manager_lock(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.theme-manager.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _inventory(root, *, allow_integrity=True):
    root = Path(root).resolve()
    require(root.is_dir(), 'source', 'cartella richiesta')
    manifest_path = root / 'bundle.json'
    require(manifest_path.exists(), 'bundle.json', 'manifest mancante')
    manifest_mode = manifest_path.lstat()
    require(stat.S_ISREG(manifest_mode.st_mode) and manifest_mode.st_nlink == 1,
            'bundle.json', 'manifest regolare senza link richiesto')
    require(manifest_mode.st_size <= MAX_MANIFEST_BYTES, 'bundle.json', 'manifest troppo grande')
    try:
        descriptor = os.open(manifest_path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    except OSError as error:
        raise ThemeError('bundle.json', 'manifest regolare senza link richiesto') from error
    with os.fdopen(descriptor, 'rb') as stream:
        opened_mode = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened_mode.st_mode) and opened_mode.st_nlink == 1,
                'bundle.json', 'manifest regolare senza link richiesto')
        require(opened_mode.st_size <= MAX_MANIFEST_BYTES, 'bundle.json', 'manifest troppo grande')
        opaque_paths = _declared_visual_data(stream.read(MAX_MANIFEST_BYTES + 1))
    entries, normalized, total = {}, set(), 0
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories:
            path = Path(parent) / name
            require(not path.is_symlink(), 'source', 'directory link non supportata')
            relative_path(path.relative_to(root).as_posix())
        for name in files:
            path = Path(parent) / name
            relative = relative_path(path.relative_to(root).as_posix())
            key = unicodedata.normalize('NFC', relative).casefold()
            require(key not in normalized, relative, 'nome duplicato normalizzato')
            normalized.add(key)
            mode = path.lstat()
            require(stat.S_ISREG(mode.st_mode) and mode.st_nlink == 1, relative, 'link/file speciale non supportato')
            _validate_file_suffix(relative, opaque_paths)
            require(mode.st_size <= MAX_FILE_BYTES, relative, 'file troppo grande')
            total += mode.st_size
            require(total <= MAX_PAYLOAD_BYTES, 'payload', 'budget complessivo superato')
            require(len(entries) < MAX_FILES, 'payload', 'troppi file')
            if relative == 'integrity.json':
                require(allow_integrity, relative, 'inventario generato dal builder')
                continue
            with path.open('rb') as stream:
                if path.suffix.lower() not in ALLOWED_SUFFIXES:
                    _validate_opaque_header(stream.read(16), relative)
                    stream.seek(0)
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            entries[relative] = {'sha256': digest, 'bytes': mode.st_size}
    require(REQUIRED <= set(entries), 'payload', 'manifest o registry mancante')
    return entries


def _declared_visual_data(contents):
    """Read only bounded declarations; full manifest validation follows later."""
    require(len(contents) <= MAX_MANIFEST_BYTES, 'bundle.json', 'manifest troppo grande')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'bundle.json', 'chiave JSON duplicata')
            result[key] = value
        return result
    try:
        manifest = json.loads(contents.decode('utf-8'), object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise ThemeError('bundle.json', 'JSON non valido') from error
    require(isinstance(manifest, dict), 'bundle.json', 'manifest oggetto richiesto')
    resources = manifest.get('resources', [])
    require(isinstance(resources, list) and len(resources) <= MAX_FILES, 'resources', 'inventario risorse non valido')
    paths = set()
    for resource in resources:
        require(isinstance(resource, dict), 'resources', 'descrittore risorsa non valido')
        if resource.get('type') == 'data':
            paths.add(relative_path(resource.get('path')))
    return paths


def _validate_file_suffix(relative, opaque_paths):
    path = Path(relative)
    require(not {suffix.lower() for suffix in path.suffixes} & NON_VISUAL_CODE_SUFFIXES,
            relative, 'codice nativo/script/installatore non consentito')
    require(path.suffix.lower() in ALLOWED_SUFFIXES or relative in opaque_paths,
            relative, 'tipo file non consentito: dati visuali opachi richiedono dichiarazione data')


def _validate_opaque_header(header, relative):
    # This prevents common renamed executable payloads, not arbitrary code or
    # malicious author QML. The trusted author-code model remains unchanged.
    magic = (b'\x7fELF', b'MZ', b'#!', b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
             b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca')
    require(not header.startswith(magic), relative, 'eseguibile rinominato non consentito come dato visuale')


def payload_digest(entries):
    return hashlib.sha256(canonical_bytes({'integrityVersion': 1, 'files': entries})).hexdigest()


def verify_integrity(root):
    inventory = _inventory(root)
    integrity = read_json(Path(root) / 'integrity.json')
    require(isinstance(integrity, dict) and set(integrity) == {'integrityVersion', 'files', 'digest'}
            and type(integrity['integrityVersion']) is int and integrity['integrityVersion'] == 1,
            'integrity.json', 'formato inventario non valido')
    require(integrity['files'] == inventory, 'integrity.json', 'inventario/hash dei file non corrispondente')
    digest = payload_digest(inventory)
    require(integrity['digest'] == digest, 'integrity.digest', 'digest payload non corrispondente')
    return digest, inventory


def effective_manifest(value, surfaces):
    """Runtime-only Base fallback for the four additive Casa surfaces."""
    result=deepcopy(value)
    coverage=result['coverage']
    known=set(coverage['surfaces']) | set(coverage['fallbacks'])
    casa={'casa.overview','casa.devices','casa.detail','settings.casa'}
    if set(surfaces)-known == casa:
        coverage['fallbacks']=sorted(set(coverage['fallbacks']) | casa)
        coverage['mode']='partial'
    return result


def _manifest(value, root, profile=None):
    require(isinstance(value, dict) and not set(value) - MANIFEST_FIELDS, 'bundle.json', 'campo sconosciuto')
    for key in ('bundleFormat', 'id', 'version', 'name', 'engineApi', 'contextApis', 'targetProfile',
                'qtMinimum', 'qtModules', 'coverage', 'adjustments', 'trust', 'resources'):
        require(key in value, 'bundle.' + key, 'campo richiesto')
    require(type(value['bundleFormat']) is int and value['bundleFormat'] == 1, 'bundleFormat', 'formato non supportato')
    require(type(value['engineApi']) is int and value['engineApi'] == 2, 'engineApi', 'API non supportata')
    identifier = value['id']
    require(isinstance(identifier, str) and bool(ID.fullmatch(identifier)) and '.' in identifier
            and not identifier.startswith(('builtin.', 'smartpc.')), 'bundle.id', 'namespace autore richiesto')
    semver(value['version'])
    require(isinstance(value['name'], str) and 1 <= len(value['name']) <= 80, 'bundle.name', 'nome richiesto')
    require(value['trust'] == 'author-code', 'bundle.trust', 'modello codice visuale autore richiesto')
    require(value.get('retention', 'all') in ('all', 'latest'), 'bundle.retention', 'politica revisioni non valida')
    require(value['targetProfile'] == 'a733-960x640-eglfs', 'targetProfile', 'profilo non supportato')
    minimum = semver(value['qtMinimum'])
    require(minimum >= (6, 8, 2), 'qtMinimum', 'API bundle richiede Qt 6.8.2 o superiore')
    apis = value['contextApis']
    require(isinstance(apis, dict) and apis and not set(apis) - set(CONTEXT_APIS), 'contextApis', 'API contesti non valide')
    for key, version in apis.items():
        require(type(version) is int and version == CONTEXT_APIS[key], 'contextApis.' + key, 'versione API incompatibile')
    modules = value['qtModules']
    allowed_modules = {'QtQuick', 'QtQuick.Shapes', 'QtQuick.Controls', 'QtQuick.Layouts', 'QtQml', 'QtQuick.Window',
                       'SmartPC.ThemeApi', 'QtQuick.Timeline', 'QtQuick.Particles'}
    require(isinstance(modules, list) and all(isinstance(m, str) and m in allowed_modules for m in modules) and len(modules) == len(set(modules))
            and 'SmartPC.ThemeApi' in modules and 'QtQuick' in modules, 'qtModules', 'moduli richiesti non validi')
    adjustments = value['adjustments']
    require(isinstance(adjustments, list) and all(isinstance(v, str) for v in adjustments) and len(adjustments) == len(set(adjustments))
            and set(adjustments) <= {'paletteMode', 'textScale', 'motionMode'}, 'adjustments', 'adattamenti non validi')
    document = read_json(Path(root) / 'theme-api/surfaces.json')
    surfaces = {row['id'] for row in document['surfaces']}
    coverage = value['coverage']
    require(isinstance(coverage, dict) and set(coverage) == {'mode', 'surfaces', 'fallbacks'}
            and coverage['mode'] in ('partial', 'complete'), 'coverage', 'copertura esplicita richiesta')
    for field in ('surfaces', 'fallbacks'):
        values = coverage[field]
        require(isinstance(values, list) and all(isinstance(s, str) for s in values)
                and len(values) == len(set(values)) and set(values) <= surfaces, 'coverage.' + field, 'superfici non valide')
    own, fallback = set(coverage['surfaces']), set(coverage['fallbacks'])
    # Validate additive coverage without changing the immutable author payload.
    coverage=effective_manifest(value,surfaces)['coverage']
    fallback=set(coverage['fallbacks'])
    require(not own & fallback and own | fallback == surfaces, 'coverage', 'ogni superficie richiede renderer o fallback esplicito')
    require(coverage['mode'] != 'complete' or not fallback, 'coverage', 'copertura completa non ammette fallback')
    if 'layout' in value:
        require('shell.main' in own, 'layout', 'layout personalizzato richiede shell.main di proprietà del tema')
        validate_layout(value['layout'])
    resources = value['resources']
    require(isinstance(resources, list) and len(resources) <= MAX_FILES, 'resources', 'inventario risorse non valido')
    ids, paths = set(), set()
    for resource in resources:
        require(isinstance(resource, dict) and set(resource) == {'id', 'path', 'type'}, 'resources', 'descrittore risorsa non valido')
        require(isinstance(resource['id'], str) and bool(ID.fullmatch(resource['id'])) and resource['id'] not in ids,
                'resources.id', 'ID non valido/duplicato')
        ids.add(resource['id'])
        path = relative_path(resource['path'])
        require(path not in paths, 'resources.path', 'risorsa duplicata')
        paths.add(path)
        require(isinstance(resource['type'], str) and resource['type'] in RESOURCE_TYPES, 'resources.type', 'tipo risorsa non supportato')
    if profile:
        require(semver(profile.get('qtVersion', '0.0.0')) >= minimum, 'qtMinimum', 'Qt destinatario incompatibile')
        available = profile.get('qtModules')
        if available is not None:
            require(set(modules) <= set(available), 'qtModules', 'moduli mancanti sul destinatario')
    return surfaces


def _registry(registry, manifest, inventory, app_root):
    require(isinstance(registry, dict) and not set(registry) - REGISTRY_FIELDS
            and type(registry.get('registryVersion')) is int and registry['registryVersion'] == 1,
            'visual-registry.json', 'registry non valido')
    rows = registry.get('presentations', [])
    require(isinstance(rows, list), 'presentations', 'lista richiesta')
    seen, covered = set(), set()
    context_surfaces = {r['id']: r for r in read_json(Path(app_root) / 'theme-api/surfaces.json')['surfaces']}
    def descriptor(identifier, row, family):
        require(isinstance(identifier, str) and bool(ID.fullmatch(identifier)) and identifier.startswith(manifest['id'] + '.')
                and identifier not in seen, 'registry.id', 'ID duplicato o fuori namespace')
        seen.add(identifier)
        require(isinstance(row, dict), 'registry.' + identifier, 'descrittore richiesto')
        allowed = {'id', 'file', 'apiVersion', 'contextApi', 'name', 'contentIds', 'events', 'parameters', 'sceneMode', 'footprint', 'respectsOccupiedRegions', 'dataDomains', 'dataProjection'}
        require(not set(row) - allowed, 'registry.' + identifier, 'campo sconosciuto')
        if 'dataProjection' in row:
            require(family == 'presentations' and row.get('contextApi') == 'page2' and row['dataProjection'] in ('full','route'),
                    'registry.' + identifier + '.dataProjection', 'proiezione dati non valida')
        if 'dataDomains' in row:
            domains = row['dataDomains']
            require(family == 'presentations' and row.get('contextApi') == 'page2',
                    'registry.' + identifier + '.dataDomains', 'selezione domini riservata a PageContext')
            require(isinstance(domains, list) and all(isinstance(name, str) and name in
                    ('weather', 'account', 'nextEvent', 'sport', 'team', 'fantasy', 'racing') for name in domains)
                    and len(domains) == len(set(domains)),
                    'registry.' + identifier + '.dataDomains', 'domini non validi o duplicati')
        path = relative_path(row.get('file'))
        require(path in inventory and path.endswith('.qml'), 'registry.' + identifier + '.file', 'componente QML mancante')
        require(type(row.get('apiVersion')) is int and row['apiVersion'] in ((2,) if family in ('presentations', 'sceneRenderers') else (1,)),
                'registry.' + identifier + '.apiVersion', 'API renderer incompatibile')
        if family == 'presentations':
            contents = row.get('contentIds')
            require(isinstance(contents, list) and contents and all(isinstance(c, str) and c in context_surfaces for c in contents) and len(contents) == len(set(contents)),
                    'registry.' + identifier + '.contentIds', 'superfici non valide')
            require('scene.main' not in contents, 'registry.' + identifier + '.contentIds',
                    'scene.main richiede sceneRenderers e theme.scene.renderer')
            for content in contents:
                expected = context_surfaces[content]['hostFamily']
                context_api = row.get('contextApi')
                api_name = 'notification1' if expected == 'notification' else 'page2' if expected == 'page' else expected + '1'
                require(context_api == api_name, 'registry.' + identifier + '.contextApi', 'API contesto incompatibile per ' + content)
                require(expected in manifest['contextApis'], 'contextApis', 'API contesto non dichiarata')
            covered.update(contents)
        elif family == 'sceneRenderers':
            require(row.get('contextApi') == 'scene1' and 'scene' in manifest['contextApis'], 'scene.contextApi', 'SceneContext API1 tipizzato richiesto')
            require(row.get('sceneMode') in ('actor', 'background', 'decoration', 'canvas'), 'sceneMode', 'modalità scena non valida')
            footprint = row.get('footprint', {})
            require(isinstance(footprint, dict) and set(footprint) == {'width', 'height'}
                    and all(type(v) in (int, float) and math.isfinite(v) and 0 < v <= 960 for v in footprint.values()),
                    'footprint', 'ingombro richiesto')
            require(footprint['height'] <= 640, 'footprint.height', 'ingombro fuori viewport')
            if row['sceneMode'] == 'canvas':
                require(row.get('respectsOccupiedRegions') is True, 'scene.respectsOccupiedRegions', 'canvas deve rispettare gli ingombri della shell')
        elif family == 'recipes':
            require(isinstance(row.get('events', []), list) and all(isinstance(e, str) for e in row.get('events', [])), 'events', 'eventi non validi')
            require(isinstance(row.get('parameters', {}), dict), 'parameters', 'parametri non validi')
            for name, spec in row.get('parameters', {}).items():
                require(isinstance(name, str) and isinstance(spec, dict) and set(spec) == {'minimum', 'maximum'}
                        and all(type(v) in (int, float) and math.isfinite(v) for v in spec.values())
                        and spec['minimum'] <= spec['maximum'], 'parameters.' + name, 'intervallo non valido')
    for row in rows:
        require(isinstance(row, dict), 'presentations', 'descrittore richiesto')
        descriptor(row.get('id'), row, 'presentations')
    for field in ('recipes', 'iconRenderers', 'sceneRenderers'):
        definitions = registry.get(field, {})
        require(isinstance(definitions, dict), field, 'oggetto richiesto')
        for identifier, row in definitions.items():
            descriptor(identifier, row, field)
    sets = registry.get('iconSets', {})
    require(isinstance(sets, dict), 'iconSets', 'oggetto richiesto')
    for identifier, definitions in sets.items():
        require(isinstance(identifier, str) and identifier.startswith(manifest['id'] + '.') and bool(ID.fullmatch(identifier))
                and identifier not in seen and isinstance(definitions, dict), 'iconSets', 'set fuori namespace o duplicato')
        seen.add(identifier)
    if 'scene.main' in manifest['coverage']['surfaces'] and registry.get('sceneRenderers'):
        covered.add('scene.main')
    require(set(manifest['coverage']['surfaces']) == covered, 'coverage', 'copertura e renderer dichiarati non corrispondono')


def _extended_tokens(tokens, manifest):
    require(isinstance(tokens, dict) and len(tokens) <= 256, 'extendedTokens', 'descrittori non validi')
    aliases = set()
    for name, spec in tokens.items():
        require(isinstance(name, str) and name.startswith(manifest['id'] + '.') and bool(ID.fullmatch(name)), 'extendedTokens', 'token fuori namespace')
        require(isinstance(spec, dict) and not set(spec) - {'type', 'default', 'minimum', 'maximum', 'enum', 'alias'}
                and {'type', 'default', 'alias'} <= set(spec), name, 'descrittore tipizzato richiesto')
        alias = spec['alias']
        require(isinstance(alias, str) and bool(re.fullmatch(r'[a-z][A-Za-z0-9]*', alias)) and alias not in aliases
                and alias not in {'context', 'style', 'base', 'parent', 'children', 'data', 'objectName', 'active', 'id', 'property', 'signal', 'readonly', 'required', 'default', 'function', 'import', 'pragma', 'destroy' }, name, 'alias QML non valido/duplicato')
        aliases.add(alias)
        value, kind = spec['default'], spec['type']
        valid = type(value) is bool if kind == 'bool' else type(value) is int if kind == 'int' else type(value) in (int, float) and math.isfinite(value) if kind == 'real' else isinstance(value, str) and bool(re.fullmatch(r'#[0-9a-fA-F]{6}', value)) if kind == 'color' else isinstance(value, str) and len(value) <= 120 if kind == 'string' else False
        require(valid, name, 'default/tipo non valido')
        for key in ('minimum', 'maximum'):
            if key in spec:
                require(kind in ('int', 'real') and type(spec[key]) in (int, float) and math.isfinite(spec[key]), name, 'vincolo incompatibile')
                require(value >= spec[key] if key == 'minimum' else value <= spec[key], name, 'default fuori intervallo')
        if 'enum' in spec:
            require(isinstance(spec['enum'], list) and 1 <= len(spec['enum']) <= 64 and all(type(item) is type(value) or kind == 'real' and type(item) in (int, float) and math.isfinite(item) for item in spec['enum']) and any(type(item) is type(value) and item == value or kind == 'real' and type(item) in (int, float) and item == value for item in spec['enum']), name, 'enum/default incompatibile')


def _lint_visual(path, manifest):
    from theme_api_contract import qml_tokens
    source = path.read_text(encoding='utf-8')
    tokens = qml_tokens(source)
    forbidden = {'XMLHttpRequest', 'WebSocket', 'LocalStorage', 'WorkerScript', 'FileDialog', 'FolderDialog',
                 'ApplicationWindow'}
    for index, (kind, value) in enumerate(tokens):
        if kind == 'code' and value in forbidden:
            raise ThemeError(str(path), 'API fuori contratto: ' + value)
        if kind == 'code' and value == 'Window' and index + 1 < len(tokens) and tokens[index + 1] == ('code', '{'):
            raise ThemeError(str(path), 'nuove Window fuori contratto')
        if tokens[index:index + 3] in ([('code', 'Qt'), ('code', '.'), ('code', 'quit')], [('code', 'Qt'), ('code', '.'), ('code', 'exit')]):
            raise ThemeError(str(path), 'uscita globale fuori contratto')
    # Imports are declarations, not arbitrary source substring matching.
    for match in re.finditer(r'^\s*import\s+([^\n;]+)', source, re.MULTILINE):
        declaration = match.group(1).strip()
        if declaration.startswith(('"', "'")):
            local = declaration.split()[0].strip('"\'')
            require(local == '.' or not any(p == '..' for p in local.split('/')) and not local.startswith('/')
                    and ':' not in local, str(path), 'import locale fuori bundle')
        else:
            module = declaration.split()[0]
            require(module in manifest['qtModules'], str(path), 'modulo non dichiarato: ' + module)
    for kind, value in tokens:
        if kind == 'string' and isinstance(value, str) and re.match(r'^(https?|file|ftp|qrc):', value):
            raise ThemeError(str(path), 'URL esterna non portabile')


def _image_budget(path):
    """Bound common decoded pixel dimensions before Qt preflight performs decoding."""
    import struct
    data = path.read_bytes()
    dimensions = None
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        dimensions = struct.unpack('>II', data[16:24])
    elif data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        dimensions = struct.unpack('<HH', data[6:10])
    elif path.suffix.lower() == '.svg':
        import xml.etree.ElementTree as ET
        require(b'<!DOCTYPE' not in data.upper() and b'<!ENTITY' not in data.upper(), str(path), 'entità SVG non supportate')
        try:
            document = ET.fromstring(data)
        except ET.ParseError as error:
            raise ThemeError(str(path), 'SVG non valido') from error
        for element in document.iter():
            for attribute, value in element.attrib.items():
                require(not attribute.endswith('href') or value.startswith('#'), str(path), 'riferimento SVG esterno non supportato')
        viewbox = document.get('viewBox', '').replace(',', ' ').split()
        if len(viewbox) == 4:
            dimensions = tuple(float(v) for v in viewbox[2:])
        else:
            try:
                dimensions = (float(document.attrib['width'].removesuffix('px')), float(document.attrib['height'].removesuffix('px')))
            except (KeyError, ValueError):
                raise ThemeError(str(path), 'dimensioni SVG esplicite richieste')
    elif data.startswith(b'\xff\xd8'):
        index = 2
        while index + 9 < len(data):
            if data[index] != 255:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xD8, 0xD9):
                index += 2
                continue
            length = int.from_bytes(data[index + 2:index + 4], 'big')
            require(length >= 2, str(path), 'JPEG non valido')
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                dimensions = (int.from_bytes(data[index + 7:index + 9], 'big'), int.from_bytes(data[index + 5:index + 7], 'big'))
                break
            index += length + 2
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        try:
            from PIL import Image
            with Image.open(path) as image:
                dimensions = image.size
        except ImportError as error:
            raise ThemeError(str(path), 'decodifica WebP richiede Pillow o preflight Qt dedicato') from error
    require(dimensions is not None and all(math.isfinite(v) and 0 < v <= 8192 for v in dimensions), str(path), 'dimensioni immagine non valide')
    estimate = math.ceil(dimensions[0]) * math.ceil(dimensions[1]) * 4
    require(estimate <= MAX_IMAGE_BYTES, str(path), 'budget pixel decodificati superato')
    return estimate


def validate_project(project, app_root=ROOT, profile=None, *, check_integrity=False):
    project = Path(project).resolve()
    inventory = _inventory(project)
    manifest = read_json(project / 'bundle.json')
    _manifest(manifest, app_root, profile)
    registry = read_json(project / 'visual-registry.json')
    _registry(registry, manifest, inventory, app_root)
    _extended_tokens(manifest.get('extendedTokens', {}), manifest)
    declared = {resource['path'] for resource in manifest['resources']}
    resource_files = {p for p in inventory if p.startswith(('qml/', 'assets/'))}
    require(resource_files <= declared and declared <= set(inventory), 'resources', 'ogni QML/asset deve essere inventariato')
    image_bytes = 0
    for resource in manifest['resources']:
        path = canonical_file(project, resource['path'])
        suffix = path.suffix.lower()
        expected = {'qml': {'.qml'}, 'js': {'.js', '.mjs'}, 'font': {'.ttf', '.otf', '.woff', '.woff2'},
                    'image': {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif'}, 'preview': {'.png', '.jpg', '.jpeg', '.svg', '.webp'},
                    'license': {'.txt', '.md', '.license'}, 'data': DATA_SUFFIXES}
        if resource['type'] == 'data':
            require(suffix in DATA_SUFFIXES or suffix not in ALLOWED_SUFFIXES,
                    resource['path'], 'tipo risorsa/estensione incompatibili: codice/font/immagini richiedono tipo specifico')
        else:
            require(suffix in expected[resource['type']], resource['path'], 'tipo risorsa/estensione incompatibili')
        if resource['type'] in ('image', 'preview'):
            image_bytes += _image_budget(path)
            require(image_bytes <= MAX_IMAGE_BYTES, 'resources', 'budget complessivo pixel superato')
    for relative in inventory:
        if relative.endswith(('.qml', '.js', '.mjs')):
            _lint_visual(canonical_file(project, relative), manifest)
    pack = read_json(project / 'theme.json')
    require(pack.get('id') == manifest['id'] and pack.get('version') == manifest['version'], 'theme.json', 'identità diversa dal bundle')
    require(pack.get('extends') in (None, 'base'), 'extends', 'dipendenze fra temi devono essere risolte dal builder')
    require(not (set(pack.get('presentations', {})) - set(manifest['coverage']['surfaces'])), 'theme.presentations', 'renderer non dichiarato in coverage')
    require('scene.main' not in pack.get('presentations', {}), 'theme.presentations.scene.main',
            'la scena primaria si seleziona con theme.scene.renderer')
    selected_scene = pack.get('scene', {}).get('renderer', 'builtin.actor')
    scene_owned = 'scene.main' in manifest['coverage']['surfaces']
    require(scene_owned == (selected_scene in registry.get('sceneRenderers', {})), 'coverage.scene.main',
            'la scena selezionata richiede coverage propria; una scena Base richiede fallback')
    rows = {row['id']: row for row in registry.get('presentations', [])}
    for surface in manifest['coverage']['surfaces']:
        if surface == 'scene.main' and pack.get('scene', {}).get('renderer') in registry.get('sceneRenderers', {}):
            # Coverage describes a supplied capability, even if initially off.
            continue
        renderer = pack.get('presentations', {}).get(surface)
        require(renderer in rows and surface in rows[renderer]['contentIds'], 'theme.presentations.' + surface, 'renderer selezionato mancante/incompatibile')
    catalog = ThemeCatalog(root=app_root)
    revision = {'id': manifest['id'], 'version': manifest['version'], 'digest': payload_digest(inventory),
                'payload': str(project), 'manifest': manifest, 'registry': registry, 'files': inventory}
    register_catalog(catalog, revision)
    catalog.validate_pack(pack)
    for variant in ('day', 'night'):
        catalog.resolve(manifest['id'], variant=variant)
    digest = verify_integrity(project)[0] if check_integrity else payload_digest(inventory)
    return {'reportVersion': 1, 'status': 'valid', 'validation': 'static', 'runtimeVerification': 'unverified',
            'id': manifest['id'], 'version': manifest['version'], 'digest': digest, 'files': inventory,
            'fileCount': len(inventory), 'payloadBytes': sum(v['bytes'] for v in inventory.values()),
            'estimatedImageBytes': image_bytes, 'manifest': manifest, 'registry': registry,
            'trust': 'author-code', 'sandbox': False}


def register_catalog(catalog, revision):
    """Register one immutable revision; caller chooses explicitly which is active."""
    surfaces={row['id'] for row in read_json(catalog.root/'theme-api/surfaces.json')['surfaces']}
    manifest, registry = effective_manifest(revision['manifest'],surfaces), revision['registry']
    payload = Path(revision['payload']).resolve()
    key = revision_key(revision)
    files = revision.get('files') or _inventory(payload)
    def row(identifier, definition):
        result = deepcopy(definition)
        result['id'] = identifier
        result['sourceRoot'] = str(payload)
        result['sourceUrl'] = canonical_file(payload, definition['file']).as_uri()
        if 'dataProjection' in definition: result['dataProjection'] = definition['dataProjection']
        result['rendererIdentity'] = {'origin': 'bundle', 'id': identifier, 'context': definition.get('contextApi', ''),
                                      'revision': key, 'resource': definition['file'], 'digest': revision['digest'],
                                      'resourceDigest': files[definition['file']]['sha256']}
        result['rendererKey'] = 'bundle:' + hashlib.sha256(canonical_bytes(result['rendererIdentity'])).hexdigest()
        return result
    for definition in registry.get('presentations', []):
        catalog.presentations[definition['id']] = row(definition['id'], definition)
    for field, attribute in (('recipes', 'recipes'), ('iconRenderers', 'icon_renderers'), ('sceneRenderers', 'scene_renderers')):
        for identifier, definition in registry.get(field, {}).items():
            getattr(catalog, attribute)[identifier] = row(identifier, definition)
    catalog.icon_sets.update(deepcopy(registry.get('iconSets', {})))
    for name, specification in manifest.get('extendedTokens', {}).items():
        catalog.contract[name] = {k: deepcopy(v) for k, v in specification.items() if k != 'alias'}
    catalog.packs[manifest['id']] = read_json(payload / 'theme.json')
    catalog.directories[manifest['id']] = payload
    revisions = getattr(catalog, 'bundle_revisions', {})
    revisions[manifest['id']] = {k: deepcopy(revision[k]) for k in ('id', 'version', 'digest')}
    catalog.bundle_revisions = revisions
    metadata = getattr(catalog, 'bundle_metadata', {})
    metadata[manifest['id']] = deepcopy(manifest)
    catalog.bundle_metadata = metadata
    revision_metadata = getattr(catalog, 'bundle_revision_metadata', {})
    revision_metadata[key] = deepcopy(manifest)
    catalog.bundle_revision_metadata = revision_metadata
    layouts = getattr(catalog, 'bundle_layouts', {})
    # Registration of another revision of the same ID must also clear an old
    # custom layout when the newly selected manifest omits it.
    if 'layout' in manifest:
        layouts[manifest['id']] = validate_layout(manifest['layout'])
    else:
        layouts.pop(manifest['id'], None)
    catalog.bundle_layouts = layouts


def generate_extended_facade(manifest):
    """One descriptor definition generates typed QML properties and tool metadata."""
    _extended_tokens(manifest.get('extendedTokens', {}), manifest)
    lines = ['import QtQuick', 'import SmartPC.ThemeApi 2.0', 'QtObject {',
             '    property ThemeStyle base: null']
    metadata = ['import QtQuick.tooling 1.2', 'Module {', '    Component {',
                '        name: "ThemeRoles"', '        prototype: "QObject"',
                '        exports: ["ThemeRoles 1.0"]',
                '        Property { name: "base"; type: "ThemeStyle"; isPointer: true }']
    for name, descriptor in sorted(manifest.get('extendedTokens', {}).items()):
        alias, kind = descriptor['alias'], descriptor['type']
        key = json.dumps(name, ensure_ascii=False)
        value = json.dumps(descriptor['default'], ensure_ascii=False, allow_nan=False)
        lines.append('    readonly property ' + kind + ' ' + alias + ': base && base.tokenSnapshot[' + key + '] !== undefined ? base.tokenSnapshot[' + key + '] : ' + value)
        metadata.append('        Property { name: "' + alias + '"; type: "' + kind + '"; isReadonly: true }')
    lines.extend(['}', ''])
    metadata.extend(['    }', '}', ''])
    return {'qml/ThemeRoles.qml': '\n'.join(lines), 'qml/ThemeRoles.qmltypes': '\n'.join(metadata)}


def build_bundle(project, archive_path, *, app_root=ROOT, profile=None):
    project = Path(project).resolve()
    manifest = read_json(project / 'bundle.json')
    if not manifest.get('extendedTokens'):
        return _write_bundle(project, archive_path, app_root=app_root, profile=profile)
    # Validate the author's source first; generated roles are part of the final
    # payload identity, never mutable globals shared by installed themes.
    validate_project(project, app_root, profile)
    with tempfile.TemporaryDirectory(prefix='smartpc-theme-roles-') as temporary:
        prepared = Path(temporary) / 'payload'
        shutil.copytree(project, prepared)
        files = generate_extended_facade(manifest)
        generated_paths = set(files)
        resources = [r for r in manifest['resources'] if r['path'] not in generated_paths]
        for path, source in files.items():
            identifier = 'generated.roles' if path.endswith('.qml') else 'generated.roles.types'
            require(not any(r['id'] == identifier for r in resources), 'resources', 'ID generato riservato')
            target = prepared / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding='utf-8')
            resources.append({'id': identifier, 'path': path, 'type': 'qml' if path.endswith('.qml') else 'data'})
        manifest['resources'] = resources
        atomic_json(prepared / 'bundle.json', manifest)
        (prepared / 'integrity.json').unlink(missing_ok=True)
        report = _write_bundle(prepared, archive_path, app_root=app_root, profile=profile)
        report['generated'] = sorted(generated_paths)
        return report


def _write_bundle(project, archive_path, *, app_root=ROOT, profile=None):
    """Reproducible bytes: sorted entries and fixed ZIP timestamps, no author data."""
    project, destination = Path(project).resolve(), Path(archive_path).resolve()
    require(not destination.exists(), 'destination', 'destinazione già esistente')
    require(not destination.is_relative_to(project), 'destination', 'archivio deve essere esterno al progetto')
    report = validate_project(project, app_root, profile)
    inventory = report['files']
    integrity = {'integrityVersion': 1, 'files': inventory, 'digest': report['digest']}
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.theme-build-', dir=destination.parent)
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in sorted([*inventory, 'integrity.json']):
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                data = canonical_bytes(integrity) + b'\n' if relative == 'integrity.json' else canonical_file(project, relative).read_bytes()
                if relative != 'integrity.json':
                    require(hashlib.sha256(data).hexdigest() == inventory[relative]['sha256'], relative, 'sorgente modificata durante build')
                archive.writestr(info, data)
        with open(temporary, 'rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        sync_directory(destination.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {**report, 'operation': 'build', 'archive': str(destination)}


def _extract_archive(source, destination):
    require(source.stat().st_size <= MAX_ARCHIVE_BYTES, 'archive', 'archivio troppo grande')
    deadline = time.monotonic() + 30
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        require(len(entries) <= MAX_FILES + 1, 'archive', 'troppi file')
        names, total = set(), 0
        for info in entries:
            require(not info.is_dir(), 'archive', 'entry directory non canonica: il builder include solo file')
            path = relative_path(info.filename)
            name = unicodedata.normalize('NFC', path).casefold()
            require(name not in names, path, 'nome duplicato normalizzato')
            names.add(name)
            mode = info.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG), path, 'link/file speciale non supportato')
            require(not info.flag_bits & 1, path, 'archivio cifrato non supportato')
            require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), path, 'compressione non supportata')
            require(info.file_size <= MAX_FILE_BYTES, path, 'file troppo grande')
            total += info.file_size
            require(total <= MAX_PAYLOAD_BYTES, 'archive', 'budget espanso superato')
        require(REQUIRED | {'integrity.json'} <= {i.filename for i in entries}, 'archive', 'payload incompleto')
        manifest_info = next(info for info in entries if info.filename == 'bundle.json')
        require(manifest_info.file_size <= MAX_MANIFEST_BYTES, 'bundle.json', 'manifest troppo grande')
        with archive.open(manifest_info) as stream:
            opaque_paths = _declared_visual_data(stream.read(MAX_MANIFEST_BYTES + 1))
        for info in entries:
            _validate_file_suffix(info.filename, opaque_paths)
        require(shutil.disk_usage(destination.parent).free >= total + MAX_PAYLOAD_BYTES,
                'storage', 'spazio insufficiente per staging e precedente')
        for info in entries:
            require(time.monotonic() < deadline, 'archive', 'timeout estrazione')
            target = canonical_file(destination, info.filename, must_exist=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with archive.open(info) as stream, target.open('xb') as output:
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    written += len(chunk)
                    require(written <= info.file_size and written <= MAX_FILE_BYTES, info.filename, 'dimensione espansa incoerente')
                    if written == len(chunk) and Path(info.filename).suffix.lower() not in ALLOWED_SUFFIXES:
                        _validate_opaque_header(chunk[:16], info.filename)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            require(written == info.file_size, info.filename, 'file troncato')


class BundleManager:
    def __init__(self, data_root, app_root=ROOT):
        self.root = Path(data_root).resolve()
        self.app_root = Path(app_root).resolve()
        for name in ('theme-bundles', 'theme-staging', 'theme-quarantine', 'theme-reports'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.resources = ResourceResolver(self.app_root)

    def _revision_path(self, identity):
        revision_key(identity)
        return self.root / 'theme-bundles' / identity['id'] / (identity['version'] + '-' + identity['digest'])

    def import_bundle(self, source, *, preflight=None, require_preflight=False, profile=None):
        source = Path(source).resolve()
        with manager_lock(self.root):
            temporary = Path(tempfile.mkdtemp(prefix='.import-', dir=self.root / 'theme-staging'))
            payload = temporary / 'payload'
            payload.mkdir()
            try:
                if source.is_dir():
                    built = temporary / 'source.zip'
                    build_bundle(source, built, app_root=self.app_root, profile=profile)
                    _extract_archive(built, payload)
                    built.unlink()
                else:
                    try:
                        _extract_archive(source, payload)
                    except (zipfile.BadZipFile, RuntimeError) as error:
                        raise ThemeError('archive', 'archivio ZIP non valido') from error
                checked = validate_project(payload, self.app_root, profile, check_integrity=True)
                identity = {k: checked[k] for k in ('id', 'version', 'digest')}
                final = self._revision_path(identity)
                siblings = final.parent
                if siblings.exists():
                    for sibling in siblings.glob(identity['version'] + '-*'):
                        require(sibling == final, 'version', 'stesso ID/versione con payload diverso: conflitto')
                if final.exists():
                    existing = self.verify_revision(identity)
                    existing['idempotent'] = True
                    return existing
                runtime = {'status': 'unverified', 'reason': 'preflight Qt non richiesto/eseguito'}
                if preflight:
                    runtime = preflight(payload, checked['manifest'], checked['registry'])
                    require(isinstance(runtime, dict) and runtime.get('status') in ('passed', 'failed', 'unverified'), 'preflight', 'risposta preflight non valida')
                    require(runtime['status'] != 'failed', 'preflight', 'preflight renderer fallito')
                require(not require_preflight or runtime['status'] == 'passed', 'preflight', 'compatibilità runtime non verificata')
                revision = {**identity, 'key': revision_key(identity), 'manifest': checked['manifest'], 'registry': checked['registry'],
                            'files': checked['files'], 'preflight': runtime}
                atomic_json(temporary / 'revision.json', revision)
                for directory, _, _ in os.walk(payload, topdown=False):
                    sync_directory(directory)
                sync_directory(temporary)
                siblings.mkdir(parents=True, exist_ok=True)
                os.rename(temporary, final)
                sync_directory(siblings)
                return self.verify_revision(identity)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)

    def verify_revision(self, identity):
        path = self._revision_path(identity)
        revision = read_json(path / 'revision.json')
        require(revision_key(revision) == revision_key(identity), 'revision', 'metadati identità incoerenti')
        digest, inventory = verify_integrity(path / 'payload')
        require(digest == identity['digest'] and revision.get('files') == inventory, 'revision', 'revisione modificata fuori manager')
        require(revision['manifest'] == read_json(path / 'payload/bundle.json')
                and revision['registry'] == read_json(path / 'payload/visual-registry.json'), 'revision', 'metadati diversi dal payload')
        revision.update(path=str(path), payload=str(path / 'payload'))
        self.resources.register(revision['key'], revision['payload'])
        return revision

    def list_revisions(self, *, include_quarantined=False):
        result = []
        for descriptor in sorted((self.root / 'theme-bundles').glob('*/*/revision.json')):
            try:
                revision = self.verify_revision(read_json(descriptor))
                quarantine = self.root / 'theme-quarantine' / (revision['digest'] + '.json')
                revision['quarantined'] = quarantine.exists()
                if include_quarantined or not revision['quarantined']:
                    result.append(revision)
            except (OSError, ThemeError):
                continue
        return sorted(result, key=lambda r: (r['id'], semver(r['version']), r['digest']))

    def register_catalog(self, catalog, revision):
        revision = self.verify_revision(revision)
        register_catalog(catalog, revision)
        return revision

    def export_bundle(self, identity, destination):
        revision = self.verify_revision(identity)
        return build_bundle(revision['payload'], destination, app_root=self.app_root)

    def quarantine(self, identity, reason):
        revision = self.verify_revision(identity)
        record = {'revision': {k: revision[k] for k in ('id', 'version', 'digest')}, 'reason': str(reason)[:500]}
        with manager_lock(self.root):
            atomic_json(self.root / 'theme-quarantine' / (revision['digest'] + '.json'), record)
        return record
