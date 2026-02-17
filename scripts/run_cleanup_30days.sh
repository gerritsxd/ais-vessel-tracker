#!/bin/bash
# Run 30-day database cleanup (use after git pull on VPS to trim and reclaim space).
# Usage: from project root:  ./scripts/run_cleanup_30days.sh
#    or: bash scripts/run_cleanup_30days.sh

set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

if [ -d "$ROOT/venv" ]; then
  PYTHON="$ROOT/venv/bin/python"
else
  PYTHON="python3"
fi

echo "Running 30-day database cleanup from: $ROOT"
"$PYTHON" src/utils/cleanup_database.py

echo ""
echo "Optional: restart services if the app is running (e.g. systemd)."
