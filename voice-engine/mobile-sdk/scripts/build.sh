#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
npm --prefix apps/web run build
(cd apps/web && node ../../scripts/check-call-session-output-id.mjs)
apps/api/.venv/bin/python -m compileall \
  apps/api/__init__.py \
  apps/api/config.py \
  apps/api/main.py \
  apps/api/integrations \
  apps/api/memory \
  apps/api/realtime \
  apps/api/runtime \
  apps/api/shared \
  apps/api/voice
