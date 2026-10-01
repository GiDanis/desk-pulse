"""Offline regression checks: protocol vectors, account isolation and recovery.

No real account, network access or credentials. Public signature vectors are
from https://developer.tuya.com/en/docs/iot/new-singnature?id=Kbw0q34cs2e5g.
"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from tuya_core import (CloudClient, CloudConfig, TuyaError, atomic_json, http_get,
                       load_config, normalize_status, read_inventory, signature,
                       synchronize)
from tuya_probe import main


CONFIG = CloudConfig('https://openapi.tuyaeu.com', 'example_client', 'example_secret', 'example_uid')


def ok(value):
    return {'success': True, 'result': value}


def token(access='example_token'):
    return ok({'access_token': access, 'refresh_token': 'example_refresh', 'expire_time': 7200})


def device(identifier='lamp', name='Luce', **extra):
    return {'id': identifier, 'name': name, 'category': 'dj', 'online': True,
            'model': 'model_a', 'product_id': 'product_a', **extra}


def page(devices, more=False, cursor='', total=None):
    result = {'list': devices, 'has_more': more, 'last_row_key': cursor}
    if total is not None:
        result['total'] = total
    return ok(result)


class ScriptedTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        if not self.responses:
            raise AssertionError('Unexpected extra request')
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def client(*responses, config=CONFIG, monotonic=lambda: 100):
    transport = ScriptedTransport(*responses)
    return CloudClient(config, transport=transport, clock=lambda: 1790840000, monotonic=monotonic), transport


class TuyaChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cache = Path(self.directory.name) / 'inventory.json'

    def test_official_token_signature_vector(self):
        self.assertEqual(self.public_signature('/v1.0/token?grant_type=1'),
                         '9E48A3E93B302EEECC803C7241985D0A34EB944F40FB573C7B5C2A82158AF13E')

    def test_official_business_signature_vector(self):
        self.assertEqual(self.public_signature('/v2.0/apps/schema/users?page_no=1&page_size=50',
                                               token='3f4eda2bdec17232f67c0b188af3eec1'),
                         'AE4481C692AA80B25F3A7E12C3A5FD9BBF6251539DD78E565A1A72A508A88784')

    @staticmethod
    def public_signature(path, **kwargs):
        return signature('1KAD46OrT9HafiKdsXeg', '4OHBOnWOqaEC1mWXOpVL3yV50s0qGSRC', path,
                         '1588925778000', nonce='5138cc3a9033d69856923fd07b491173',
                         signed_headers='area_id:29a33e8796834b1efa6\ncall_id:8afdb70ab2ed11eb85290242ac130003\n',
                         **kwargs)

    def test_full_pagination_account_scope_and_safe_cache(self):
        api, transport = client(token(), page([device(local_key='private', ip='192.168.1.1')], True, 'next +/'),
                                page([device('sensor', 'Sensore', gateway_id='hub', sub=True)], total=2))
        snapshot, changes = synchronize(api, self.cache)
        self.assertEqual(changes['added'], ['lamp', 'sensor'])
        self.assertTrue(snapshot['devices'][1]['subDevice'])
        for url, headers, timeout in transport.calls[1:]:
            parsed = urlsplit(url)
            self.assertEqual(parse_qs(parsed.query)['source_id'], [CONFIG.uid])
            self.assertEqual(parse_qs(parsed.query)['source_type'], ['tuyaUser'])
            self.assertEqual(headers['sign'], signature(CONFIG.access_id, CONFIG.access_secret,
                             parsed.path + '?' + parsed.query, headers['t'], token=headers['access_token']))
            self.assertEqual(timeout, 12)
        self.assertEqual(parse_qs(urlsplit(transport.calls[2][0]).query)['last_row_key'], ['next +/'])
        persisted = self.cache.read_text()
        for secret in ('private', '192.168.1.1', CONFIG.access_id, CONFIG.uid, CONFIG.access_secret, 'example_token'):
            self.assertNotIn(secret, persisted)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)
        self.assertEqual(read_inventory(self.cache, api.scope), snapshot)

    def test_second_page_failure_preserves_last_complete_inventory(self):
        api, _ = client(token(), page([device()], total=1), page([], True, 'next'),
                        TuyaError('offline', 'Cloud non raggiungibile'))
        synchronize(api, self.cache)
        before = self.cache.read_bytes()
        with self.assertRaises(TuyaError):
            synchronize(api, self.cache)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_valid_empty_inventory_clears_devices_after_reboot(self):
        api, _ = client(token(), page([device()]), page([], total=0))
        synchronize(api, self.cache)
        snapshot, changes = synchronize(api, self.cache)
        self.assertEqual(changes['removed'], ['lamp'])
        self.assertEqual(read_inventory(self.cache, api.scope)['devices'], [])
        self.assertEqual(snapshot['devices'], [])

    def test_rename_add_remove_preserve_identity(self):
        api, _ = client(token(), page([device(), device('old', 'Vecchio')]),
                        page([device(name='Nuovo nome'), device('new', 'Nuovo')]))
        synchronize(api, self.cache)
        _, changes = synchronize(api, self.cache)
        self.assertEqual(changes, {'added': ['new'], 'removed': ['old'], 'renamed': ['lamp'], 'replaced': []})

    def test_different_account_cannot_reuse_previous_cache(self):
        first, _ = client(token(), page([device()]))
        synchronize(first, self.cache)
        other = CloudConfig(CONFIG.endpoint, CONFIG.access_id, CONFIG.access_secret, 'another_uid')
        second, _ = client(token(), page([], total=0), config=other)
        self.assertIsNone(read_inventory(self.cache, second.scope))
        _, changes = synchronize(second, self.cache)
        self.assertEqual(changes['removed'], [])

    def test_broken_pagination_duplicate_and_total_mismatch_rejected(self):
        cases = [
            [page([device(), device()])],
            [page([device()], total=2)],
            [page([], True, 'again'), page([], True, 'again')],
            [ok({'list': [], 'has_more': 'false'})],
        ]
        for responses in cases:
            with self.subTest(responses=responses):
                api, _ = client(token(), *responses)
                with self.assertRaises(TuyaError):
                    synchronize(api, self.cache)
                self.assertFalse(self.cache.exists())

    def test_invalid_token_reauthenticates_and_replays_once(self):
        api, transport = client(token(), {'success': False, 'code': 1010}, token('new_token'), page([]))
        self.assertEqual(api.inventory(), [])
        self.assertEqual(len(transport.calls), 4)
        self.assertNotIn('access_token', transport.calls[2][1])
        self.assertEqual(transport.calls[3][1]['access_token'], 'new_token')

    def test_repeated_token_error_has_bounded_requests(self):
        error = {'success': False, 'code': 1010}
        api, transport = client(token(), error, token(), error)
        with self.assertRaises(TuyaError):
            api.inventory()
        self.assertEqual(len(transport.calls), 4)

    def test_expired_token_uses_refresh_without_business_token(self):
        now = [0]
        api, transport = client(token(), page([]), token('renewed_token'), page([]), monotonic=lambda: now[0])
        api.inventory()
        now[0] = 7200
        api.inventory()
        self.assertTrue(transport.calls[2][0].endswith('/v1.0/token/example_refresh'))
        self.assertNotIn('access_token', transport.calls[2][1])
        self.assertEqual(transport.calls[3][1]['access_token'], 'renewed_token')

    def test_provider_error_never_echoes_message_or_credentials(self):
        api, _ = client(token(), {'success': False, 'code': 1106, 'msg': CONFIG.access_secret})
        with self.assertRaises(TuyaError) as caught:
            api.inventory()
        self.assertEqual(caught.exception.code, '1106')
        self.assertNotIn(CONFIG.access_secret, str(caught.exception))
        self.assertNotIn(CONFIG.access_secret, repr(CONFIG))

    def test_http_quota_and_redirect_do_not_expose_response_or_retry(self):
        for code, kind in ((429, 'quota'), (302, 'http')):
            with self.subTest(code=code):
                opener = unittest.mock.Mock()
                opener.open.side_effect = HTTPError('https://example.invalid/private', code,
                                                    CONFIG.access_secret, {}, io.BytesIO(b'secret'))
                with patch('tuya_core.build_opener', return_value=opener) as factory:
                    with self.assertRaises(TuyaError) as caught:
                        http_get(CONFIG.endpoint, {}, 12)
                self.assertEqual(caught.exception.kind, kind)
                self.assertNotIn(CONFIG.access_secret, str(caught.exception))
                self.assertIsNone(factory.call_args.args[0].redirect_request(None, None, 302, '', {}, 'https://other'))
                self.assertEqual(opener.open.call_count, 1)

    def test_sensor_scaling_false_and_zero_require_specification(self):
        specs = {'status': [{'code': 'temp', 'type': 'Integer', 'values': '{"scale":1,"unit":"°C"}'},
                            {'code': 'switch', 'type': 'Boolean'},
                            {'code': 'zero', 'type': 'Integer', 'values': '{"scale":0}'}]}
        status = [{'code': 'temp', 'value': 234}, {'code': 'switch', 'value': False},
                  {'code': 'zero', 'value': 0}, {'code': 'unknown', 'value': 0}]
        rows = normalize_status(status, specs)
        self.assertEqual((rows[0]['value'], rows[0]['unit']), (23.4, '°C'))
        self.assertIs(rows[1]['value'], False)
        self.assertEqual(rows[2]['value'], 0)
        self.assertIsNone(rows[3]['value'])
        self.assertEqual(rows[3]['quality'], 'unverified')

    def test_missing_malformed_or_unsupported_values_stay_unverified(self):
        cases = [('Boolean', {}, 0), ('Integer', {}, 234), ('Integer', {'scale': 1}, 10**1000),
                 ('Enum', {'range': ['on']}, 'off'), ('Raw', {}, 'private'), ('Integer', {'scale': 1}, None)]
        for kind, values, raw in cases:
            with self.subTest(kind=kind, raw_type=type(raw).__name__):
                rows = normalize_status([{'code': 'state', 'value': raw}],
                                        {'status': [{'code': 'state', 'type': kind, 'values': values}]})
                self.assertIsNone(rows[0]['value'])

    def test_duplicate_status_or_specifications_rejected(self):
        spec = {'code': 'switch', 'type': 'Boolean'}
        for states, specs in (([{'code': 'switch'}]*2, [spec]), ([], [spec, spec])):
            with self.assertRaises(TuyaError):
                normalize_status(states, {'status': specs})

    def test_config_is_private_regular_file_and_not_symlink(self):
        path = self.cache.parent / 'config.json'
        atomic_json(path, {'endpoint': CONFIG.endpoint, 'access_id': CONFIG.access_id,
                          'access_secret': CONFIG.access_secret, 'uid': CONFIG.uid})
        self.assertEqual(load_config(path), CONFIG)
        path.chmod(0o644)
        with self.assertRaises(TuyaError):
            load_config(path)
        path.chmod(0o600)
        link = self.cache.parent / 'link.json'
        link.symlink_to(path)
        with self.assertRaises(TuyaError):
            load_config(link)

    def test_cache_rebuild_discards_external_secret_fields(self):
        api, _ = client(token(), page([device()]))
        snapshot, _ = synchronize(api, self.cache)
        snapshot['devices'][0]['local_key'] = 'private'
        atomic_json(self.cache, snapshot)
        self.assertNotIn('private', json.dumps(read_inventory(self.cache, api.scope)))

    def test_atomic_write_failure_keeps_previous_inventory(self):
        atomic_json(self.cache, {'old': True})
        before = self.cache.read_bytes()
        with patch('tuya_core.os.replace', side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):
                atomic_json(self.cache, {'new': True})
        self.assertEqual(self.cache.read_bytes(), before)
        self.assertEqual(list(self.cache.parent.iterdir()), [self.cache])

    def test_cli_creates_blank_config_without_overwriting_and_checks_offline(self):
        path = self.cache.parent / 'config.json'
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--config', str(path), '--init-config']), 0)
            before = path.read_bytes()
            self.assertEqual(main(['--config', str(path), '--init-config']), 2)
            self.assertEqual(main(['--config', str(path), '--check-config']), 2)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main(verbosity=2)
