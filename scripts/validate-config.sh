#!/usr/bin/env sh
set -eu

if command -v python3 >/dev/null 2>&1; then
  python3 scripts/validate_config.py
else
  printf 'python3 is required to run validation.\n' >&2
  exit 1
fi
