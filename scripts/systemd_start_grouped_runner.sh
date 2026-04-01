#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/otavio/overseas-business-online"
PYTHON="$ROOT/.venv/bin/python"
RUNTIME_MINUTES="${1:-540}"

mkdir -p "$ROOT/.streamlit_logs" "$ROOT/.streamlit_logs/grouped_click_runs"

cd "$ROOT"
exec "$PYTHON" "$ROOT/run_grouped_ad_clicker.py" \
  --max-concurrent-groups 2 \
  --max-runtime-minutes "$RUNTIME_MINUTES"
