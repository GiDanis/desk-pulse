#!/usr/bin/env python3
"""Offline AI authoring SDK: projects, truthful Qt previews and bundle tooling.

No provider I/O, device preferences or running kiosk are needed by this tool.
The author-code trust model permits executable QML; validation is not a sandbox.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / 'examples/bundles/studio-ambient'
SDK_DIRS = {'components', 'presentations', 'themes', 'icons', 'motion', 'scenes',
            'theme-api', 'fixtures', 'extensions', 'qml', 'examples', 'authoring'}
SDK_SUFFIXES = {'.py', '.qml', '.js', '.json', '.qmltypes', '.md', '.svg', '.ttf', '.otf',
                '.png', '.jpg', '.html', '.base64', '.txt', '.sh'}


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def issue(code, message, **detail):
    return {'code': code, 'message': message, **detail}


def initialize(destination, identifier='studio.personal', name='Tema personale', *, example=EXAMPLE):
    """A runnable project with explicit coverage, never a pretend full renderer set."""
    from theme_core import ThemeError
    if not isinstance(identifier, str) or not re.fullmatch(r'[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+', identifier):
        raise ThemeError('id', 'ID namespaced richiesto, esempio studio.personal')
    destination = Path(destination)
    if destination.exists():
        raise ThemeError('destination', 'cartella già esistente')
    shutil.copytree(example, destination)
    for filename in ('bundle.json', 'visual-registry.json', 'theme.json'):
        path = destination / filename
        source = json.loads(path.read_text())
        previous = 'studio.ambient'
        def replace(value):
            if isinstance(value, str):
                return identifier + value[len(previous):] if value.startswith(previous) else value
            if isinstance(value, list):
                return [replace(item) for item in value]
            if isinstance(value, dict):
                return {replace(key): replace(item) for key, item in value.items()}
            return value
        source = replace(source)
        if filename != 'visual-registry.json':
            source['name'] = name
        dump(path, source)
    return {'reportVersion': 1, 'operation': 'init', 'status': 'created',
            'destination': str(destination.resolve()), 'id': identifier,
            'newRenderers': ['home.now', 'alerts.banner.small', 'alerts.banner.large', 'shell.main'],
            'remainingSurfaces': 'Explicit Base fallbacks declared in bundle.json; editable using the generated contracts.'}


def find_qmllint():
    executable=shutil.which('qmllint') or shutil.which('pyside6-qmllint')
    if executable: return executable
    try:
        import PySide6
        bundled=Path(PySide6.__file__).parent/'qmllint'
        if bundled.is_file(): return str(bundled)
    except ImportError:
        pass
    return None


def lint_project(project, executable=None):
    """Run real qmllint; retain missing-tool status and file/line diagnostics."""
    project = Path(project).resolve()
    if executable is None:
        executable = find_qmllint()
    if not executable or not (Path(executable).is_file() or shutil.which(str(executable))):
        return {'status': 'notVerified', 'issues': [issue('lint.unavailable', 'qmllint non disponibile')], 'files': []}
    files = []
    for path in sorted(project.rglob('*.qml')):
        value = subprocess.run([executable, '--ignore-settings', '--unresolved-type', 'error', '-W', '0',
                                '-I', str(ROOT / 'qml'), str(path)], capture_output=True, text=True, timeout=30)
        files.append({'file': str(path.relative_to(project)), 'exitCode': value.returncode,
                      'diagnostics': value.stdout + value.stderr})
    return {'status': 'passed' if files and all(row['exitCode'] == 0 for row in files) else 'failed', 'files': files,
            'tool': str(executable), 'modulePath': str(ROOT / 'qml'),
            'issues': [] if files and all(row['exitCode'] == 0 for row in files) else [issue('lint.failed', 'Correggere gli errori QML riportati')]}


def validate(project, *, lint=False, qmllint=None, runtime=False, qt_python=None, profile=None):
    from theme_bundle import validate_project
    report = validate_project(Path(project), app_root=ROOT, profile=profile)
    report = deepcopy(report)
    report.setdefault('verification', {})
    report['verification'].setdefault('boardRuntime', 'notVerified')
    if report.get('status') not in ('valid', 'passed', 'verified'):
        return report
    if lint:
        report['lint'] = lint_project(project, qmllint)
        report['verification']['qmlLint'] = report['lint']['status']
        if report['lint']['status'] == 'failed':
            report['status'] = 'invalid'
        elif report['lint']['status'] == 'notVerified':
            report['status'] = 'notVerified'
    if runtime:
        with tempfile.TemporaryDirectory(prefix='smartpc-theme-preflight-') as directory:
            result = subprocess.run([qt_python or sys.executable, str(ROOT / 'theme_bundle_preview.py'),
                                     str(Path(project).resolve()), '--output', directory, '--matrix'],
                                    capture_output=True, text=True, timeout=120)
            try:
                preview = json.loads(result.stdout)
            except json.JSONDecodeError:
                preview = {'status': 'notVerified', 'issues': [issue('preview.unavailable', (result.stderr + result.stdout)[-5000:])]}
            report['runtime'] = preview
            report['verification']['rendererFixtures'] = preview['status']
            if preview['status'] == 'failed':
                report['status'] = 'invalid'
            elif preview['status'] != 'passed' and report['status'] != 'invalid':
                report['status'] = 'notVerified'
    return report


def write_full_kit(destination, *, profile=None):
    """Copy a source SDK, not user state. The resulting kit has no repo dependency."""
    from theme_api_contract import ThemeApiContract
    from theme_api_tools import rendered_files
    from theme_authoring import generated_schema
    from theme_core import ThemeCatalog, ThemeError
    destination = Path(destination).resolve()
    if destination.exists() or destination.is_relative_to(ROOT):
        raise ThemeError('output', 'cartella nuova esterna al runtime richiesta')
    stage = Path(tempfile.mkdtemp(prefix='.smartpc-kit-', dir=destination.parent))
    try:
        sdk = stage / 'sdk'; sdk.mkdir()
        copied = {}
        for path in sorted(ROOT.rglob('*')):
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink() or '__pycache__' in relative.parts:
                continue
            allowed = (len(relative.parts) == 1 and (path.suffix in {'.py', '.qml', '.sh'} or path.name == 'smartpc-theme')) or relative.parts[0] in SDK_DIRS
            if not allowed or path.suffix not in SDK_SUFFIXES and path.name not in ('qmldir', 'smartpc-theme'):
                continue
            target = sdk / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            if path.name in ('smartpc-theme', 'run.sh'): target.chmod(path.stat().st_mode & 0o777)
            copied[str(relative)] = hashlib.sha256(target.read_bytes()).hexdigest()
        contract = ThemeApiContract(ROOT)
        contracts = stage / 'contracts'; contracts.mkdir()
        for name, body in rendered_files(contract).items():
            (contracts / name).write_text(body, encoding='utf-8')
        for path in (ROOT / 'theme-api').glob('*.json'):
            shutil.copyfile(path, contracts / path.name)
        dump(contracts / 'theme-pack.schema.json', generated_schema(ThemeCatalog()))
        dump(stage / 'target-profile.json', profile or {'status': 'notVerified', 'reason': 'Profilo board non acquisito da questo export'})
        for path in (ROOT / 'authoring/templates').iterdir():
            if path.is_file():
                shutil.copyfile(path, stage / path.name)
            elif path.is_dir():
                shutil.copytree(path, stage / path.name)
        if (ROOT.parent / 'LICENSE').is_file():
            shutil.copyfile(ROOT.parent / 'LICENSE', stage / 'LICENSE')
        dump(stage / 'kit-manifest.json', {'kitVersion': 2, 'engineApi': 2, 'apiFingerprint': contract.fingerprint,
                                          'module': 'SmartPC.ThemeApi 2.0', 'sdkSha256': copied,
                                          'runtimeProof': 'Generate with validate --runtime; board acceptance is separate'})
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {'reportVersion': 1, 'operation': 'kit', 'status': 'created', 'destination': str(destination),
            'apiFingerprint': contract.fingerprint, 'sdkFiles': len(copied), 'privateStateIncluded': False,
            'runtimeModuleIncluded': (destination / 'sdk/qml/SmartPC/ThemeApi/qmldir').is_file()}


def inspect_archive(source):
    import zipfile
    source = Path(source)
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        for name in names:
            parts = Path(name).parts
            if name.startswith('/') or '..' in parts or '\\' in name:
                raise ValueError('Percorso non valido nell’archivio')
        if len(names) != len(set(names)):
            raise ValueError('File duplicato nell’archivio')
        if archive.getinfo('bundle.json').file_size > 2 * 1024 * 1024:
            raise ValueError('Manifest troppo grande')
        manifest = json.loads(archive.read('bundle.json'))
        inventory = json.loads(archive.read('integrity.json'))
        return {'reportVersion': 1, 'operation': 'inspect', 'status': 'inspected', 'bundle': manifest,
                'integrity': inventory, 'archiveSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'verification': {'runtime': 'notVerified', 'scope': 'Metadata inspection; use validate/import for integrity and compatibility'}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init'); init.add_argument('destination', type=Path); init.add_argument('--id', default='studio.personal'); init.add_argument('--name', default='Tema personale')
    check = commands.add_parser('validate'); check.add_argument('project', type=Path); check.add_argument('--lint', action='store_true'); check.add_argument('--qmllint'); check.add_argument('--runtime', action='store_true'); check.add_argument('--qt-python'); check.add_argument('--profile', type=Path)
    preview = commands.add_parser('preview'); preview.add_argument('project', type=Path); preview.add_argument('--output', type=Path, required=True); preview.add_argument('--qt-python'); preview.add_argument('--matrix', action='store_true'); preview.add_argument('--visible', action='store_true')
    pack = commands.add_parser('pack'); pack.add_argument('project', type=Path); pack.add_argument('destination', type=Path)
    kit = commands.add_parser('kit'); kit.add_argument('destination', type=Path); kit.add_argument('--profile', type=Path)
    info = commands.add_parser('inspect'); info.add_argument('archive', type=Path)
    receive = commands.add_parser('import'); receive.add_argument('project', type=Path); receive.add_argument('--store', type=Path, required=True, help='Application data root containing theme-bundles; does not apply the theme')
    transfer = commands.add_parser('transfer'); transfer.add_argument('archive', type=Path); transfer.add_argument('--board', required=True); transfer.add_argument('--identity', type=Path)
    export = commands.add_parser('export'); export.add_argument('identity'); export.add_argument('destination', type=Path); export.add_argument('--store', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        profile = json.loads(args.profile.read_text()) if getattr(args, 'profile', None) else None
        if args.command == 'init':
            report = initialize(args.destination, args.id, args.name)
        elif args.command == 'validate':
            report = validate(args.project, lint=args.lint, qmllint=args.qmllint, runtime=args.runtime, qt_python=args.qt_python, profile=profile)
        elif args.command == 'preview':
            command = [args.qt_python or sys.executable, str(ROOT / 'theme_bundle_preview.py'), str(args.project.resolve()), '--output', str(args.output.resolve())]
            if args.matrix: command.append('--matrix')
            if args.visible: command.append('--visible')
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            report = json.loads(result.stdout)
        elif args.command == 'pack':
            from theme_bundle import build_bundle
            report = build_bundle(args.project, args.destination)
        elif args.command == 'kit':
            args.destination.parent.mkdir(parents=True, exist_ok=True)
            report = write_full_kit(args.destination, profile=profile)
        elif args.command == 'inspect':
            report = inspect_archive(args.archive)
        elif args.command == 'import':
            from theme_bundle import BundleManager
            from theme_runtime import preflight
            revision=BundleManager(args.store,app_root=ROOT).import_bundle(args.project,preflight=preflight,require_preflight=True)
            report={'reportVersion':1,'operation':'import','status':'imported','revision':revision,'applied':False,'verification':{'preflight':'passed','boardEglfs':'notVerified'}}
        elif args.command == 'export':
            from theme_bundle import BundleManager
            match = re.fullmatch(r'(.+)@([0-9]+\.[0-9]+\.[0-9]+)#([0-9a-f]{64})', args.identity)
            if not match: raise ValueError('Identity richiesta: ID@VERSION#DIGEST')
            identity = dict(zip(('id', 'version', 'digest'), match.groups()))
            report = BundleManager(args.store).export_bundle(identity, args.destination)
        elif args.command == 'transfer':
            from theme_transfer import BoardTransport
            transport = BoardTransport(args.board, args.identity)
            # Transfer an immutable snapshot; the device imports and validates it later.
            with tempfile.TemporaryDirectory(prefix='smartpc-bundle-transfer-') as temporary:
                payload = Path(temporary) / 'theme.smartpc-theme'; shutil.copyfile(args.archive, payload)
                digest = hashlib.sha256(payload.read_bytes()).hexdigest()
                import shlex
                remote_profile = transport.profile()
                inbox = remote_profile['inbox']
                destination = inbox + '/' + digest + '.smartpc-theme'
                staging_name = '.receive-' + digest + '.smartpc-theme'
                staging_path = inbox + '/' + staging_name
                payload.rename(Path(temporary) / staging_name)
                ssh = ['ssh', *transport.options, '--', transport.destination]
                result = subprocess.run([*ssh, 'mkdir -p -- ' + shlex.quote(inbox)], capture_output=True, text=True, timeout=30)
                if result.returncode: raise ValueError('Creazione inbox fallita: ' + result.stderr[-1000:])
                transport.upload(Path(temporary), inbox)
                result = subprocess.run([*ssh, 'sha256sum -- ' + shlex.quote(staging_path)], capture_output=True, text=True, timeout=30)
                if result.returncode or result.stdout.split()[0] != digest: raise ValueError('SHA256 remoto diverso dal pacchetto trasferito')
                result = subprocess.run([*ssh, 'mv -- ' + shlex.quote(staging_path) + ' ' + shlex.quote(destination)], capture_output=True, text=True, timeout=30)
                if result.returncode: raise ValueError('Pubblicazione inbox fallita: ' + result.stderr[-1000:])
                report = {'reportVersion': 1, 'operation': 'transfer', 'status': 'transferred', 'archiveSha256': digest, 'destination': destination, 'applied': False, 'verification': {'remoteSha256': 'verified', 'deviceImport': 'notVerified'}}
    except (OSError, ValueError, TypeError, ImportError, KeyError, subprocess.TimeoutExpired) as error:
        detail = {'phase': 'operation'}
        if hasattr(error, 'path'):
            detail.update(path=error.path, pointer='/' + error.path.replace('.', '/'), phase='validation')
        report = {'reportVersion': 1, 'operation': args.command, 'status': 'invalid',
                  'issues': [issue('bundle.validation' if hasattr(error, 'path') else 'tool.failed', str(error), **detail)]}
    if args.format == 'json':
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(args.command + ': ' + report['status'])
        for error in report.get('issues', []): print('[' + error.get('code', 'error') + '] ' + error.get('message', ''))
    return 1 if report['status'] in ('invalid', 'failed') else 2 if report['status'] == 'notVerified' else 0


if __name__ == '__main__':
    raise SystemExit(main())
