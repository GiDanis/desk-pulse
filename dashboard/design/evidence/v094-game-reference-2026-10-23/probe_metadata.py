"""Finite QtCore-only metadata diagnostic, never a production data directory."""
from pathlib import Path
import argparse,json,time
from PySide6.QtCore import QCoreApplication
from game import GameService


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert str(a.root.resolve()).startswith('/var/tmp/')
    app=QCoreApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('Dashboard')
    started=time.monotonic();service=GameService(a.root,async_metadata=True);rows=[];last=-1
    try:
        while not service._drivers and time.monotonic()-started<90:
            app.processEvents();time.sleep(.005)
            second=int(time.monotonic()-started)
            if second>last:
                last=second;r=service._metadata_reader
                rows.append(dict(seconds=second,error=service._storage_error,ticket=service._metadata_ticket,
                    reader=bool(r),inflight=bool(r and r.inflight),pending=bool(r and r.pending),
                    processAlive=bool(r and r.process and r.process.is_alive()),stats=r.last_stats if r else {}))
                a.output.write_text(json.dumps(dict(rows=rows,drivers=len(service._drivers)),indent=2)+'\n')
        print(json.dumps(dict(seconds=time.monotonic()-started,drivers=len(service._drivers),error=service._storage_error)),flush=True)
    finally:service.close()


if __name__=='__main__':main()
