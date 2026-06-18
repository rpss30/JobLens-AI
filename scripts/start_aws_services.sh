#!/usr/bin/env bash

set -uo pipefail

api_pid=""
dashboard_pid=""

shutdown() {
    trap - EXIT INT TERM

    if [[ -n "${api_pid}" ]]; then
        kill -TERM "${api_pid}" 2>/dev/null || true
    fi

    if [[ -n "${dashboard_pid}" ]]; then
        kill -TERM "${dashboard_pid}" 2>/dev/null || true
    fi

    wait "${api_pid}" "${dashboard_pid}" 2>/dev/null || true
}

trap shutdown EXIT INT TERM

uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 &
api_pid="$!"

streamlit run src/dashboard/app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true \
    --browser.gatherUsageStats=false &
dashboard_pid="$!"

wait -n "${api_pid}" "${dashboard_pid}"
