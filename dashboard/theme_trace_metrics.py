"""Post-run statistics only. Preserve denominators and non-measurable outcomes."""
from collections import Counter
import math


def percentile(values, fraction):
    return round(sorted(values)[int((len(values)-1)*fraction)], 3) if values else None


def summary(values):
    return {'count': len(values), 'median': percentile(values, .5),
            'p95': percentile(values, .95), 'max': max(values, default=None), 'samples': values}


def build_trace_metrics(raw, operation='selectDraft'):
    requests = {row['requestId']: row for row in raw['requests'] if row['operation'] == operation}
    outcomes = Counter(row['outcome'] or 'unfinished' for row in requests.values())
    coherent, settled, lag, mandatory = [], [], [], []
    first_ids, settled_ids = set(), set()
    for frame in raw.get('frameSummaries', []):
        request = requests.get(frame['requestId'])
        if request is None or request['outcome'] != 'coherentSubmission':
            continue
        ms = (frame['submittedSessionNs'] - request['startedNs']) / 1e6
        if frame.get('firstCoherent'):
            coherent.append(ms); first_ids.add(frame['requestId'])
            hosts = {p['instanceId'] for p in frame.get('participants', [])
                     if p.get('mandatory') and p.get('surfaceId') not in ('shell.main', 'scene.main')}
            commits = {}
            for event in raw['events']:
                if event['requestId'] != frame['requestId'] or event['event'] not in ('host.reuse','host.commit.end'):
                    continue
                fields = event['metadata']
                if fields.get('revision') == frame['revision']:
                    commits[fields.get('instanceId')] = event['timestampNs']
            if hosts and hosts <= commits.keys():
                mandatory.append((max(commits[h] for h in hosts)-request['startedNs'])/1e6)
        if frame.get('firstSettled'):
            settled.append(ms); settled_ids.add(frame['requestId'])
        lag.append(frame['queuedDeliveryLagNs']/1e6)
    costs = [raw['recordingCostNsByRequest'][identity]/1e6 for identity in requests]
    expected = {identity for identity, row in requests.items() if row['outcome'] == 'coherentSubmission'}
    invalid = list(raw.get('incompleteReasons', []))
    if expected != first_ids: invalid.append('missingOrDuplicateFirstCoherentSummary')
    unexpected = {key: count for key, count in outcomes.items() if key not in ('coherentSubmission','noVisualChange')}
    if unexpected: invalid.append('unexpectedRequestOutcomes')
    if any(not math.isfinite(v) or v < 0 for v in coherent + settled): invalid.append('invalidLatency')
    return {'complete': not invalid, 'incompleteReasons': invalid,
            'operationFilter': operation, 'requestedCount': len(requests), 'outcomes': dict(outcomes),
            'noVisualChangePolicy': 'counted in denominator; no invented zero latency or required frame',
            'requestToCoherentSubmissionMs': summary(coherent),
            'requestToMotionSettledFrameMs': summary(settled),
            'settledFramesMissing': len(expected-settled_ids),
            'mandatoryHostsCommittedMs': summary(mandatory),
            'mandatoryCommitScope': 'Recorded host commit/reuse; inline shell and scene readiness separately observed in immutable frame ticket',
            'queuedDeliveryLagMs': summary(lag), 'recordingCostMs': summary(costs),
            'recordingCostScope': raw.get('recordingCostMethod'),
            'eventIdRevisionRankToSubmissionMs': dict(summary([r['durationMs'] for r in raw.get('notificationFrames', [])]),
                inputsCount=raw.get('notificationInputsCount', 0),
                scope='Normalized QML event identity observed to immutable submission; source-publication legacy latency remains separate',
                identities=raw.get('notificationFrames', [])),
            'requestToPersistedMs': summary([(r['endedNs']-r['startedNs'])/1e6 for r in raw['requests']
                if r['operation']=='apply' and r.get('terminalMetadata',{}).get('persisted') is True]),
            'nativeSignalTimestampVerified': False, 'gilDelayQuantified': False}
