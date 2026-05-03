#!/usr/bin/env bash
# Upgrade robocar on the Pi from the public GitHub repo and restart the service.
# Usage: bash scripts/deploy.sh
# Override: PI_HOST=pi@192.168.1.93 VENV=/home/pi/robocar-venv bash scripts/deploy.sh
set -euo pipefail

PI_HOST="${PI_HOST:-pi@192.168.1.93}"
VENV="${VENV:-/home/pi/robocar-venv}"

echo "=== robocar deploy ==="
echo "Target : $PI_HOST"
echo ""

ssh "$PI_HOST" bash << ENDSSH
set -e
echo "→ Upgrading robocar package"
$VENV/bin/pip install --upgrade "git+https://github.com/ZioGuillo/robocar.git" -q
echo "→ Restarting service"
sudo systemctl restart robocar
sleep 2
if systemctl is-active --quiet robocar; then
    echo "✓ robocar is running"
else
    echo "✗ Service failed — last 30 log lines:"
    journalctl -u robocar -n 30 --no-pager
    exit 1
fi
ENDSSH

echo ""
echo "=== Deploy complete ==="
echo "  Logs : ssh $PI_HOST journalctl -u robocar -f"
