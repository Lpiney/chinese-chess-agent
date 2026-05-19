#!/usr/bin/env bash

set -euo pipefail

PORT=5000

PIDS="$(lsof -ti tcp:${PORT} || true)"

if [ -z "$PIDS" ]; then
  echo "No process is using port ${PORT}."
  exit 0
fi

echo "Stopping processes on port ${PORT}: $PIDS"
kill $PIDS
echo "Stopped."
