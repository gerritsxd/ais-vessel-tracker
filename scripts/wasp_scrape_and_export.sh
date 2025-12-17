#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."  # project root

PY="/var/www/apihub/venv/bin/python3"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

echo "Using python: $PY"

# 1) Export current WASP adopter list (ground truth) from DB
$PY scripts/export_wasp_adopters_from_db.py || true

# 2) Try Gemini first; if quota exhausted (exit 42), fall back to V2 scraper
set +e
$PY scripts/run_gemini_intelligence_for_wasp.py --limit 30 --sleep 30
RC=$?
set -e

if [ $RC -eq 42 ]; then
  echo "Gemini quota exhausted; falling back to intelligence_v2 (DuckDuckGo) for WASP adopters"
  $PY scripts/run_intelligence_v2_for_wasp.py --limit 20 || true
elif [ $RC -ne 0 ]; then
  echo "Gemini WASP scrape failed with exit code $RC (continuing)"
fi

# 3) WASP-only website profiling (About/Mission/Sustainability pages)
$PY scripts/run_profiler_v3_for_wasp.py --limit 30 --max-pages 8 || true

# 4) Export WASP website sentiment CSV (from profiled pages)
$PY scripts/export_wasp_website_sentiment.py || true

# 5) Optional: export suction-tech (Econowind proxy) adopter list from DB
$PY scripts/export_econowind_adopters_from_db.py || true

# 6) Export regression dataset (feature matrix + labels)
$PY scripts/export_econowind_dataset.py || true
