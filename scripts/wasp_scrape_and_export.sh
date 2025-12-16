#!/usr/bin/env bash
set -euo pipefail

# Runs a targeted WASP adopter scrape (Gemini) + exports.
# Intended to be run by systemd timer on VPS.

cd "$(dirname "$0")/.."  # project root

PY="/var/www/apihub/venv/bin/python3"
if [ ! -x "$PY" ]; then
  # Fallback for local runs
  PY="python3"
fi

echo "Using python: $PY"

# 1) Export current WASP adopter list (ground truth) from DB
$PY scripts/export_wasp_adopters_from_db.py || true

# 2) Run Gemini intelligence scrape ONLY for WASP adopter companies
# Keep conservative defaults to stay under free tier limits.
$PY scripts/run_gemini_intelligence_for_wasp.py --limit 30 --sleep 30

# 3) Optional: export suction-tech (Econowind proxy) adopter list from DB
$PY scripts/export_econowind_adopters_from_db.py || true

# 4) Export regression dataset (feature matrix + labels)
$PY scripts/export_econowind_dataset.py || true
