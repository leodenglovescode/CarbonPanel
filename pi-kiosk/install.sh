#!/usr/bin/env bash
# Pulls pi-kiosk from GitHub, sets up its venv, prompts for CarbonPanel
# credentials, and installs it as a systemd service. Safe to re-run: pulls
# the latest code and reuses an existing config.json unless you say no.
#
#   ./install.sh                              # first run, or update in place
#   ./install.sh --proxy http://host:port     # apt+pip through a proxy
set -euo pipefail

REPO_URL="https://github.com/leodenglovescode/CarbonPanel.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/CarbonPanel}"
PROXY=""

while [ $# -gt 0 ]; do
    case "$1" in
        --proxy) PROXY="$2"; shift 2 ;;
        -h|--help) echo "usage: $0 [--proxy http://host:port]"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [ -n "$PROXY" ]; then
    export http_proxy="$PROXY" https_proxy="$PROXY"
    echo "Acquire::http::Proxy \"$PROXY\";
Acquire::https::Proxy \"$PROXY\";" | sudo tee /etc/apt/apt.conf.d/95proxy >/dev/null
fi

echo "==> checking system packages"
NEEDED=()
command -v git >/dev/null || NEEDED+=(git)
python3 -c "import sysconfig,os,sys; sys.exit(0 if os.path.exists(sysconfig.get_paths()['include']+'/Python.h') else 1)" || NEEDED+=(python3-dev)
python3 -m venv --help >/dev/null 2>&1 || NEEDED+=(python3-venv)
if [ "${#NEEDED[@]}" -gt 0 ]; then
    sudo apt update
    sudo apt install -y "${NEEDED[@]}"
fi

echo "==> fetching CarbonPanel into $INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
KIOSK_DIR="$INSTALL_DIR/pi-kiosk"
cd "$KIOSK_DIR"

echo "==> python environment"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

KEEP=n
if [ -f config.json ]; then
    read -rp "config.json already exists — keep it? [Y/n] " KEEP
    KEEP=${KEEP:-Y}
fi

if [[ ! "$KEEP" =~ ^[Yy] ]]; then
    GATEWAY=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
    DEFAULT_URL="http://${GATEWAY:-192.168.1.1}:8000"
    read -rp "CarbonPanel base URL [$DEFAULT_URL]: " BASE_URL
    BASE_URL=${BASE_URL:-$DEFAULT_URL}
    read -rp "CarbonPanel username: " CP_USER
    read -rsp "CarbonPanel password: " CP_PASS
    echo
    python3 - "$BASE_URL" "$CP_USER" "$CP_PASS" <<'PYEOF'
import json, sys
base_url, username, password = sys.argv[1:4]
with open("config.json", "w") as f:
    json.dump({"base_url": base_url, "username": username, "password": password}, f, indent=2)
PYEOF
    chmod 600 config.json
fi

echo "==> selftest"
.venv/bin/python kiosk.py --selftest

echo "==> installing systemd service"
sed -e "s#__DIR__#$KIOSK_DIR#g" -e "s#__USER__#$(whoami)#g" carbonpanel-kiosk.service \
    | sudo tee /etc/systemd/system/carbonpanel-kiosk.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now carbonpanel-kiosk

echo "==> done — journalctl -u carbonpanel-kiosk -f to watch it, or edit $KIOSK_DIR/config.json and 'sudo systemctl restart carbonpanel-kiosk'"
