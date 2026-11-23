#!/usr/bin/env python3
"""Planning arithmetic only: not the Companion controller or board benchmark.

One-minute integration, seven days, automatic sleep 23:00-07:00.
Each visit completes one meal, one pet and one ball round instantly.
No XP, action eligibility, rendering, writes, notification or runtime simulation.
"""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


PROFILES = {
    "october_proposal": {"sat_awake": 10, "sat_sleep": 5, "meal": 35, "company_awake": 8, "energy_awake": 4, "round_energy": 8},
    "november_satiety_company_only": {"sat_awake": 6, "sat_sleep": 3, "meal": 45, "company_awake": 6, "energy_awake": 4, "round_energy": 8},
    "november_candidate": {"sat_awake": 6, "sat_sleep": 3, "meal": 45, "company_awake": 6, "energy_awake": 3, "round_energy": 6},
}
SCENARIOS = {
    "three_visits": (8, 14, 20),
    "two_visits": (8, 20),
    "four_visits": (8, 12, 16, 20),
    "three_skip_day3_afternoon": (8, 14, 20),
}
RESOURCES = ("satiety", "energy", "company")


def clamp(value):
    return min(100.0, max(0.0, value))


def simulate(profile, scenario):
    start = datetime(2026, 11, 23, 7, tzinfo=ZoneInfo("Europe/Rome"))
    state = dict(zip(RESOURCES, (70.0, 80.0, 70.0)))
    minima = state.copy()
    low_minutes = dict.fromkeys(RESOURCES, 0)
    zero_minutes = dict.fromkeys(RESOURCES, 0)
    visits = 0
    for minute in range(7 * 24 * 60):
        now = start + timedelta(minutes=minute)
        day = (now.date() - start.date()).days
        visit = now.minute == 0 and now.hour in SCENARIOS[scenario]
        if scenario == "three_skip_day3_afternoon" and day == 2 and now.hour == 14:
            visit = False
        if visit:
            visits += 1
            state["satiety"] = clamp(state["satiety"] + profile["meal"])
            state["company"] = clamp(state["company"] + 20)
            state["satiety"] = clamp(state["satiety"] - 1)
            state["energy"] = clamp(state["energy"] - profile["round_energy"])
            state["company"] = clamp(state["company"] + 15)
        awake = 7 <= now.hour < 23
        rates = {
            "satiety": -profile["sat_awake"] if awake else -profile["sat_sleep"],
            "energy": -profile["energy_awake"] if awake else 24,
            "company": -profile["company_awake"] if awake else 0,
        }
        for resource in RESOURCES:
            if awake and state[resource] < 30 - 1e-8:
                low_minutes[resource] += 1
            if state[resource] <= 1e-8:
                zero_minutes[resource] += 1
            state[resource] = clamp(state[resource] + rates[resource] / 60)
            minima[resource] = min(minima[resource], state[resource])
            assert 0 <= state[resource] <= 100
    return {
        "visits": visits,
        "minimum": {key: round(value, 2) for key, value in minima.items()},
        "final_at_day8_0700": {key: round(value, 2) for key, value in state.items()},
        "awake_hours_below_30": {key: round(value / 60, 2) for key, value in low_minutes.items()},
        "all_hours_at_zero": {key: round(value / 60, 2) for key, value in zero_minutes.items()},
    }


def offline_loss(before, loss):
    """The floor limits deterioration; it must never create free nourishment."""
    return min(before, max(15, before - loss))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert offline_loss(10, 80) == 10
    assert offline_loss(70, 80) == 15
    assert offline_loss(70, 0) == 70
    results = {
        name: {scenario: simulate(profile, scenario) for scenario in SCENARIOS}
        for name, profile in PROFILES.items()
    }
    # Independent daily balance, excluding clipping and round costs.
    balances = {
        name: {
            "satiety_decay_per_day": p["sat_awake"] * 16 + p["sat_sleep"] * 8,
            "maximum_three_meal_gain": 3 * p["meal"],
            "company_decay_per_day": p["company_awake"] * 16,
            "maximum_three_pet_and_ball_gain": 3 * (20 + 15),
        }
        for name, p in PROFILES.items()
    }
    report = {
        "kind": "offline_design_arithmetic_not_runtime_qualification",
        "step_seconds": 60,
        "days": 7,
        "profiles": PROFILES,
        "visit_hours": SCENARIOS,
        "daily_balance": balances,
        "results": results,
        "limits": [
            "Every planned action succeeds, including at low energy; this is a simplifying assumption.",
            "Visits have zero duration; no scheduling, motion, persistence or XP is modeled.",
            "This week has no DST transition; clock recovery needs separate tests.",
            "No empirical claim about enjoyment or actual user attention.",
        ],
        "offline_floor_examples": {"10_minus_80": offline_loss(10, 80), "70_minus_80": offline_loss(70, 80)},
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for profile_name, scenarios in results.items():
        for scenario, row in scenarios.items():
            print(profile_name, scenario, "min", row["minimum"], "awake h <30", row["awake_hours_below_30"])


if __name__ == "__main__":
    main()
