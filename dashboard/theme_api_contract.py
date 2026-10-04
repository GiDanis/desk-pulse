"""Canonical public theme contracts. Pure checks; no Qt, services or user state.

This describes the API under construction, not an installed QML module.
Schema-1 registry fingerprints and compatibility remain independent.
"""
from __future__ import annotations

from copy import deepcopy
import ast
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).parent
DOCUMENTS = ('surfaces.json', 'contexts.json', 'actions.json', 'semantic-roles.json')
PRIMITIVES = {'string', 'int', 'real', 'bool', 'color', 'scalar', 'legacyMap', 'array'}
IDENTIFIER = re.compile(r'^[a-z][a-z0-9_.-]{0,127}$')
TYPE_NAME = re.compile(r'^[A-Z][A-Za-z0-9]*$')


def finite(value):
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


class ContractError(ValueError):
    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f'{path}: {message}')

    def issue(self):
        return {'code': self.code, 'path': self.path, 'message': self.message}


def read_document(path):
    path = Path(path)
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ContractError('api.json.size', str(path), 'contratto troppo grande')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('chiave duplicata: ' + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('numero non finito: ' + value)

    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as error:
        raise ContractError('api.json.invalid', str(path), str(error)) from error


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def qml_tokens(source):
    """Conservative source inventory, not a QML compiler or a sandbox.

    Discards comments, keeps string literals distinct, and accepts both quotes.
    Nonliteral routing calls must be explicitly inventoried in surfaces.json.
    """
    pattern = r'''//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_$][\w$]*|===|!==|==|!=|[^\s]'''
    result = []
    for match in re.finditer(pattern, source):
        token = match.group()
        if token.startswith(('//', '/*')):
            continue
        if token.startswith(('"', "'")):
            try:
                value = json.loads(token) if token.startswith('"') else ast.literal_eval(token)
            except (ValueError, SyntaxError):
                raise ContractError('api.source.string', 'QML', 'stringa non analizzabile')
            result.append(('string', value))
        else:
            result.append(('code', token))
    return result


class ThemeApiContract:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.documents = {name: read_document(self.root / 'theme-api' / name) for name in DOCUMENTS}
        for name, document in self.documents.items():
            self.require(isinstance(document, dict), name, 'oggetto contratto richiesto')
        self.surfaces_document = self.documents['surfaces.json']
        self.context_document = self.documents['contexts.json']
        self.action_document = self.documents['actions.json']
        self.semantic_document = self.documents['semantic-roles.json']
        self.contexts = self.context_document.get('contexts', {})
        self.types = self.context_document.get('types', {})
        self.models = self.context_document.get('models', {})
        self.actions = self.action_document.get('actions', {})
        self.validate_contract()

    @staticmethod
    def require(condition, path, message, code='api.contract.invalid'):
        if not condition:
            raise ContractError(code, path, message)

    def fields(self, name, seen=()):
        self.require(name not in seen, name, 'ereditarietà ciclica')
        definition = {**self.types, **self.contexts}.get(name)
        self.require(isinstance(definition, dict), name, 'tipo sconosciuto')
        inherited = self.fields(definition['extends'], (*seen, name)) if 'extends' in definition else {}
        result = {**inherited, **deepcopy(definition.get('fields', {}))}
        if name in self.contexts and 'contextVersion' in result:
            result['contextVersion'] = {**result['contextVersion'], 'const': definition['version']}
        return result

    def _check_spec(self, spec, path):
        self.require(isinstance(spec, dict), path, 'descrittore richiesto')
        allowed = {'type', 'nullable', 'required', 'readOnly', 'minimum', 'maximum', 'minLength',
                   'maxLength', 'maxItems', 'items', 'enum', 'const', 'format', 'unit'}
        self.require(not set(spec) - allowed, path, 'chiavi descrittore sconosciute')
        known = PRIMITIVES | set(self.types) | set(self.models) | set(self.contexts)
        self.require(spec.get('type') in known, path, 'riferimento al tipo sconosciuto')
        for key in ('nullable', 'required', 'readOnly'):
            if key in spec:
                self.require(type(spec[key]) is bool, path + '.' + key, 'booleano richiesto')
        if spec['type'] == 'array':
            self.require(spec.get('items') in known, path, 'tipo degli elementi sconosciuto')
        if 'enum' in spec:
            self.require(isinstance(spec['enum'], list) and bool(spec['enum']), path, 'enum vuota/invalida')
            for value in spec['enum']:
                self._value({k: v for k, v in spec.items() if k != 'enum'}, value, path)
        for key in ('minimum', 'maximum', 'minLength', 'maxLength', 'maxItems'):
            if key in spec:
                self.require(type(spec[key]) in (int, float) and finite(spec[key]), path, 'limite non finito')
                self.require(spec['type'] in ('int', 'real') if key in ('minimum', 'maximum') else spec['type'] == 'array' if key == 'maxItems' else spec['type'] in ('string', 'color'), path, 'limite incompatibile con il tipo')
                if key in ('minLength', 'maxLength', 'maxItems'):
                    self.require(type(spec[key]) is int and spec[key] >= 0, path, 'dimensione intera non negativa richiesta')
        if 'minimum' in spec and 'maximum' in spec:
            self.require(spec['minimum'] <= spec['maximum'], path, 'limiti invertiti')

    def validate_contract(self):
        module = self.surfaces_document.get('module')
        self.require(isinstance(module, dict) and module.get('uri') == 'SmartPC.ThemeApi'
                     and type(module.get('major')) is int and module['major'] == 2
                     and type(module.get('minor')) is int and module['minor'] >= 0,
                     'module', 'modulo/versione non supportati')
        for name, document in self.documents.items():
            self.require(isinstance(document, dict) and type(document.get('contractVersion')) is int
                         and document['contractVersion'] == 1, name, 'versione contratto non supportata')
            self.require(document.get('module') == module and document.get('apiState') == 'contractOnly', name,
                         'contratto incoerente; modulo runtime non ancora disponibile')
        for name in ('types', 'contexts', 'models'):
            mapping = self.context_document.get(name)
            self.require(isinstance(mapping, dict) and bool(mapping), name, 'mappa richiesta')
            self.require(all(TYPE_NAME.fullmatch(k) for k in mapping), name, 'nome di tipo invalido')
        names = [*self.types, *self.contexts, *self.models]
        self.require(len(names) == len(set(names)), 'types', 'nomi duplicati fra categorie')
        private = set(self.context_document['privateHandles'])
        for name, definition in {**self.types, **self.contexts}.items():
            self.require(isinstance(definition, dict) and isinstance(definition.get('fields'), dict), name, 'campi richiesti')
            for field, spec in self.fields(name).items():
                self.require(re.fullmatch(r'[a-z][A-Za-z0-9]*', field) and field not in private,
                             name + '.' + field, 'campo privato o nome invalido')
                self._check_spec(spec, name + '.' + field)
                self.require(spec.get('readOnly') is True, name + '.' + field, 'proprietà pubblica mutabile')
            if name in self.contexts:
                self.require(type(definition.get('version')) is int and definition['version'] >= 1, name, 'versione contesto richiesta')
                for method, spec in definition.get('methods', {}).items():
                    self.require(method not in private | set(self.action_document['privateEffects']), name + '.' + method, 'metodo privato esposto')
                    self.require(spec.get('result') in PRIMITIVES | set(self.types) | {'void'}, name + '.' + method, 'ritorno sconosciuto')
                    self.require(all(t in PRIMITIVES | set(self.types) for t in spec.get('parameters', [])), name + '.' + method, 'parametro sconosciuto')
                signals = definition.get('signals', {})
                self.require(isinstance(signals, dict), name + '.signals', 'mappa segnali richiesta')
                for signal, spec in signals.items():
                    self.require(re.fullmatch(r'[a-z][A-Za-z0-9]*', signal) and signal not in private,
                                 name + '.' + signal, 'segnale privato o nome invalido')
                    self.require(isinstance(spec, dict) and set(spec) == {'parameters'}
                                 and isinstance(spec['parameters'], list)
                                 and all(t in PRIMITIVES | set(self.types) for t in spec['parameters']),
                                 name + '.' + signal, 'parametri segnale invalidi')
        for name, model in self.models.items():
            self.require(model.get('itemType') in self.types, name, 'tipo riga sconosciuto')
            self.require(model.get('identityRole') in self.fields(model['itemType']), name, 'identità della riga assente')
            self.require(type(model.get('maxItems')) is int and model['maxItems'] > 0, name, 'limite elementi richiesto')
        self.require(isinstance(self.actions, dict) and bool(self.actions), 'actions', 'azioni richieste')
        for name, action in self.actions.items():
            self.require(re.fullmatch(r'[a-z][A-Za-z0-9_.-]{0,127}', name), name, 'ID azione invalido')
            self._check_spec(action['target'], name + '.target')
            self.require(action.get('authorizesRuntimeDispatch') is False, name, 'il contratto non autorizza dispatch runtime')
            self.require(isinstance(action.get('arguments'), dict) and isinstance(action.get('metadata'), dict), name, 'parametri richiesti')
            self.require(not set(action['arguments']) & set(action['metadata']), name, 'collisione metadata/argomenti')
            for key, spec in {**action['arguments'], **action['metadata']}.items():
                self._check_spec(spec, name + '.' + key)
        rows = self.surfaces_document.get('surfaces')
        self.require(isinstance(rows, list) and bool(rows), 'surfaces', 'lista superfici richiesta')
        self.surfaces = {}
        routes = set()
        for row in rows:
            identifier = row.get('id', '')
            self.require(isinstance(identifier, str) and IDENTIFIER.fullmatch(identifier), 'surfaces', 'ID invalido')
            self.require(identifier not in self.surfaces, identifier, 'ID superficie duplicato')
            self.require(row.get('context') in self.contexts, identifier, 'contesto sconosciuto')
            self.require(row.get('contextVersion') == self.contexts[row['context']]['version'], identifier, 'versione contesto incoerente')
            self.require(row.get('hostFamily') in ('page', 'overlay', 'shell', 'notification', 'scene'), identifier, 'famiglia host sconosciuta')
            self.require(isinstance(row.get('actions'), list) and len(row['actions']) == len(set(row['actions'])), identifier, 'allowlist invalida')
            self.require(not set(row['actions']) - set(self.actions), identifier, 'azione non dichiarata')
            route = row.get('legacyRoute')
            self.require(route is None or (isinstance(route, str) and bool(route) and route not in routes), identifier, 'route duplicata/invalida')
            if route:
                routes.add(route)
            source = row.get('legacySource', '')
            self.require(isinstance(source, str) and not Path(source).is_absolute()
                         and '..' not in Path(source).parts and (self.root / source).is_file(), identifier, 'sorgente legacy assente/fuori root')
            self.surfaces[identifier] = row
        dynamic = self.surfaces_document.get('dynamicRouting', [])
        self.require(isinstance(dynamic, list), 'dynamicRouting', 'lista richiesta')
        sites = set()
        for site in dynamic:
            self.require(isinstance(site, dict) and isinstance(site.get('file'), str)
                         and isinstance(site.get('expression'), str), 'dynamicRouting', 'sito richiesto')
            key = (site['file'], site['expression'])
            self.require(key not in sites, 'dynamicRouting', 'sito duplicato')
            sites.add(key)
            self.require(isinstance(site.get('possibleRoutes'), list) and bool(site['possibleRoutes'])
                         and not set(site['possibleRoutes']) - routes, 'dynamicRouting', 'destinazioni non coperte')
        setting_rows = self.action_document.get('settingRows', {}).get('sections', {})
        expected_sections = {name for name, row in self.surfaces.items() if row['context'] == 'SettingsContext'}
        self.require(set(setting_rows) == expected_sections, 'settings.rows', 'sezioni impostazioni mancanti/sconosciute')
        for section, rows in setting_rows.items():
            ids, positions = set(), set()
            for row in rows:
                self.require(isinstance(row.get('id'), str) and bool(row['id']) and row['id'] not in ids,
                             section, 'ID riga impostazioni duplicato/vuoto')
                self.require(type(row.get('legacyPosition')) is int and row['legacyPosition'] >= 0
                             and row['legacyPosition'] not in positions, section, 'posizione template invalida')
                ids.add(row['id']); positions.add(row['legacyPosition'])
        required = self.surfaces_document.get('fixtureRequirements', {})
        cases = required.get('requiredCases', [])
        expected_cases = {(row['id'], variant) for row in self.surfaces.values() for variant in row['variants'] or ['default']}
        found_cases, case_ids = set(), set()
        for case in cases:
            self.require(case['id'] not in case_ids and case.get('verification') == 'requiredNotExecuted', 'fixtures', 'caso duplicato o falsa verifica')
            case_ids.add(case['id']); found_cases.add((case['surfaceId'], case['variant']))
        self.require(found_cases == expected_cases and len(found_cases) == len(cases), 'fixtures', 'varianti mancanti/sconosciute')
        roles = self.semantic_document.get('roles', {})
        token_contract = read_document(self.root / 'themes/token-contract.json')['tokens']
        for name, role in roles.items():
            self.require(role.get('type') == 'color', name, 'ruolo colore richiesto')
            legacy = role.get('legacy', {})
            if 'token' in legacy:
                self.require(legacy['token'] in token_contract and token_contract[legacy['token']]['type'] == 'color', name, 'token colore legacy assente')
            else:
                self._value({'type': 'color'}, legacy.get('fixedColor'), name)
        usage_ids = set()
        for usage in self.semantic_document.get('usages', []):
            self.require(usage['id'] not in usage_ids, usage['id'], 'uso duplicato')
            usage_ids.add(usage['id'])
            self.require(usage.get('foreground') in roles, usage['id'], 'ruolo foreground assente')
            background = usage.get('backgroundToken')
            self.require(background in token_contract and token_contract[background]['type'] == 'color', usage['id'], 'sfondo sconosciuto')
            self.require(usage.get('kind') in ('text', 'indicator'), usage['id'], 'tipo uso invalido')
            self.require(type(usage.get('minimum')) in (int, float) and usage['minimum'] >= (4.5 if usage['kind'] == 'text' else 3), usage['id'], 'soglia insufficiente')
            self.require(bool(usage.get('surfaces')) and not set(usage['surfaces']) - set(self.surfaces), usage['id'], 'superficie uso sconosciuta')
            self.require(usage.get('variants') == ['day', 'night'], usage['id'], 'varianti richieste')
        self.require(bool(roles) and bool(usage_ids), 'semantic', 'grafo vuoto')
        self.require(self.semantic_document['policy']['runtimeChecksActive'] is False
                     and self.semantic_document['policy']['lightPaletteSupported'] is False,
                     'semantic.policy', 'G21 non ancora implementato')

    @property
    def fingerprint(self):
        return hashlib.sha256(canonical_bytes(self.documents)).hexdigest()

    def metadata(self):
        return {'availability': 'contractOnly', 'contractVersion': 1,
                'module': deepcopy(self.surfaces_document['module']), 'apiFingerprint': self.fingerprint,
                'surfaces': len(self.surfaces), 'contexts': len(self.contexts),
                'types': len(self.types), 'models': len(self.models), 'actions': len(self.actions),
                'contrastPairs': len(self.semantic_document['usages']),
                'requiredVariantCases': len(self.surfaces_document['fixtureRequirements']['requiredCases']),
                'runtimeModuleVerified': False}

    def _value(self, spec, value, path):
        if value is None and spec.get('nullable'):
            return
        kind = spec['type']
        if kind in ('real', 'int'):
            valid = type(value) is int if kind == 'int' else type(value) in (int, float)
            self.require(valid and finite(value), path, 'numero finito del tipo richiesto', 'api.value.type')
        elif kind == 'bool':
            self.require(type(value) is bool, path, 'booleano richiesto', 'api.value.type')
        elif kind in ('string', 'color'):
            self.require(isinstance(value, str), path, 'stringa richiesta', 'api.value.type')
            if kind == 'color':
                self.require(re.fullmatch(r'#[0-9a-fA-F]{6}', value), path, 'colore #RRGGBB richiesto', 'api.value.color')
            self.require(len(value) >= spec.get('minLength', 0) and len(value) <= spec.get('maxLength', len(value)), path, 'lunghezza fuori intervallo', 'api.value.range')
            if spec.get('format') == 'date':
                from datetime import date
                try:
                    date.fromisoformat(value)
                except ValueError as error:
                    raise ContractError('api.value.date', path, 'data ISO richiesta') from error
        elif kind == 'scalar':
            self.require(type(value) in (str, bool, int, float) or (value is None and spec.get('nullable')), path, 'scalare richiesto', 'api.value.type')
            if type(value) in (int, float):
                self.require(finite(value), path, 'numero non finito', 'api.value.type')
        elif kind == 'legacyMap':
            self.require(isinstance(value, dict), path, 'snapshot mappa richiesto', 'api.value.type')
            self.require(all(isinstance(k, str) for k in value), path, 'chiavi stringa richieste', 'api.value.json')
            try:
                canonical_bytes(value)
            except (TypeError, ValueError) as error:
                raise ContractError('api.value.json', path, 'snapshot JSON richiesto') from error
        elif kind == 'array' or kind in self.models:
            self.require(isinstance(value, list), path, 'lista richiesta', 'api.value.type')
            item_type = spec.get('items') if kind == 'array' else self.models[kind]['itemType']
            limit = spec.get('maxItems', 10000) if kind == 'array' else self.models[kind]['maxItems']
            self.require(len(value) <= limit, path, 'troppi elementi', 'api.value.range')
            ids = set()
            for index, item in enumerate(value):
                self._value({'type': item_type}, item, f'{path}/{index}')
                if kind in self.models:
                    identity = item[self.models[kind]['identityRole']]
                    self.require(isinstance(identity, str) and bool(identity), path, 'ID riga vuoto/invalido', 'api.value.identity')
                    self.require(identity not in ids, path, 'ID riga duplicato', 'api.value.identity')
                    ids.add(identity)
        else:
            self.require(kind in self.types or kind in self.contexts, path, 'tipo sconosciuto')
            self._object(self.fields(kind), value, path)
            definition = {**self.types, **self.contexts}[kind]
            for rule in definition.get('invariants', []):
                if all(type(value.get(k)) is type(v) and value[k] == v for k, v in rule['when'].items()):
                    self.require(all(value.get(k) is not None for k in rule['notNull']), path, 'dato disponibile privo di valore', 'api.value.availability')
        if 'const' in spec:
            self.require(type(value) is type(spec['const']) and value == spec['const'], path, 'valore costante richiesto', 'api.value.const')
        if 'enum' in spec:
            self.require(any(type(value) is type(candidate) and value == candidate for candidate in spec['enum']), path, 'valore fuori enum', 'api.value.enum')
        for key, predicate in (('minimum', lambda a, b: a >= b), ('maximum', lambda a, b: a <= b)):
            if key in spec:
                self.require(predicate(value, spec[key]), path, 'valore fuori intervallo', 'api.value.range')

    def _object(self, fields, value, path):
        self.require(isinstance(value, dict), path, 'oggetto richiesto', 'api.value.type')
        self.require(all(isinstance(k, str) for k in value), path, 'chiavi stringa richieste', 'api.value.type')
        self.require(not set(value) - set(fields), path, 'campi sconosciuti: ' + ', '.join(sorted(set(value) - set(fields))), 'api.value.unknown')
        for key, spec in fields.items():
            if key not in value:
                self.require(not spec.get('required', True), path + '/' + key, 'campo richiesto', 'api.value.required')
            else:
                self._value(spec, value[key], path + '/' + key)

    def validate_snapshot(self, type_name, value):
        self.require(type_name in self.types or type_name in self.models or type_name in self.contexts, type_name, 'tipo sconosciuto')
        self._value({'type': type_name}, value, type_name)

    def validate_request(self, surface_id, action_id, target_id='', arguments=None):
        self.require(surface_id in self.surfaces, surface_id, 'superficie sconosciuta', 'api.request.surface')
        self.require(action_id in self.surfaces[surface_id]['actions'], action_id, 'azione non consentita su questa superficie', 'api.request.action')
        action = self.actions[action_id]
        self._value(action['target'], target_id, action_id + '/targetId')
        self._object({**action['arguments'], **action['metadata']}, {} if arguments is None else arguments, action_id + '/arguments')
        return {'shapeVerified': True, 'runtimeDispatchVerified': False}

    def check_source_coverage(self):
        expected_routes = {s['legacyRoute'] for s in self.surfaces.values() if s['legacyRoute']}
        observed_routes, observed_contents, dynamic = set(), set(), set()
        for path in sorted(self.root.rglob('*.qml')):
            if 'design' in path.relative_to(self.root).parts:
                continue
            tokens = qml_tokens(path.read_text(encoding='utf-8'))
            for index, (kind, value) in enumerate(tokens):
                if kind != 'code':
                    continue
                if value == 'overlay' and index + 2 < len(tokens) and tokens[index + 1][1] in ('===', '!==', '==', '!=', '=') and tokens[index + 2][0] == 'string':
                    if tokens[index + 2][1]:
                        observed_routes.add(tokens[index + 2][1])
                if value == 'contentId' and index + 2 < len(tokens) and tokens[index + 1][1] == ':' and tokens[index + 2][0] == 'string':
                    if tokens[index + 2][1]:
                        observed_contents.add(tokens[index + 2][1])
                if value == 'pushOverlay' and index + 1 < len(tokens) and tokens[index + 1][1] == '(' and (not index or tokens[index - 1][1] != 'function'):
                    depth, args, cursor = 1, [], index + 2
                    while cursor < len(tokens) and depth:
                        if tokens[cursor][1] == '(' and tokens[cursor][0] == 'code':
                            depth += 1
                        elif tokens[cursor][1] == ')' and tokens[cursor][0] == 'code':
                            depth -= 1
                        if depth:
                            args.append(tokens[cursor])
                        cursor += 1
                    if len(args) == 1 and args[0][0] == 'string':
                        observed_routes.add(args[0][1])
                    else:
                        dynamic.add((path.relative_to(self.root).as_posix(), ''.join(v for _, v in args)))
                # SettingsPanel.targets covers conditional/dynamic destinations.
                if value == 'targets' and index + 2 < len(tokens) and tokens[index + 1][1] == ':' and tokens[index + 2][1] == '[':
                    cursor = index + 3
                    while cursor < len(tokens) and tokens[cursor][1] != ']':
                        if tokens[cursor][0] == 'string':
                            observed_routes.add(tokens[cursor][1])
                        cursor += 1
        approved = {(row['file'], row['expression']) for row in self.surfaces_document.get('dynamicRouting', [])}
        self.require(dynamic == approved, 'routes.dynamic', 'dispatch dinamici non censiti/obsoleti: ' + str(sorted(dynamic ^ approved)), 'api.coverage.dynamic')
        self.require(observed_routes == expected_routes, 'routes', 'route non coperte/obsolete: ' + str(sorted(observed_routes ^ expected_routes)), 'api.coverage.routes')
        registry = read_document(self.root / 'presentations/registry.json')
        registered = {cid for row in registry['presentations'] for cid in row['contentIds']}
        expected_hosted = {s['id'] for s in self.surfaces.values() if s['hostFamily'] in ('page', 'notification')}
        self.require(registered == expected_hosted, 'contentIds', 'content ID del registry non coperti/obsoleti: ' + str(sorted(registered ^ expected_hosted)), 'api.coverage.registry')
        self.require(not observed_contents - set(self.surfaces), 'contentIds', 'content ID QML non coperti: ' + str(sorted(observed_contents - set(self.surfaces))), 'api.coverage.contents')
        return {'routes': len(observed_routes), 'registeredContents': len(registered), 'dynamicDispatches': len(dynamic),
                'scope': 'Conservative literal/source inventory plus declared dynamic sites; not full QML data-flow analysis'}

    def json_schema(self):
        def convert(spec):
            kind = spec['type']
            if kind in ('string', 'color', 'int', 'real', 'bool'):
                result = {'type': {'int': 'integer', 'real': 'number', 'bool': 'boolean', 'color': 'string'}.get(kind, kind)}
                if kind == 'color':
                    result['pattern'] = '^#[0-9a-fA-F]{6}$'
            elif kind == 'scalar':
                result = {'type': ['string', 'boolean', 'integer', 'number']}
            elif kind == 'legacyMap':
                result = {'type': 'object'}
            elif kind == 'array' or kind in self.models:
                item = spec['items'] if kind == 'array' else self.models[kind]['itemType']
                result = {'type': 'array', 'items': convert({'type': item})}
                if kind in self.models:
                    result['maxItems'] = self.models[kind]['maxItems']
            else:
                result = {'$ref': '#/$defs/' + kind}
            for key in ('enum', 'const', 'minimum', 'maximum', 'minLength', 'maxLength', 'maxItems', 'format', 'readOnly'):
                if key in spec:
                    result[key] = deepcopy(spec[key])
            if 'unit' in spec:
                result['description'] = 'Unit: ' + spec['unit']
            return {'anyOf': [result, {'type': 'null'}]} if spec.get('nullable') else result

        definitions = {}
        for name in [*self.types, *self.contexts]:
            fields = self.fields(name)
            schema = {'type': 'object', 'properties': {k: convert(v) for k, v in fields.items()},
                      'required': [k for k, v in fields.items() if v.get('required', True)], 'additionalProperties': False}
            constraints = []
            for rule in {**self.types, **self.contexts}[name].get('invariants', []):
                constraints.append({'if': {'properties': {k: {'const': v} for k, v in rule['when'].items()}, 'required': list(rule['when'])},
                                    'then': {'properties': {k: {'not': {'type': 'null'}} for k in rule['notNull']}, 'required': rule['notNull']}})
            if constraints:
                schema['allOf'] = constraints
            definitions[name] = schema
        for name in self.models:
            definitions[name] = convert({'type': name})
        return {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'SmartPC Theme API 2 contract snapshots (not runtime availability)',
                '$defs': definitions, 'description': 'Choose an explicit $defs type. Python validator also checks model identity uniqueness and request allowlists.'}


def api_metadata(root=ROOT):
    """Old deployed roots must report unavailable, never borrow the PC ABI."""
    root = Path(root)
    if not (root / 'theme-api').exists():
        return {'availability': 'unavailable', 'apiFingerprint': None, 'runtimeModuleVerified': False}
    return ThemeApiContract(root).metadata()
