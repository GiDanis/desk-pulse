"""Real editorial HTTP + FotMob roster, then durable board verification data."""

import argparse
import json
from pathlib import Path
import time
from fantacalcio_core import Client, page_key, presentation, save_cache
from sport_core import (
    HTTPClient,
    refresh_snapshot,
    refresh_detail,
    save_cache as save_league,
)
from sport_team_core import refresh as refresh_team, save_cache as save_team

parser = argparse.ArgumentParser()
parser.add_argument("--directory", required=True)
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=True)
client = HTTPClient()
league = refresh_snapshot(client, None, time.time(), full=True)
match = next(m for m in league["fixtures"] if m["providerMatchId"] == "5749681")
league = refresh_detail(client, league, time.time(), match["canonicalMatchId"])
assert not league.get("detailError")
match = next(m for m in league["fixtures"] if m["providerMatchId"] == "5749681")
assert all(len(t["squad"]) == 23 for t in match["lineups"])
save_league(root / "sport.json", league)
team = refresh_team(client, "8636", "inter")
save_team(root / "sport-team-8636.json", team)
editorial = Client()
key = page_key(match)
page = editorial.get(key)
save_cache(root / ("fantacalcio-" + key.replace("/", "-") + ".json"), page)
data = presentation(page, match)
assert data["published"] and data["matched"] and not data["warning"]
josep = next(p for p in data["teams"][1]["players"] if p["name"] == "Josep Martínez")
assert josep["vote"] == 6.5 and josep["fantavote"] == 4.5
report = {
    "source": page["source"],
    "sourceUrl": page["url"],
    "fetchedAt": page["fetchedAt"],
    "matchId": "5749681",
    "match": "Roma - Inter",
    "season": match["season"],
    "round": match["round"],
    "sourceTeams": len(page["teams"]),
    "sourcePlayers": sum(len(t["players"]) for t in page["teams"]),
    "teams": [
        {
            "name": t["name"],
            "formation": t["formation"],
            "players": len(t["players"]),
            "starters": sum(p["group"] == "Titolari" for p in t["players"]),
            "substitutes": sum(p["group"] == "Subentrati" for p in t["players"]),
            "bench": sum(p["group"] == "Panchina" for p in t["players"]),
            "baseVotes": sum(p["vote"] is not None for p in t["players"]),
        }
        for t in data["teams"]
    ],
    "sample": {
        "player": josep["name"],
        "vote": josep["vote"],
        "fantavote": josep["fantavote"],
    },
    "requests": {"editorial": editorial.requests, "sport": client.request_count},
    "unmatchedNames": data["warning"],
}
(root / "fantacalcio-online.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
