#!/usr/bin/env python3
"""Generate/check the public API contract reference, schema and fingerprint.

Does not install a QML module or claim its runtime availability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import shutil

DEFAULT_ROOT = Path(__file__).parent
from theme_api_contract import ContractError, ThemeApiContract


def contract_typeinfo(contract):
    """Tooling blueprint; A1 must compare it to actual registered metaobjects."""
    primitives = {'string': 'QString', 'color': 'QColor', 'int': 'int', 'real': 'double',
                  'bool': 'bool', 'scalar': 'QVariant', 'legacyMap': 'QVariantMap', 'array': 'QVariantList',
                  'Rect': 'QRectF', 'Point': 'QPointF', 'ActionResult': 'QVariantMap'}
    version = contract.surfaces_document['module']
    quoted = lambda value: json.dumps(value, ensure_ascii=False)
    lines = ['import QtQuick.tooling 1.2', '', '// Generated contract blueprint; not runtime type availability.',
             '// A1 must verify registration/metaobjects before this is used by the public SDK.', '', 'Module {']
    for name, definition in {**contract.types, **contract.contexts, **contract.models}.items():
        if name in ('Rect', 'Point', 'ActionResult'):
            continue
        lines += ['    Component {', '        name: ' + quoted(name),
                  '        prototype: ' + quoted(definition.get('extends', 'QObject')),
                  '        exports: [' + quoted(f"{version['uri']}/{name} {version['major']}.{version['minor']}") + ']',
                  f"        exportMetaObjectRevisions: [{version['major'] * 256 + version['minor']}]",
                  '        isCreatable: false']
        for field, spec in definition.get('fields', {}).items():
            kind = spec['type']
            nullable_primitive = spec.get('nullable') and kind in primitives and kind not in ('Rect', 'Point')
            native = 'QVariant' if nullable_primitive else primitives.get(kind, kind)
            pointer = kind not in primitives
            lines += ['        Property {', '            name: ' + quoted(field), '            type: ' + quoted(native),
                      '            isReadonly: true']
            if pointer:
                lines.append('            isPointer: true')
            lines.append('        }')
        for method, spec in definition.get('methods', {}).items():
            lines += ['        Method {', '            name: ' + quoted(method)]
            if spec['result'] != 'void':
                lines.append('            type: ' + quoted(primitives.get(spec['result'], spec['result'])))
            for index, parameter in enumerate(spec['parameters']):
                lines += ['            Parameter {', '                name: ' + quoted('arg' + str(index)),
                          '                type: ' + quoted(primitives.get(parameter, parameter)), '            }']
            lines.append('        }')
        for signal, spec in definition.get('signals', {}).items():
            lines += ['        Signal {', '            name: ' + quoted(signal)]
            for index, parameter in enumerate(spec['parameters']):
                lines += ['            Parameter {', '                name: ' + quoted('arg' + str(index)),
                          '                type: ' + quoted(primitives.get(parameter, parameter)), '            }']
            lines.append('        }')
        lines.append('    }')
    return '\n'.join([*lines, '}', ''])


def rendered_files(contract):
    metadata = contract.metadata()
    lines = ['# SmartPC Theme API 2 — contract reference', '',
             '**Contract only: QML runtime module, broker and adapters are not implemented.**', '',
             'Generated from the four canonical JSON documents. Do not edit generated files.', '',
             f'API fingerprint: `{contract.fingerprint}`', '',
             'This fingerprint is independent from the schema-1 registry fingerprint.', '',
             '## Surfaces', '', '| Content ID | Context/version | Host | Legacy route | Actions |',
             '| --- | --- | --- | --- | --- |']
    for row in contract.surfaces.values():
        lines.append(f"| {row['id']} | {row['context']} {row['contextVersion']} | {row['hostFamily']} | {row['legacyRoute'] or '—'} | {', '.join(row['actions']) or '—'} |")
    for group, definitions in [('Contexts', contract.contexts), ('DTOs', contract.types)]:
        lines += ['', '## ' + group]
        for name, definition in definitions.items():
            lines += ['', '### ' + name, '', '| Read-only field | Type | Optional/nullable | Constraints |',
                      '| --- | --- | --- | --- |']
            for key, spec in contract.fields(name).items():
                limits = {k: v for k, v in spec.items() if k not in ('type', 'nullable', 'required', 'readOnly')}
                lines.append(f"| {key} | {spec['type']} | {'optional' if not spec.get('required', True) else 'required'} / {'nullable' if spec.get('nullable') else 'non-null'} | {json.dumps(limits, ensure_ascii=False).replace('|', '&#124;')} |")
            for method, spec in definition.get('methods', {}).items():
                lines += ['', f"Method `{method}({', '.join(spec['parameters'])}) → {spec['result']}`."]
            for signal, spec in definition.get('signals', {}).items():
                lines += ['', f"Signal `{signal}({', '.join(spec['parameters'])})`."]
    lines += ['', '## Models', '', '| Model | Row type | Identity |', '| --- | --- | --- |']
    for name, model in contract.models.items():
        lines.append(f"| {name} | {model['itemType']} | {model['identityRole']} |")
    lines += ['', '## Actions', '', 'Shape and per-surface allowlist checks do not authorize an action in the live app.', '',
              'The A1 broker must also check lifecycle, generation, urgent priority and backend state.', '',
              '| Action | Target | Required arguments |', '| --- | --- | --- |']
    for name, action in contract.actions.items():
        lines.append(f"| {name} | {'required' if action['target'].get('minLength') else 'optional'} | {json.dumps(action['arguments'], ensure_ascii=False).replace('|', '&#124;')} |")
    lines += ['', '## Semantic roles', '',
              'The usage graph is a contract. New foreground resolution and runtime contrast checks require A1/G21.', '',
              '| Usage | Foreground role | Background token | Minimum | Kind |', '| --- | --- | --- | --- | --- |']
    for usage in contract.semantic_document['usages']:
        lines.append(f"| {usage['id']} | {usage['foreground']} | {usage['backgroundToken']} | {usage['minimum']} | {usage['kind']} |")
    serialize = lambda value: json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    files = {'reference.md': '\n'.join(lines) + '\n', 'snapshots.schema.json': serialize(contract.json_schema()),
             'api-metadata.json': serialize(metadata), 'contract.qmltypes': contract_typeinfo(contract),
             'fixture-requirements.json': serialize(contract.surfaces_document['fixtureRequirements']),
             'settings-rows.json': serialize(contract.action_document['settingRows'])}
    files['manifest.json'] = serialize({'generatedVersion': 1, 'apiFingerprint': contract.fingerprint,
                                       'sha256': {name: hashlib.sha256(body.encode()).hexdigest() for name, body in files.items()}})
    return files


def lint_blueprint(contract, executable):
    """Check the synthetic typeinfo without installing/importing a runtime API."""
    if not shutil.which(executable):
        raise FileNotFoundError('qmllint non disponibile: ' + executable)
    with tempfile.TemporaryDirectory(prefix='smartpc-api-typeinfo-') as directory:
        root = Path(directory)
        module = root / 'SmartPC/ThemeApi'; module.mkdir(parents=True)
        (module / 'contract.qmltypes').write_text(contract_typeinfo(contract))
        version = contract.surfaces_document['module']
        (module / 'qmldir').write_text('module SmartPC.ThemeApi\ntypeinfo contract.qmltypes\ndepends QtQml 2.0\ndepends QtQuick 2.0\n')
        source = f'''import QtQuick
import SmartPC.ThemeApi {version['major']}.{version['minor']}
Item {{
    id: root
    required property PageContext context
    readonly property color surface: root.context.style.surface
    readonly property string timeText: root.context.clock.timeText
    readonly property bool hasTemperature: root.context.weather.temperature.available
}}
'''
        records = []
        for filename, body, should_pass in [('Valid.qml', source, True), ('Invalid.qml', source.replace('style.surface', 'style.surfaec'), False)]:
            path = root / filename; path.write_text(body)
            result = subprocess.run([executable, '--ignore-settings', '--unresolved-type', 'error', '-W', '0', '-I', str(root), str(path)],
                                    capture_output=True, text=True, timeout=30)
            if should_pass and result.returncode != 0 or not should_pass and (result.returncode == 0 or 'surfaec' not in result.stderr or 'missing-property' not in result.stderr):
                raise ContractError('api.typeinfo.lint', filename, (result.stdout + result.stderr)[-3000:])
            records.append({'fixture': filename, 'exitCode': result.returncode, 'expectedSuccess': should_pass})
        return {'status': 'verified', 'fixtures': records, 'runtimeModuleVerified': False,
                'scope': 'Synthetic tooling contract only; A1 must compare actual registered types/metaobjects'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', action='store_true', help='Fail if source coverage or generated artifacts differ')
    parser.add_argument('--qmllint', help='Also check the typeinfo blueprint with this qmllint executable')
    args = parser.parse_args()
    try:
        contract = ThemeApiContract(args.root)
        coverage = contract.check_source_coverage()
        output = args.output or args.root / 'theme-api/generated'
        expected = rendered_files(contract)
        if args.check:
            stale = [name for name, body in expected.items() if not (output / name).is_file() or (output / name).read_bytes() != body.encode()]
            if stale:
                raise ContractError('api.generated.stale', str(output), 'rigenerare: ' + ', '.join(stale))
        else:
            output.mkdir(parents=True, exist_ok=True)
            for name, body in expected.items():
                (output / name).write_text(body, encoding='utf-8')
        lint = lint_blueprint(contract, args.qmllint) if args.qmllint else {'status': 'notVerified', 'runtimeModuleVerified': False}
        print(json.dumps({'status': 'verified' if args.check else 'generated', **contract.metadata(), 'sourceCoverage': coverage,
                          'typeinfoBlueprint': lint}, ensure_ascii=False))
        return 0
    except (ContractError, OSError, subprocess.TimeoutExpired) as error:
        issue = error.issue() if isinstance(error, ContractError) else {'code': 'api.io', 'message': str(error)}
        print(json.dumps({'status': 'invalid', 'issues': [issue]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
