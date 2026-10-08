"""Post-run statistics only. Preserve denominators and non-measurable outcomes."""
from collections import Counter
import math


def percentile(values, fraction):
    return round(sorted(values)[int((len(values)-1)*fraction)], 3) if values else None


def summary(values):
    return {'count': len(values), 'median': percentile(values, .5),
            'p95': percentile(values, .95), 'max': max(values, default=None), 'samples': values}


def missing_settlement_details(raw, requests, expected, settled_ids):
    """Explain missing observations without inventing terminal pixels or latency.

    A coherent transaction may be preempted by the next request before an
    immutable frame proves settlement. GUI stop events alone are not a submitted
    frame, and their recorded callback time is not an optical timestamp.
    """
    events = raw.get('events', [])
    all_requests = raw.get('requests', [])
    details = []
    for identity, request in requests.items():
        if identity not in expected or identity in settled_ids:
            continue
        frames = [frame for frame in raw.get('frameSummaries', []) if frame.get('requestId') == identity]
        first = next((frame for frame in frames if frame.get('firstCoherent')), None)
        revision = request.get('terminalMetadata', {}).get('revision', first.get('revision') if first else None)
        recorded_frames = [event for event in events if event.get('requestId') == identity and event.get('event') == 'frame.submission']
        stops = [event for event in events if event.get('requestId') == identity and event.get('event') == 'motion.stopped']
        following_requests = [row for row in all_requests if row.get('operation') == request.get('operation')
                              and row.get('startedNs', -1) > request['startedNs']]
        following_publications = [event for event in events if event.get('event') == 'appearance.published'
                                  and type(revision) is int and event.get('metadata', {}).get('revision', -1) > revision]
        next_request = min(following_requests, key=lambda row: row['startedNs'], default=None)
        next_publication = min(following_publications, key=lambda row: row['timestampNs'], default=None)
        last = recorded_frames[-1] if recorded_frames else None
        details.append({
            'requestId': identity, 'revision': revision, 'outcome': request['outcome'],
            'firstCoherentSubmissionMs': (first['submittedSessionNs'] - request['startedNs']) / 1e6 if first else None,
            'recordedSubmissionCount': len(recorded_frames),
            'lastRecordedSubmission': ({'recordedSessionNs': last.get('timestampNs'),
                **{key: last.get('metadata', {}).get(key) for key in ('frameSerial', 'revision', 'outcome',
                    'motionSettled', 'motionSettlementEvidence', 'synchronizedNs', 'submittedNs')}} if last else None),
            'guiStopObservations': [{'recordedSessionNs': event.get('timestampNs'),
                **{key: event.get('metadata', {}).get(key) for key in ('instanceId', 'motionEvent', 'revision')}} for event in stops],
            'nextRequest': ({'requestId': next_request['requestId'], 'startedSessionNs': next_request['startedNs']}
                            if next_request else None),
            'nextPublication': ({'revision': next_publication['metadata']['revision'],
                                 'recordedSessionNs': next_publication['timestampNs']} if next_publication else None),
            'observation': 'nextRevisionPublishedWithoutObservedSettledFrame' if next_publication else 'noObservedSettledFrame',
            'interpretation': 'Missing immutable settled-frame proof; GUI stop or subsequent publication cannot supply a settlement latency.'
        })
    return details


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
    if expected != first_ids or len(coherent)!=len(expected): invalid.append('missingOrDuplicateFirstCoherentSummary')
    if expected != settled_ids or len(settled)!=len(expected): invalid.append('missingOrDuplicateMotionSettledSummary')
    unexpected = {key: count for key, count in outcomes.items() if key not in ('coherentSubmission','noVisualChange')}
    if unexpected: invalid.append('unexpectedRequestOutcomes')
    if any(not math.isfinite(v) or v < 0 for v in coherent + settled): invalid.append('invalidLatency')
    return {'complete': not invalid, 'incompleteReasons': invalid,
            'operationFilter': operation, 'requestedCount': len(requests), 'outcomes': dict(outcomes),
            'noVisualChangePolicy': 'counted in denominator; no invented zero latency or required frame',
            'requestToCoherentSubmissionMs': summary(coherent),
            'requestToMotionSettledFrameMs': summary(settled),
            'settledFramesMissing': len(expected-settled_ids),
            'missingSettledFrames': missing_settlement_details(raw, requests, expected, settled_ids),
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
