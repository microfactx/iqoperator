#!/bin/bash
# Encaminha SIGTERM/SIGINT aos filhos para não deixar bot duplicado no restart.
set -e
echo "=== Start bot + cockpit ==="
python main.py &
BOT_PID=$!
PORT=${PORT:-3000} npm --prefix cockpit-next start -- -p $PORT &
COCKPIT_PID=$!
trap 'echo "stop: encerrando filhos..."; kill $BOT_PID $COCKPIT_PID 2>/dev/null; wait' TERM INT
wait $BOT_PID $COCKPIT_PID
