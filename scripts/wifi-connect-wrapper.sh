#!/usr/bin/env bash
# wifi-connect-wrapper.sh
#
# Runs on every boot via wifi-connect-fallback.service, AFTER
# wifi_provision.sh's boot-partition wifi.txt method has already had a
# chance to run. If the device already has a working network connection
# (from a previously-saved NetworkManager profile, or wifi_provision.sh),
# this does nothing. Otherwise it starts WiFi Connect's captive portal —
# connect to the "RoboCar-Setup" WiFi network from your phone or laptop,
# and it'll prompt you to pick the real network to join.
set -euo pipefail

WAIT_SECONDS="${WIFI_CONNECT_WAIT_SECONDS:-20}"
POLL_INTERVAL=2

echo "[wifi-connect-fallback] Waiting up to ${WAIT_SECONDS}s for an existing connection..."

elapsed=0
while [ "$elapsed" -lt "$WAIT_SECONDS" ]; do
    if [ "$(nmcli -t -f STATE general 2>/dev/null)" = "connected" ]; then
        echo "[wifi-connect-fallback] Already connected — skipping captive portal"
        exit 0
    fi
    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
done

# ${VAR:-default} intentionally falls back for BOTH "unset" and "set to
# empty" — matters because .env.example ships PORTAL_SSID= (blank) and
# systemd's EnvironmentFile= would otherwise export that literal empty
# string, which wifi-connect could take as a real (invalid) SSID.
PORTAL_SSID="${PORTAL_SSID:-RoboCar-Setup}"

echo "[wifi-connect-fallback] No connection after ${WAIT_SECONDS}s — starting the captive portal"
echo "[wifi-connect-fallback] Connect to WiFi '${PORTAL_SSID}' from your phone, then open any webpage"

if [ -n "${PORTAL_PASSPHRASE:-}" ]; then
    exec /usr/local/sbin/wifi-connect \
        --ui-directory /usr/local/share/wifi-connect/ui \
        --portal-ssid "$PORTAL_SSID" \
        --portal-passphrase "$PORTAL_PASSPHRASE"
else
    exec /usr/local/sbin/wifi-connect \
        --ui-directory /usr/local/share/wifi-connect/ui \
        --portal-ssid "$PORTAL_SSID"
fi
