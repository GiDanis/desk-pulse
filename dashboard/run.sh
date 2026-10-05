#!/usr/bin/env bash
set -euo pipefail

dashboard_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mode="${1:---desktop}"
if [[ $# -gt 0 ]]; then shift; fi
demo=0
if [[ "$mode" == --demo ]]; then
    mode=--desktop
    demo=1
fi
case "$mode" in
    --desktop)
        export QSG_RHI_BACKEND=opengl
        export QT_XCB_GL_INTEGRATION=xcb_egl
        ;;
    --device)
        export QT_QPA_PLATFORM=eglfs
        export QT_QPA_EGLFS_INTEGRATION=eglfs_kms
        export QT_QPA_EGLFS_HIDECURSOR=1
        export QT_QPA_EGLFS_KMS_CONFIG="${SMARTPC_KMS_CONFIG:-/etc/smartpc/eglfs-kms.json}"
        export QSG_RHI_BACKEND=opengl
        ;;
    *)
        echo "Uso: $0 [--desktop|--device|--demo]" >&2
        exit 2
        ;;
esac

python_bin="${SMARTPC_PYTHON:-python3}"
if [[ "$mode" == --desktop ]] && ! "$python_bin" -c 'import PySide6.QtQuick' >/dev/null 2>&1; then
    desktop_python="${HOME}/.local/share/smartpc-dev-venv/bin/python"
    if [[ -x "$desktop_python" ]]; then
        python_bin="$desktop_python"
    fi
fi
if [[ "${SMARTPC_QML_ONLY:-0}" != 1 ]] && "$python_bin" -c 'import PySide6.QtQuick' >/dev/null 2>&1; then
    if [[ "$demo" == 1 ]]; then
        exec "$python_bin" "$dashboard_dir/app.py" --demo "$@"
    fi
    if [[ "$mode" == --device ]]; then
        theme_data_root="$("$python_bin" -c 'import os; from pathlib import Path; from PySide6.QtCore import QCoreApplication,QStandardPaths; a=QCoreApplication([]); a.setOrganizationName("SmartPC"); a.setApplicationName("SmartPC"); store=os.environ.get("SMARTPC_THEME_STORE"); print(str(Path(store).parent) if store else QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))')"
        exec "$python_bin" "$dashboard_dir/theme_supervisor.py" --data-root "$theme_data_root" -- "$python_bin" "$dashboard_dir/app.py" "$@"
    fi
    exec "$python_bin" "$dashboard_dir/app.py" "$@"
fi

if [[ "$demo" == 1 ]]; then
    echo "PySide6 non trovato: la modalità demo richiede il backend Python." >&2
    exit 1
fi
if [[ "$mode" == --device ]]; then
    echo "PySide6 non trovato: il kiosk richiede il backend Python." >&2
    exit 1
fi

if command -v qml6 >/dev/null 2>&1; then
    qml_bin="$(command -v qml6)"
elif command -v qml >/dev/null 2>&1; then
    qml_bin="$(command -v qml)"
elif [[ -x /usr/lib/qt6/bin/qml ]]; then
    qml_bin=/usr/lib/qt6/bin/qml
elif command -v qmlscene >/dev/null 2>&1; then
    qml_bin="$(command -v qmlscene)"
elif [[ -x /usr/lib/qt6/bin/qmlscene ]]; then
    qml_bin=/usr/lib/qt6/bin/qmlscene
else
    echo "Qt 6 QML runtime non trovato. Installa qmlscene e i moduli Qt Quick." >&2
    exit 1
fi

exec "$qml_bin" "$dashboard_dir/Main.qml"
