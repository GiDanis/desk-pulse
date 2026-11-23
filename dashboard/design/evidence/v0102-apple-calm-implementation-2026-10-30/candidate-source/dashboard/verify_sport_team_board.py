"""Fetch a real club/calendar and future cup/friendly/finished details for board QA."""

import argparse
import json
from pathlib import Path
import time
from sport_core import HTTPClient, refresh_snapshot, save_cache as save_league
from sport_team_core import refresh, present, save_cache

parser = argparse.ArgumentParser()
parser.add_argument("--directory", required=True)
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=True)
client = HTTPClient()
league = refresh_snapshot(client, None, time.time(), full=True)
assert league["provider"] == "fotmob"
save_league(root / "sport.json", league)
profile = refresh(client, "8636", "inter")
view = present(profile, time.time(), "inter")
selected = [
    view["upcoming"][0],
    next(m for m in view["upcoming"] if m["providerLeagueId"] == 42),
    view["results"][0],
]
details = []
for match in selected:
    profile = refresh(client, "8636", "inter", profile, match["canonicalMatchId"], True)
    assert not profile["detailError"], profile["detailError"]
    detail = next(
        m
        for m in profile["fixtures"]
        if m["canonicalMatchId"] == match["canonicalMatchId"]
    )
    details.append(
        {
            "id": detail["providerMatchId"],
            "competition": detail["competitionName"],
            "status": detail["status"],
            "venue": detail["venue"],
            "stats": len(detail["stats"]),
            "lineups": len(detail["lineups"]),
        }
    )
save_cache(root / "sport-team-8636.json", profile)
responses = {
    url: [entry[1], entry[2]]
    for url, entry in client.cache.items()
    if "matchDetails?" in url
}
(root / "team-responses.json").write_text(json.dumps(responses))
report = {
    "fetchedAt": profile["fetchedAt"],
    "leagueFixtures": len(league["fixtures"]),
    "teamFixtures": len(profile["fixtures"]),
    "futureFixtures": len(view["upcoming"]),
    "competitions": sorted({m["competitionName"] for m in profile["fixtures"]}),
    "squad": len(profile["squad"]),
    "coach": profile["coach"],
    "stadium": profile["stadium"],
    "requests": client.request_count,
    "details": details,
}
(root / "team-online.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
