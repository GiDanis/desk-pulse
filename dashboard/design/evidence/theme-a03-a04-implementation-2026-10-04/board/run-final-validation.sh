#!/bin/bash
set -euo pipefail
TASK_ROOT=/tmp/smartpc-a03-diagnostic-complete/dashboard
TASK_RESULTS=/tmp/smartpc-a03-benchmark-complete
mkdir -p "$TASK_RESULTS"
trap 'sudo -n systemctl start smartpc-dashboard.service' EXIT
export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software
for suite in check_theme_ui.py check_notifications.py check_theme_motion.py check_theme_recovery.py;do
 python3 "$TASK_ROOT/check_theme_runtime_fixtures.py" --regression-child "$suite" >"$TASK_RESULTS/$suite.log" 2>&1
done
sudo -n systemctl stop smartpc-dashboard.service
export QT_QPA_PLATFORM=eglfs QT_QPA_EGLFS_INTEGRATION=eglfs_kms QT_QPA_EGLFS_HIDECURSOR=1 QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json QSG_RHI_BACKEND=opengl
unset QT_QUICK_BACKEND QSG_RENDER_LOOP
for check in check_theme_trace.py check_theme_frame_trace.py check_theme_trace_bridge.py check_theme_trace_metrics.py check_theme_core.py check_theme_api_contract.py;do
 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software python3 "$TASK_ROOT/$check" >"$TASK_RESULTS/$check.log" 2>&1
done
for loop in unset basic threaded; do
 if [[ $loop == unset ]];then unset QSG_RENDER_LOOP;else export QSG_RENDER_LOOP=$loop;fi
 timeout 40 python3 "$TASK_ROOT/verify_theme_frame_protocol.py" --directory "$TASK_RESULTS/protocol-$loop" >"$TASK_RESULTS/protocol-$loop.log" 2>&1
done
unset QSG_RENDER_LOOP
for trace in off on;do
 args=();if [[ $trace == on ]];then args+=(--trace);fi
 timeout 30 python3 "$TASK_ROOT/verify_theme_trace_idle.py" "${args[@]}" --output "$TASK_RESULTS/idle-$trace.json" >"$TASK_RESULTS/idle-$trace.log" 2>&1
done
for fonts in none three; do
 for pair in 1 2 3; do
  order='off on'; if [[ $pair == 2 ]];then order='on off';fi
  for trace in $order;do
   target="$TASK_RESULTS/$fonts-pair$pair-$trace"
   mkdir -p "$target"
   args=();if [[ $trace == on ]];then args+=(--trace);fi
   echo "START $fonts pair=$pair trace=$trace"
   if timeout 80 python3 "$TASK_ROOT/verify_theme_trace_board.py" --directory "$target" --swaps 100 --fonts "$fonts" "${args[@]}" >"$target/run.log" 2>&1;then outcome=0;else outcome=$?;fi
   printf "%s\n" "$outcome" >"$target/exit-code.txt"
   python3 - "$target/report.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));d=r.get('diagnostics',{})
print(json.dumps({'done':sys.argv[1],'swaps':r['swaps'],'legacyP95':r['requestToThemeFrameMs']['p95'],'coherentP95':d.get('requestToCoherentSubmissionMs',{}).get('p95'),'diagnosticsComplete':d.get('complete'),'peakPssMiB':r['memoryMiB']['peakPss'],'warnings':r['warnings']}))
PY
  done
 done
done
