#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r api/requirements.txt

uvicorn api.main:app --host 127.0.0.1 --port "${PORT:-8787}" &
api_pid=$!

cd web
npm install
npm run dev

kill "$api_pid"
