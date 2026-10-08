"""Independent Casa adapter/cache/budget regressions. No Qt or live API calls."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from tuya_core import CloudClient, CloudConfig, TuyaError, atomic_json
from casa_core import (
    RequestBudget,
    acquire,
    empty_snapshot,
    load_snapshot,
    clean_snapshot,
    display_devices,
    policy,
    MANUAL_LIMIT,
)

CONFIG = CloudConfig(
    "https://openapi.tuyaeu.com", "public-client", "public-secret", "public-uid"
)


def raw_device(identity="lamp", value=False):
    return {
        "id": identity,
        "name": "Luce di prova",
        "category": "dj",
        "product_id": "product",
        "online": True,
        "status": [{"code": "switch_led", "value": value}],
        "local_key": "never-persist",
        "ip": "192.0.2.1",
        "uid": "never-persist",
    }


class FakeCloud:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [raw_device()]
        self.now = 1000000
        self.calls = []
        self.bad_page = 0
        self.fail_spec = False

    def __call__(self, url, headers, timeout):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.calls.append(parsed.path)
        if parsed.path == "/v1.0/token":
            result = {
                "access_token": "public-token",
                "refresh_token": "public-refresh",
                "expire_time": 7200,
            }
        elif parsed.path.endswith("/devices"):
            page = int(query["page_no"][0])
            size = int(query["page_size"][0])
            if page == self.bad_page:
                raise TuyaError("offline", "Synthetic offline")
            result = deepcopy(self.rows[(page - 1) * size : page * size])
        elif parsed.path.endswith("/specification"):
            if self.fail_spec:
                raise TuyaError("offline", "Synthetic offline")
            result = {
                "status": [{"code": "switch_led", "type": "Boolean", "values": "{}"}]
            }
        else:
            raise AssertionError("Unexpected endpoint")
        return {"success": True, "result": result}

    def client(self):
        return CloudClient(
            CONFIG, transport=self, clock=lambda: self.now, monotonic=lambda: 0
        )


class CasaChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self):
        fake = FakeCloud()
        client = fake.client()
        return fake, client, acquire(client, empty_snapshot(client.scope))

    def test_page_number_scan_full_page_requires_terminal_page(self):
        fake = FakeCloud([raw_device("one"), raw_device("two")])
        client = fake.client()
        self.assertEqual([r["id"] for r in client.smart_inventory(1)], ["one", "two"])
        self.assertEqual(
            client.request_count, 4
        )  # token, two full pages, empty terminator

    def test_duplicate_and_malformed_page_are_rejected(self):
        client = FakeCloud([raw_device(), raw_device()]).client()
        with self.assertRaises(TuyaError):
            client.smart_inventory(1)
        fake = FakeCloud()
        fake.rows[0]["status"].append({"code": "switch_led", "value": True})
        with self.assertRaises(TuyaError):
            fake.client().smart_inventory()

    def test_second_page_error_never_commits_partial_cache(self):
        fake = FakeCloud([raw_device(str(i)) for i in range(51)])
        fake.bad_page = 2
        client = fake.client()
        path = self.root / "cache.json"
        atomic_json(path, {"sentinel": True})
        before = path.read_bytes()
        with self.assertRaises(TuyaError):
            acquire(client, empty_snapshot(client.scope))
        self.assertEqual(path.read_bytes(), before)

    def test_unknown_schema_never_turns_value_into_false(self):
        fake = FakeCloud()
        fake.rows[0]["category"] = "other"
        client = fake.client()
        snap = acquire(client, empty_snapshot(client.scope))
        self.assertIsNone(snap["devices"][0]["states"][0]["value"])
        self.assertEqual(snap["devices"][0]["states"][0]["quality"], "unverified")

    def test_false_zero_scaling_and_bounds(self):
        fake, client, snap = self.snapshot()
        self.assertIs(snap["devices"][0]["states"][0]["value"], False)
        fake.rows[0]["category"] = "wsdcg"
        fake.rows[0]["status"] = [{"code": "va_temperature", "value": 0}]
        original = fake.__call__

        def transport(url, headers, timeout):
            if url.endswith("/specification"):
                return {
                    "success": True,
                    "result": {
                        "status": [
                            {
                                "code": "va_temperature",
                                "type": "Integer",
                                "values": {
                                    "scale": 1,
                                    "min": -200,
                                    "max": 600,
                                    "unit": "℃",
                                },
                            }
                        ]
                    },
                }
            return original(url, headers, timeout)

        client.transport = transport
        fake.now += 100
        result = acquire(client, snap)
        self.assertEqual(result["devices"][0]["states"][0]["value"], 0)
        fake.rows[0]["status"][0]["value"] = 900
        result = acquire(client, result)
        self.assertIsNone(result["devices"][0]["states"][0]["value"])

    def test_specs_reused_and_new_unknown_code_is_not_fetched_forever(self):
        fake, client, snap = self.snapshot()
        before = client.request_count
        fake.now += 60
        snap = acquire(client, snap)
        self.assertEqual(client.request_count - before, 1)
        fake.rows[0]["status"].append({"code": "not_in_spec", "value": 10})
        fake.now += 60
        before = client.request_count
        snap = acquire(client, snap)
        self.assertEqual(client.request_count - before, 2)
        fake.now += 60
        before = client.request_count
        acquire(client, snap)
        self.assertEqual(client.request_count - before, 1)

    def test_missing_metric_retains_old_stamp_and_old_quality(self):
        fake, client, snap = self.snapshot()
        stamp = snap["devices"][0]["states"][0]["checkedAt"]
        fake.rows[0]["status"] = []
        fake.now += 60
        snap = acquire(client, snap)
        metric = snap["devices"][0]["states"][0]
        self.assertEqual(metric["checkedAt"], stamp)
        self.assertTrue(metric["stale"])

    def test_two_missing_scans_keep_favourite_tombstone(self):
        fake, client, snap = self.snapshot()
        fake.rows = []
        fake.now += 60
        snap = acquire(client, snap)
        self.assertEqual(snap["devices"][0]["missingCount"], 1)
        fake.now += 60
        snap = acquire(client, snap)
        self.assertEqual(snap["devices"][0]["missingCount"], 2)
        self.assertEqual(
            display_devices(snap, "active")[0]["availability"], "Non più disponibile"
        )
        path = self.root / "cache.json"
        atomic_json(path, snap)
        self.assertFalse(load_snapshot(path, client.scope)["devices"][0]["present"])

    def test_removed_non_favourite_clears_and_empty_stays_empty_after_restart(self):
        fake, client, snap = self.snapshot()
        snap["favourites"] = []
        fake.rows = []
        snap = acquire(client, acquire(client, snap))
        self.assertEqual(snap["devices"], [])
        path = self.root / "cache.json"
        atomic_json(path, snap)
        self.assertEqual(load_snapshot(path, client.scope)["devices"], [])

    def test_rename_and_product_change_use_identity(self):
        fake, client, snap = self.snapshot()
        fake.rows[0]["name"] = "Nuovo nome"
        fake.now += 60
        updated = acquire(client, snap)
        self.assertEqual(updated["favourites"], snap["favourites"])
        self.assertEqual(updated["devices"][0]["name"], "Nuovo nome")
        fake.rows[0]["product_id"] = "new-product"
        before = client.request_count
        updated = acquire(client, updated)
        self.assertEqual(client.request_count - before, 2)
        self.assertEqual(updated["specifications"]["lamp"]["productId"], "new-product")

    def test_offline_and_cached_online_are_never_current(self):
        _, _, snap = self.snapshot()
        snap["devices"][0]["online"] = False
        d = display_devices(snap, "active")[0]
        self.assertEqual(d["primaryText"], "Spento")
        self.assertTrue(d["previous"])
        snap["devices"][0]["online"] = True
        for status in ("stale", "offline", "error", "updating"):
            d = display_devices(snap, status)[0]
            self.assertTrue(d["availabilityPrevious"])
            self.assertTrue(d["metrics"][0]["previous"])

    def test_persistence_allowlist_and_account_isolation(self):
        _, client, snap = self.snapshot()
        path = self.root / "cache.json"
        atomic_json(path, snap)
        self.assertNotIn("never-persist", path.read_text())
        self.assertNotIn("local_key", path.read_text())
        self.assertNotIn("192.0.2.1", path.read_text())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(load_snapshot(path, "different-scope")["devices"], [])
        raw = deepcopy(snap)
        raw["devices"][0]["local_key"] = "never-persist"
        self.assertNotIn("local_key", clean_snapshot(raw, client.scope)["devices"][0])

    def test_independent_concurrent_writers_never_lose_counted_requests(self):
        from concurrent.futures import ThreadPoolExecutor

        path = self.root / "budget.json"
        first = RequestBudget(path, "scope", clock=lambda: 1000000)
        second = RequestBudget(path, "scope", clock=lambda: 1000000)

        def charge_ten(budget):
            for _ in range(10):
                budget.charge()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(charge_ten, (first, second)))
        restarted = RequestBudget(path, "scope", clock=lambda: 1000000)
        self.assertEqual(restarted.data["requests"], 20)
        self.assertEqual(path.with_suffix(".lock").stat().st_mode & 0o777, 0o600)

    def test_manual_budget_survives_restart_and_has_no_auto_polling(self):
        now = [1000000]
        path = self.root / "budget.json"
        budget = RequestBudget(path, "scope", clock=lambda: now[0])
        for _ in range(MANUAL_LIMIT):
            budget.charge()
        budget = RequestBudget(path, "scope", clock=lambda: now[0])
        self.assertFalse(budget.automatic_available())
        with self.assertRaises(TuyaError):
            budget.charge()
        self.assertEqual(budget.remaining(), 0)

    def test_budget_charged_before_failed_network_and_no_grant_on_clock_rollback(self):
        now = [1000000]
        budget = RequestBudget(self.root / "budget", "scope", clock=lambda: now[0])
        budget.charge()
        restarted = RequestBudget(self.root / "budget", "scope", clock=lambda: now[0])
        self.assertEqual(restarted.data["requests"], 1)
        now[0] -= 60
        with self.assertRaises(TuyaError):
            restarted.charge()
        self.assertEqual(restarted.data["requests"], 1)

    def test_corrupt_or_unwritable_counter_stops_requests(self):
        path = self.root / "budget"
        path.write_text("{}")
        budget = RequestBudget(path, "scope", clock=lambda: 1000000)
        with self.assertRaises(TuyaError):
            budget.charge()
        path.unlink()
        budget = RequestBudget(path, "scope", clock=lambda: 1000000)
        with patch("casa_core.atomic_json", side_effect=OSError("readonly")):
            with self.assertRaises(TuyaError):
                budget.charge()
        self.assertFalse(budget.valid)

    def test_effective_budget_reserve_period_and_expiry(self):
        now = [1000000]
        p = {
            "periodStart": 999000,
            "periodEnd": 1100000,
            "apiAllowance": 100,
            "consumedBeforeStart": 75,
            "serviceExpiresAt": 1100000,
        }
        budget = RequestBudget(self.root / "budget", "scope", p, lambda: now[0])
        self.assertTrue(budget.automatic_available())
        for _ in range(5):
            budget.charge()
        with self.assertRaises(TuyaError):
            budget.charge()
        now[0] = 1100001
        p["periodStart"] = 1100000
        p["periodEnd"] = 1200000
        p["serviceExpiresAt"] = 1200000
        p["consumedBeforeStart"] = 0
        budget = RequestBudget(self.root / "budget", "scope", p, lambda: now[0])
        budget.charge()
        self.assertEqual(budget.data["requests"], 1)
        now[0] = 1200000
        with self.assertRaises(TuyaError):
            budget.charge()

    def test_daily_boost_limit_persisted_and_reads_are_side_effect_free(self):
        now = [1000000]
        p = {
            "periodStart": 999000,
            "periodEnd": 1100000,
            "apiAllowance": 26000,
            "consumedBeforeStart": 0,
            "serviceExpiresAt": 1100000,
        }
        path = self.root / "budget"
        budget = RequestBudget(path, "scope", p, lambda: now[0])
        before = deepcopy(budget.data)
        budget.automatic_available()
        self.assertEqual(before, budget.data)
        self.assertTrue(budget.boost(60, 1))
        budget = RequestBudget(path, "scope", p, lambda: now[0])
        self.assertEqual(budget.data["boostSeconds"], 60)
        self.assertFalse(budget.boost(7140, 1))
        self.assertFalse(budget.can_boost(1))

    def test_policy_never_assumes_nominal_free_quota(self):
        self.assertEqual(policy(self.root / "absent"), {})
        path = self.root / "policy"
        atomic_json(path, {"apiAllowance": 26000})
        self.assertEqual(policy(path), {})

    def test_malformed_nested_cache_is_discarded(self):
        _, client, snapshot = self.snapshot()
        path = self.root / "cache.json"
        for field, value in (
            ("device", None),
            ("favourites", [{}]),
            ("observedCodes", 42),
            ("observedCodes", "switch_led"),
        ):
            with self.subTest(field=field, value=value):
                raw = deepcopy(snapshot)
                if field == "device":
                    raw["devices"][0] = value
                elif field == "favourites":
                    raw["favourites"] = value
                else:
                    raw["specifications"]["lamp"][field] = value
                atomic_json(path, raw)
                self.assertEqual(
                    load_snapshot(path, client.scope), empty_snapshot(client.scope)
                )

    def test_previous_secondary_metric_is_visible_in_summary(self):
        _, _, snapshot = self.snapshot()
        device = snapshot["devices"][0]
        device["states"] = [
            {
                "code": "va_temperature",
                "value": 25,
                "unit": "°C",
                "quality": "reported",
                "checkedAt": 1000000,
                "stale": False,
            },
            {
                "code": "va_humidity",
                "value": 55,
                "unit": "%",
                "quality": "reported",
                "checkedAt": 999000,
                "stale": True,
            },
        ]
        summary = display_devices(snapshot, "active")[0]
        self.assertTrue(summary["previous"])
        self.assertFalse(summary["metrics"][0]["previous"])
        self.assertTrue(summary["metrics"][1]["previous"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
