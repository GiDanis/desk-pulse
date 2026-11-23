#!/usr/bin/env bash
# Build on the target architecture; keep the old library if compilation fails.
set -euo pipefail
native_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
native_output_dir="${1:-$native_repo_root/dashboard}"
native_compiler="${CC:-cc}"
mkdir -p "$native_output_dir"
native_temporary="$(mktemp "$native_output_dir/.libsmartpc_game_native.XXXXXX.so")"
trap 'rm -f "$native_temporary"' EXIT
"$native_compiler" -O3 -ffp-contract=off -fPIC -shared \
    "$native_repo_root/dashboard/game_native.c" -lm -o "$native_temporary"
chmod 755 "$native_temporary"
mv "$native_temporary" "$native_output_dir/libsmartpc_game_native.so"
file "$native_output_dir/libsmartpc_game_native.so"
