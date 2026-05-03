#!/usr/bin/env bash
# Run once on the Raspberry Pi to set up the venv, .env, and systemd service.
# Usage: cd ~/robocontrol && bash scripts/install.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$REPO_DIR/scripts/robocontrol.service"
SERVICE_DST=/etc/systemd/system/robocontrol.service
CURRENT_USER="$(whoami)"

echo "=== RoboControl install ==="
echo "Repo : $REPO_DIR"
echo "User : $CURRENT_USER"
echo ""

# ── Python virtual environment ────────────────────────────────────
echo "→ Creating virtual environment"
python3 -m venv "$REPO_DIR/venv"
source "$REPO_DIR/venv/bin/activate"

echo "→ Installing Python dependencies"
pip install --upgrade pip -q
pip install -r "$REPO_DIR/requirements.txt" -q

# ── picamera2 (system package — required for CSI camera streaming) ─
echo "→ Installing picamera2 system package"
sudo apt install -y python3-picamera2 --no-install-recommends -q 2>/dev/null || \
    echo "  (picamera2 not available on this OS — CSI camera disabled)"

# ── rrb3 hardware library (not on PyPI — install from source) ─────
SITE_PACKAGES="$REPO_DIR/venv/lib/$(python3 -c 'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')/site-packages"
if [ ! -f "$SITE_PACKAGES/rrb3.py" ]; then
    echo "→ Installing rrb3 motor driver library"
    TMP_RRB3=$(mktemp -d)
    git clone --depth 1 https://github.com/simonmonk/raspirobotboard3.git "$TMP_RRB3" -q
    cp "$TMP_RRB3/python/rrb3.py" "$SITE_PACKAGES/rrb3.py"
    rm -rf "$TMP_RRB3"
else
    echo "→ rrb3 already installed — skipping"
fi

# ── .env ─────────────────────────────────────────────────────────
if [ ! -f "$REPO_DIR/.env" ]; then
    echo "→ Creating .env from .env.example (edit it before starting)"
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
else
    echo "→ .env already exists — skipping"
fi

# ── systemd service ───────────────────────────────────────────────
echo "→ Installing systemd service"
sudo cp "$SERVICE_SRC" "$SERVICE_DST"
# Patch paths and user to match this installation
sudo sed -i "s|/home/pi/robocontrol|$REPO_DIR|g" "$SERVICE_DST"
sudo sed -i "s|User=pi|User=$CURRENT_USER|g" "$SERVICE_DST"

sudo systemctl daemon-reload
sudo systemctl enable robocontrol
sudo systemctl start robocontrol

echo ""
echo "=== Done ==="
systemctl status robocontrol --no-pager || true
echo ""
echo "Useful commands:"
echo "  sudo systemctl status robocontrol    # check status"
echo "  sudo systemctl restart robocontrol   # restart"
echo "  journalctl -u robocontrol -f         # live logs"
