"""Canonical local resource references for app and immutable visual bundles.

A resource URL conveys origin/revision as well as location. This is containment
and integrity checking for trusted author code, not a QML security sandbox.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
from pathlib import Path, PurePosixPath
import re
import unicodedata
from theme_core import ThemeError

DIGEST = re.compile(r'^[a-f0-9]{64}$')


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ThemeError('resource.path', 'percorso relativo richiesto')
    if any(ord(c) < 32 for c in value) or '\\' in value or ':' in value:
        raise ThemeError('resource.path', 'percorso non portabile')
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ThemeError('resource.path', 'percorso non canonico o traversal')
    if unicodedata.normalize('NFC', value) != value:
        raise ThemeError('resource.path', 'nome Unicode non canonico')
    return value


def canonical_file(root, relative, *, must_exist=True):
    relative = relative_path(relative)
    root = Path(root).resolve()
    candidate = root / relative
    for part in (candidate, *candidate.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ThemeError('resource.path', 'link non supportato')
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ThemeError('resource.path', 'percorso fuori origine')
    if must_exist and not resolved.is_file():
        raise ThemeError('resource.path', 'risorsa mancante')
    return resolved


@dataclass(frozen=True)
class ResourceRef:
    origin: str
    id: str
    revision: str
    resource: str
    digest: str = ''
    context: str = ''

    def identity(self):
        return asdict(self)


class ResourceResolver:
    def __init__(self, app_root, bundle_roots=None):
        self.app_root = Path(app_root).resolve()
        self.bundle_roots = dict(bundle_roots or {})

    def register(self, revision, payload):
        self.bundle_roots[revision] = Path(payload).resolve()

    def resolve(self, reference, *, verify=True):
        ref = reference if isinstance(reference, ResourceRef) else ResourceRef(**reference)
        if ref.origin == 'app':
            root = self.app_root
        elif ref.origin == 'bundle' and ref.revision in self.bundle_roots:
            root = self.bundle_roots[ref.revision]
        else:
            raise ThemeError('resource.origin', 'origine/revisione non registrata')
        path = canonical_file(root, ref.resource)
        if ref.digest:
            if not DIGEST.fullmatch(ref.digest):
                raise ThemeError('resource.digest', 'digest non valido')
            if verify:
                with path.open('rb') as stream:
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                if actual != ref.digest:
                    raise ThemeError('resource.digest', 'risorsa modificata')
        return {'url': path.as_uri(), 'path': str(path), 'identity': ref.identity()}

    def renderer(self, descriptor, *, revision='', root=None):
        """Descriptor adapter shared by page/motion/icon/scene host registries."""
        source_root = Path(descriptor.get('sourceRoot', root or self.app_root))
        origin = 'bundle' if descriptor.get('sourceRoot') else 'app'
        identity = descriptor.get('rendererIdentity', {})
        ref = ResourceRef(origin, descriptor.get('id', identity.get('id', '')),
                          revision or identity.get('revision', ''), descriptor['file'],
                          identity.get('resourceDigest', ''), descriptor.get('contextApi', ''))
        if origin == 'bundle':
            self.register(ref.revision, source_root)
        return self.resolve(ref)
