"""Explicit, bounded read-only verification of the production Casa provider.

Run manually; never schedule this probe. Output contains normalized values only.
"""
import argparse
import json
from pathlib import Path
import time

from PySide6.QtCore import QCoreApplication,QThreadPool
from casa import CasaService


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--output',type=Path);args=parser.parse_args()
    if not args.live:parser.error('This probe requires explicit --live; it makes counted cloud GET requests.')
    app=QCoreApplication([]);provider=CasaService(auto_refresh=False);before=provider.budget.data['requests'] if provider.budget else 0
    started=time.monotonic()
    try:
        assert provider.refresh(),'Casa refresh was not accepted; check private configuration and budget.'
        deadline=started+60
        while provider._busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
        assert not provider._busy,'Casa worker did not finish within the verification deadline.'
        state=provider.moduleState
        devices=state['data']['devices']
        report={'status':'passed' if state['status']=='active' else 'failed',
            'providerStatus':state['status'],'elapsedSeconds':round(time.monotonic()-started,3),
            'httpRequestsCharged':provider.budget.data['requests']-before,'requestsTotal':provider.budget.data['requests'],
            'devices':len(devices),'online':sum(d['online'] is True for d in devices),'offline':sum(d['online'] is False for d in devices),
            'polling':state['data']['polling'],'quotaConfigured':state['data']['quotaConfigured'],
            'checkedAt':state['updatedAt'],'cachePermissions':oct(provider._cache.stat().st_mode&0o777),
            'favourites':[{'name':d['name'],'availability':d['availability'],'previous':d['previous'],
                'metrics':[{'code':m['code'],'value':m['value'],'unit':m['unit'],'quality':m['quality'],'previous':m['previous']} for m in d['metrics']]} for d in state['data']['favourites']],
            'error':state['error'],'scope':'Actual cloud reads from this host; no commands or physical state changes.'}
        if args.output:args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(report,ensure_ascii=False));return 0 if report['status']=='passed' else 1
    finally:
        provider.close();QThreadPool.globalInstance().waitForDone(8000)


if __name__=='__main__':raise SystemExit(main())
