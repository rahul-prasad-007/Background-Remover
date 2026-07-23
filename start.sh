#!/bin/bash
set -euo pipefail

PORT="${PORT:-7860}"

echo "Starting Shankar Card AI on 0.0.0.0:${PORT}"
echo "BG_PROVIDER=${BG_PROVIDER:-local} | BIREFNET_MODEL=${BIREFNET_MODEL:-birefnet-general-lite}"

exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers 1 \
  --timeout-keep-alive 75 \
  --log-level info
