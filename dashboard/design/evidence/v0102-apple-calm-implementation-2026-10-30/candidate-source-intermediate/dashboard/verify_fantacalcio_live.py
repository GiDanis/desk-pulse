"""Bounded real HTTP verification; unavailable live is reported, not a success."""

import argparse
import json
from pathlib import Path
import time
from fantacalcio_core import Client, save_cache
from fantacalcio_live import LiveClient, check_descriptor, DESCRIPTOR
from sport_core import ProviderError

parser = argparse.ArgumentParser()
parser.add_argument("--directory", required=True)
parser.add_argument("--key", required=True)
args = parser.parse_args()
directory = Path(args.directory)
directory.mkdir(parents=True, exist_ok=True)
client = LiveClient(directory)
season_id = client.season_id(args.key)
requests_after_discovery = client.requests
restarted = LiveClient(directory)
assert restarted.season_id(args.key) == season_id and restarted.requests == 0
check_descriptor(client._request(DESCRIPTOR)[0].decode())
report = dict(
    key=args.key,
    seasonId=season_id,
    seasonPersisted=True,
    discoveryRequests=requests_after_discovery,
    restartDiscoveryRequests=0,
    descriptorVerified=True,
    checkedAt=time.time(),
    credentialsUsed=False,
)
try:
    page = client.get(args.key)
    report.update(liveResource="available", liveTeams=len(page["teams"]))
except ProviderError as error:
    report.update(liveResource="unavailable", liveHttpStatus=error.http_status)
client_history = Client()
historical = client_history.get("2023-24/4", 0)
team = next(t for t in historical["teams"] if t["teamId"] == "fiorentina")
expected = {
    "Terracciano": (5.5, 3.5),
    "Duncan": (6.5, 7.5),
    "Bonaventura": (7, 10),
    "Barak": (None, None),
}
for name, votes in expected.items():
    player = next(p for p in team["players"] if p["name"] == name)
    assert (player["vote"], player["fantavote"]) == votes
save_cache(directory / "fantacalcio-2023-24-4.json", historical)
report.update(
    historicalKey="2023-24/4",
    historicalTeams=len(historical["teams"]),
    historicalPlayers=sum(len(t["players"]) for t in historical["teams"]),
    historicalSample={name: list(v) for name, v in expected.items()},
    liveClientRequests=client.requests,
    historicalRequests=client_history.requests,
)
(directory / "fantacalcio-live-http.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report))
