#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/otavio/overseas-business-online"
PYTHON="$ROOT/.venv/bin/python"

mkdir -p "$ROOT/.streamlit_logs" "$ROOT/.streamlit_logs/grouped_click_runs"

cd "$ROOT"
"$PYTHON" "$ROOT/scripts/stop_grouped_runner.py"
"$PYTHON" "$ROOT/scripts/cleanup_old_artifacts.py" --days 7
