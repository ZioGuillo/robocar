#!/usr/bin/env bash
# install.sh
#
# Run once on the Raspberry Pi to set up the venv, systemd services,
# WiFi provisioning, and Cloudflare Tunnel auto-assignment.
#
# Usage: cd ~/robocontrol && bash scripts/install.sh
#
# Before running, place on the boot partition:
#
#   /boot/firmware/wifi.txt          (WiFi credentials)
#     SSID=YourNetwork
#     PASSWORD=YourPassword
#
#   /boot/firmware/cloudflared.env   (Cloudflare credentials — new rover only)
#     CF_API_TOKEN=...
#     CF_ACCOUNT_ID=...
#     CF_ZONE_ID=...
#
# If this Pi already has a Cloudflare tunnel configured (~/.cloudflared/config.yml),
# the provisioning step is skipped automatically.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CURRENT_USER="$(whoami)"
ARCH="$(uname -m)"

echo "=== RoboControl install ==="
echo "Repo : $REPO_DIR"
echo "User : $CURRENT_USER"
echo "Arch : $ARCH"
echo ""

# ── Python virtual environment ────────────────────────────────────────
echo "→ Creating virtual environment"
python3 -m venv "$REPO_DIR/venv"
source "$REPO_DIR/venv/bin/activate"

echo "→ Installing Python dependencies"
pip install --upgrade pip -q
pip install -r "$REPO_DIR/requirements.txt" -q

# ── picamera2 ─────────────────────────────────────────────────────────
echo "→ Installing picamera2 system package"
sudo apt install -y python3-picamera2 --no-install-recommends -q 2>/dev/null || \
    echo "  (picamera2 not available — CSI camera disabled)"

# ── rrb3 motor driver ─────────────────────────────────────────────────
SITE_PACKAGES="$REPO_DIR/venv/lib/$(python3 -c \
    'import sys; print(f"python{sys.version_info.major}.{sys.version_info.minor}")')/site-packages"
if [ ! -f "$SITE_PACKAGES/rrb3.py" ]; then
    echo "→ Installing rrb3 motor driver"
    TMP_RRB3=$(mktemp -d)
    git clone --depth 1 https://github.com/simonmonk/raspirobotboard3.git "$TMP_RRB3" -q
    cp "$TMP_RRB3/python/rrb3.py" "$SITE_PACKAGES/rrb3.py"
    rm -rf "$TMP_RRB3"
else
    echo "→ rrb3 already installed — skipping"
fi

# ── .env ──────────────────────────────────────────────────────────────
if [ ! -f "$REPO_DIR/.env" ]; then
    echo "→ Creating .env from .env.example"
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
else
    echo "→ .env already exists — skipping"
fi

# ── cloudflared binary ────────────────────────────────────────────────
if ! command -v cloudflared &>/dev/null; then
    echo "→ Downloading cloudflared"
    case "$ARCH" in
        aarch64) CF_BIN="cloudflared-linux-arm64"  ;;
        armv7l)  CF_BIN="cloudflared-linux-arm"    ;;
        x86_64)  CF_BIN="cloudflared-linux-amd64"  ;;
        *)        echo "  Unknown arch $ARCH — skipping cloudflared download"
                  CF_BIN="" ;;
    esac
    if [ -n "$CF_BIN" ]; then
        CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/$CF_BIN"
        sudo curl -fsSL "$CF_URL" -o /usr/local/bin/cloudflared
        sudo chmod +x /usr/local/bin/cloudflared
        echo "  Installed: $(cloudflared --version)"
    fi
else
    echo "→ cloudflared already installed: $(cloudflared --version)"
fi

# ── WiFi provisioning service ─────────────────────────────────────────
echo "→ Installing wifi-provision.service"
sudo cp "$REPO_DIR/scripts/wifi-provision.service" /etc/systemd/system/wifi-provision.service
sudo sed -i "s|/home/pi/robocontrol|$REPO_DIR|g"  /etc/systemd/system/wifi-provision.service
sudo sed -i "s|User=pi|User=$CURRENT_USER|g"       /etc/systemd/system/wifi-provision.service
sudo mkdir -p /var/lib/robocontrol
sudo systemctl daemon-reload
sudo systemctl enable wifi-provision.service
# Run now so WiFi connects immediately if wifi.txt is present
sudo bash "$REPO_DIR/scripts/wifi_provision.sh" || echo "  (wifi_provision: no wifi.txt or already connected)"

# ── Cloudflare Tunnel provisioning service ────────────────────────────
echo "→ Installing cloudflared-provision.service"
sudo cp "$REPO_DIR/scripts/cloudflared-provision.service" \
        /etc/systemd/system/cloudflared-provision.service
sudo sed -i "s|/home/pi/robocontrol|$REPO_DIR|g"  /etc/systemd/system/cloudflared-provision.service
sudo sed -i "s|User=pi|User=$CURRENT_USER|g"       /etc/systemd/system/cloudflared-provision.service
sudo systemctl daemon-reload
sudo systemctl enable cloudflared-provision.service

# ── Run tunnel provisioning now ───────────────────────────────────────
if [ -f "$HOME/.cloudflared/config.yml" ]; then
    ROVER_ID=$(cat "$HOME/.cloudflared/rover_id" 2>/dev/null || echo "??")
    echo "→ Cloudflare tunnel already configured (rover${ROVER_ID}) — skipping"
else
    echo "→ Running Cloudflare Tunnel provisioning..."
    python3 "$REPO_DIR/scripts/cloudflared_provision.py" || \
        echo "  WARNING: tunnel provisioning failed — check credentials and run again"
fi

# ── robocontrol systemd service ───────────────────────────────────────
echo "→ Installing robocontrol.service"
SERVICE_SRC="$REPO_DIR/scripts/robocontrol.service"
SERVICE_DST=/etc/systemd/system/robocontrol.service
sudo cp "$SERVICE_SRC" "$SERVICE_DST"
sudo sed -i "s|/home/pi/robocontrol|$REPO_DIR|g" "$SERVICE_DST"
sudo sed -i "s|User=pi|User=$CURRENT_USER|g"      "$SERVICE_DST"
sudo systemctl daemon-reload
sudo systemctl enable robocontrol
sudo systemctl start  robocontrol

# ── done ─────────────────────────────────────────────────────────────
echo ""
echo "=== Done ==="
systemctl status robocontrol --no-pager || true
echo ""

LOCAL_IP=$(hostname -I | awk '{print $1}')
ROVER_URL=$(cat "$HOME/.cloudflared/rover_url" 2>/dev/null || echo "")

echo "  Local URL  : http://${LOCAL_IP}:8000"
if [ -n "$ROVER_URL" ]; then
    echo "  Public URL : ${ROVER_URL}"
else
    echo "  Public URL : not configured (local-only mode)"
    echo ""
    echo "  To expose this rover to the internet, add Cloudflare credentials"
    echo "  to .env and run:  python3 scripts/cloudflared_provision.py"
    echo "  See README → 'Deploying to a New Rover' for instructions."
fi
echo ""
echo "Useful commands:"
echo "  sudo systemctl status robocontrol       # app status"
echo "  sudo systemctl status cloudflared       # tunnel status"
echo "  journalctl -u robocontrol -f            # app logs"
echo "  journalctl -u cloudflared-provision -f  # provisioning logs"
