"""Bounded read-only SignalR probe using the installed normalization code."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, '/opt/smartpc/dashboard')
from PySide6.QtCore import QCoreApplication, QTimer
from motorsport_core import read_cache, bind_timing
from racing_timing import F1Timing
from dashboard_summary import build_summary

app = QCoreApplication([])
feed = F1Timing()
feed.ensure(True)

def finish():
    now = time.time()
    snapshot = read_cache(Path('/var/cache/smartpc-dashboard/SmartPC/SmartPC/f1-2026.json'), 'f1')
    timing = bind_timing(snapshot, feed.state.present(now, 2026))
    snapshot['live'] = timing
    envelope = {'status': 'active' if 0 <= now - snapshot['fetchedAt'] < 21600 else 'stale',
                'source': 'Jolpica', 'updatedAt': snapshot['fetchedAt'], 'data': snapshot}
    summary = build_summary('sport-f1', {'dashboardRacing': envelope}, {}, now)
    report = {'observedAt': now, 'scope': 'Real SignalR snapshot from board after install; REST identity from production cache; no GUI input',
              'timing': timing, 'summary': summary}
    assert timing['sessionId'] == 'f1:2026:17:Q', timing
    assert timing['status'] == 'Finished' and timing['rows'], timing
    assert summary['mode'] == 'timing' and summary['cards'][0]['value'] == 'Terminata', summary
    Path('/var/lib/smartpc-dashboard/v087-sport-live-proof/installed-real-timing.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'sessionId': timing['sessionId'], 'state': timing['status'], 'rows': len(timing['rows']),
                      'source': summary['subtitle'], 'firstCard': summary['cards'][0]}))
    feed.close()
    app.quit()

QTimer.singleShot(12000, finish)
app.exec()
