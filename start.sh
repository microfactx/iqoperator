#!/bin/bash
set -e
echo "=== Start bot + cockpit ==="
python main.py &
NEXT_PID=$!
PORT=${PORT:-3000} npm --prefix cockpit-next start -- --port $PORT &
COCKPIT_PID=$!
wait $NEXT_PID $COCKPIT_PID
