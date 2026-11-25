#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/vendor/ArdPicProg"
mkdir -p "$ROOT/tools"

# Run from an MSYS2 UCRT64/MinGW shell with GCC installed.
g++ -std=gnu++11 -O2 -Wall \
  -DARDPICPROG_VERSION='"1.8.horo"' \
  -static -static-libgcc -static-libstdc++ \
  "$SRC/hexfile.cpp" "$SRC/main.cpp" "$SRC/serialport.cpp" "$SRC/serialport_win.cpp" \
  -o "$ROOT/tools/ardpicprog.exe"

# Smoke-test executable startup without opening a serial port.
set +e
"$ROOT/tools/ardpicprog.exe" --help > "$ROOT/tools/ardpicprog-help.txt" 2>&1
status=$?
set -e
if [[ $status -ne 64 ]] || ! grep -q -- '--pic-serial-port' "$ROOT/tools/ardpicprog-help.txt"; then
  echo "ArdPicProg host executable smoke test failed (exit $status)." >&2
  exit 1
fi
rm "$ROOT/tools/ardpicprog-help.txt"
echo "Built and smoke-tested tools/ardpicprog.exe"
