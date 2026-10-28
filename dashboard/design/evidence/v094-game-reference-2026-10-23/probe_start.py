"""QtCore-only isolated Start timing; never the production store."""
from pathlib import Path
import argparse,json,time
from PySide6.QtCore import QCoreApplication
from game import GameService
from check_game_menu import menu_prepare


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert str(a.root.resolve()).startswith('/var/tmp/')
    app=QCoreApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('Dashboard')
    s=GameService(a.root,async_metadata=True);started=time.monotonic()
    try:
        while not s._drivers and time.monotonic()-started<10:app.processEvents();time.sleep(.005)
        assert s._drivers,s._storage_error
        menu_prepare(s,'Crono','qualifica');started=time.monotonic();assert s._settings.apply('start')
        last=-1
        while s._run_state not in ('running','error') and time.monotonic()-started<30:
            app.processEvents();time.sleep(.005)
            if int(time.monotonic()-started)>last:
                last=int(time.monotonic()-started)
                report=dict(seconds=time.monotonic()-started,state=s._run_state,message=s._message,
                    stages=list(s.startup_diagnostics),pid=s._process.pid if s._process else None)
                a.output.write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
        report.update(state=s._run_state,message=s._message,stages=list(s.startup_diagnostics),seconds=time.monotonic()-started)
        a.output.write_text(json.dumps(report,indent=2)+'\n')
    finally:s.close()


if __name__=='__main__':main()
