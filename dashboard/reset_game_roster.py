#!/usr/bin/env python3
"""Reset to the five capable base/residual pilots; external backup is required."""
import os
import sys
from pathlib import Path


def main():
    dashboard_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(dashboard_dir))
    from game_store import GameStore

    target = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        target = Path(sys.argv[1])
    else:
        env = os.environ.get('SMARTPC_GAME_STORE')
        if env:
            target = Path(env)
        else:
            try:
                from PySide6.QtCore import QCoreApplication, QStandardPaths
                app = QCoreApplication([])
                app.setOrganizationName('SmartPC')
                app.setApplicationName('SmartPC')
                target = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'game'
            except Exception:
                target = Path.home() / '.local' / 'share' / 'SmartPC' / 'game'

    store = GameStore(target)
    store.reset_roster()
    print(f"Roster resettato con successo in {target}:")
    for d in store.drivers():
        print(f"  - #{d['number']} {d['name']} ({d['profile']['algorithm']})")


if __name__ == '__main__':
    main()
