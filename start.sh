#!/bin/bash
set -e
echo "=== Build cockpit-next ==="
npm --prefix cockpit-next ci
npm --prefix cockpit-next run build
echo "=== Start bot + cockpit ==="
python main.py &
NEXT_PID=$!
npm --prefix cockpit-next start -- --port ${PORT:-3000} &
COCKPIT_PID=$!
wait $NEXT_PID $COCKPIT_PID
