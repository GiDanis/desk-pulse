#!/bin/sh
# Qualified Orange Pi topology only. Keep the preceding governor for rollback.
set -eu
policy=/sys/devices/system/cpu/cpufreq/policy6/scaling_governor
saved=/run/smartpc-performance/previous-governor
check_board() {
    [ -f "$policy" ] &&
    [ "$(cat /sys/devices/system/cpu/cpu0/cpu_capacity)" = 385 ] &&
    [ "$(cat /sys/devices/system/cpu/cpu6/cpu_capacity)" = 1024 ] &&
    [ "$(cat /sys/devices/system/cpu/cpufreq/policy6/related_cpus)" = '6 7' ] &&
    grep -qw performance /sys/devices/system/cpu/cpufreq/policy6/scaling_available_governors
}
case "${1:-check}" in
    check) check_board ;;
    apply)
        check_board
        cat "$policy" > "$saved"
        if ! printf '%s\n' performance > "$policy" || [ "$(cat "$policy")" != performance ]; then
            cat "$saved" > "$policy"
            exit 1
        fi
        ;;
    restore)
        if [ -s "$saved" ] && [ -f "$policy" ]; then cat "$saved" > "$policy"; fi
        ;;
    *) exit 2 ;;
esac
