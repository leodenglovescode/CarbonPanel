#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${CARBONPANEL_REPO_URL:-https://github.com/leodenglovescode/CarbonPanel}"
INSTALL_ROOT="${CARBONPANEL_INSTALL_ROOT:-/opt/carbonpanel}"
APP_PORT="${APP_PORT:-8787}"
BACKEND_PORT="${CARBONPANEL_BACKEND_PORT:-8788}"
SERVICE_USER="${CARBONPANEL_USER:-carbonpanel}"
SERVICE_GROUP="${CARBONPANEL_GROUP:-carbonpanel}"

RELEASES_DIR="$INSTALL_ROOT/releases"
SHARED_DIR="$INSTALL_ROOT/shared"
BIN_DIR="$INSTALL_ROOT/bin"
TMP_DIR="$INSTALL_ROOT/tmp"
CURRENT_LINK="$INSTALL_ROOT/current"
PREVIOUS_LINK="$INSTALL_ROOT/previous"
BACKEND_ENV_FILE="$SHARED_DIR/backend.env"
STATUS_FILE="$SHARED_DIR/update-status.json"
CONTROL_SCRIPT="$BIN_DIR/carbonpanelctl"
NGINX_SITE="/etc/nginx/sites-available/carbonpanel.conf"
NGINX_SITE_LINK="/etc/nginx/sites-enabled/carbonpanel.conf"
BACKEND_SERVICE="carbonpanel-backend.service"
UPDATE_CHECK_SERVICE="carbonpanel-update-check.service"
UPDATE_CHECK_TIMER="carbonpanel-update-check.timer"
UPDATE_SERVICE="carbonpanel-update.service"
SUDOERS_FILE="/etc/sudoers.d/carbonpanel-updater"

COMMAND="${1:-}"
shift || true

REQUESTED_REF=""

# ── Colors (disabled when not a tty) ─────────────────────────────────────────
if [[ -t 1 ]]; then
  RED=$'\e[1;31m'; GREEN=$'\e[1;32m'; YELLOW=$'\e[1;33m'
  CYAN=$'\e[1;36m'; MAGENTA=$'\e[0;35m'; WHITE=$'\e[1;37m'
  BOLD=$'\e[1m'; DIM=$'\e[2m'; NC=$'\e[0m'
else
  RED=''; GREEN=''; YELLOW=''; CYAN=''; MAGENTA=''; WHITE=''
  BOLD=''; DIM=''; NC=''
fi

if [[ "${EUID}" -ne 0 ]]; then
  printf "\n  ${RED}${BOLD}✗  hold up — this needs root.${NC}\n" >&2
  printf "  ${DIM}  try: curl -fsSL <url> | sudo bash${NC}\n\n" >&2
  exit 1
fi

# ── Output helpers ────────────────────────────────────────────────────────────
log()  { printf "  ${CYAN}›${NC}  %s\n" "$*"; }
ok()   { printf "  ${GREEN}✓${NC}  ${BOLD}%s${NC}\n" "$*"; }
warn() { printf "\n  ${YELLOW}⚠${NC}  ${YELLOW}%s${NC}\n\n" "$*" >&2; }
note() { printf "    ${DIM}%s${NC}\n" "$*"; }

die() {
  printf "\n  ${RED}${BOLD}✗  oh no —${NC} %s\n\n" "$*" >&2
  exit 1
}

# Run a command silently. On failure, dump its combined output to stderr and
# return the original exit code so callers can handle it (die, || true, etc.).
run_silent() {
  local _tmp _rc=0
  _tmp=$(mktemp)
  "$@" >"$_tmp" 2>&1 || _rc=$?
  if [[ $_rc -ne 0 ]]; then
    printf '\n' >&2
    cat "$_tmp" >&2
    printf '\n' >&2
  fi
  rm -f "$_tmp"
  return $_rc
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || die "this needs root. sudo up."
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

json_query() {
  python3 - "$1" <<'PY'
import json
import sys

query = sys.argv[1]
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    print("")
    raise SystemExit(0)

value = data
for part in query.split("."):
    if isinstance(value, list):
        try:
            value = value[int(part)]
        except (ValueError, IndexError):
            value = None
            break
    elif isinstance(value, dict):
        value = value.get(part)
    else:
        value = None
        break

if value is None:
    print("")
elif isinstance(value, (dict, list)):
    print(json.dumps(value))
else:
    print(value)
PY
}

repo_slug() {
  python3 - "$REPO_URL" <<'PY'
import sys
from urllib.parse import urlparse

url = sys.argv[1]
parsed = urlparse(url)
path = parsed.path.rstrip("/")
if path.endswith(".git"):
    path = path[:-4]
print(path.strip("/"))
PY
}

now_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

safe_name() {
  printf '%s' "$1" | tr '/:@ ' '----' | tr -cd '[:alnum:]._\n-'
}

generate_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

generate_password() {
  python3 - <<'PY'
import secrets
alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
print("".join(secrets.choice(alphabet) for _ in range(20)))
PY
}

write_json_file() {
  local target_path="$1"
  python3 - "$target_path" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)

data = {
    "repo_url": os.environ.get("CP_STATUS_REPO_URL") or None,
    "current_version": os.environ.get("CP_STATUS_CURRENT_VERSION") or None,
    "current_commit": os.environ.get("CP_STATUS_CURRENT_COMMIT") or None,
    "current_source_type": os.environ.get("CP_STATUS_CURRENT_SOURCE_TYPE") or None,
    "latest_version": os.environ.get("CP_STATUS_LATEST_VERSION") or None,
    "latest_commit": os.environ.get("CP_STATUS_LATEST_COMMIT") or None,
    "latest_source_type": os.environ.get("CP_STATUS_LATEST_SOURCE_TYPE") or None,
    "checked_at": os.environ.get("CP_STATUS_CHECKED_AT") or None,
    "status": os.environ.get("CP_STATUS_STATUS") or None,
    "error": os.environ.get("CP_STATUS_ERROR") or None,
    "release_url": os.environ.get("CP_STATUS_RELEASE_URL") or None,
    "notes_url": os.environ.get("CP_STATUS_NOTES_URL") or None,
    "update_available": os.environ.get("CP_STATUS_UPDATE_AVAILABLE", "false").lower() == "true",
}
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
tmp.replace(path)
PY
}

write_release_metadata() {
  local release_dir="$1"
  local metadata_path="$release_dir/.carbonpanel-release.json"

  CP_STATUS_REPO_URL="$REPO_URL" \
  CP_STATUS_CURRENT_VERSION="$2" \
  CP_STATUS_CURRENT_COMMIT="$3" \
  CP_STATUS_CURRENT_SOURCE_TYPE="$4" \
  CP_STATUS_CHECKED_AT="$5" \
  python3 - "$metadata_path" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = {
    "repo_url": os.environ["CP_STATUS_REPO_URL"],
    "version": os.environ["CP_STATUS_CURRENT_VERSION"],
    "commit": os.environ["CP_STATUS_CURRENT_COMMIT"],
    "source_type": os.environ["CP_STATUS_CURRENT_SOURCE_TYPE"],
    "installed_at": os.environ["CP_STATUS_CHECKED_AT"],
}
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

read_json_file_field() {
  local path="$1"
  local field="$2"

  if [[ ! -f "$path" ]]; then
    return 0
  fi

  python3 - "$path" "$field" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
field = sys.argv[2]

try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

value = data
for part in field.split("."):
    if isinstance(value, dict):
        value = value.get(part)
    else:
        value = None
        break

if value is None:
    print("")
else:
    print(value)
PY
}

load_backend_env() {
  set -a
  source "$BACKEND_ENV_FILE"
  set +a
}

sqlite_db_path() {
  load_backend_env
  python3 - "${DATABASE_URL:-}" <<'PY'
import sys

url = sys.argv[1]
for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
    if url.startswith(prefix):
        print(url[len(prefix):])
        raise SystemExit(0)
print("")
PY
}

github_api_get() {
  curl -fsSL --connect-timeout 10 --max-time 30 -H "Accept: application/vnd.github+json" "$1"
}

resolve_latest_reference() {
  local slug api_base release_json release_tag release_url tags_json tag_name repo_json default_branch
  slug="$(repo_slug)"
  api_base="https://api.github.com/repos/$slug"

  release_json="$(github_api_get "$api_base/releases/latest" 2>/dev/null || true)"
  release_tag="$(printf '%s' "$release_json" | json_query tag_name 2>/dev/null || true)"
  release_url="$(printf '%s' "$release_json" | json_query html_url 2>/dev/null || true)"

  if [[ -n "$release_tag" && "$release_tag" != "null" ]]; then
    printf 'release\n%s\n%s\n' "$release_tag" "$release_url"
    return 0
  fi

  tags_json="$(github_api_get "$api_base/tags?per_page=1" 2>/dev/null || true)"
  tag_name="$(printf '%s' "$tags_json" | json_query 0.name 2>/dev/null || true)"
  if [[ -n "$tag_name" && "$tag_name" != "null" ]]; then
    printf 'tag\n%s\n%s\n' "$tag_name" "https://github.com/$(repo_slug)/tags"
    return 0
  fi

  repo_json="$(github_api_get "$api_base" 2>/dev/null || true)"
  default_branch="$(printf '%s' "$repo_json" | json_query default_branch 2>/dev/null || true)"
  [[ -n "$default_branch" ]] || default_branch="master"
  printf 'branch\n%s\n%s\n' "$default_branch" "$REPO_URL"
}

resolve_requested_reference() {
  if [[ -n "$REQUESTED_REF" ]]; then
    if git ls-remote --exit-code --tags "$REPO_URL" "refs/tags/$REQUESTED_REF" >/dev/null 2>&1; then
      printf 'tag\n%s\n%s\n' "$REQUESTED_REF" "https://github.com/$(repo_slug)/releases/tag/$REQUESTED_REF"
      return 0
    fi
    printf 'branch\n%s\n%s\n' "$REQUESTED_REF" "$REPO_URL"
    return 0
  fi

  resolve_latest_reference
}

ensure_port_available() {
  if command_exists ss && ss -ltn "( sport = :$APP_PORT )" | grep -q ":$APP_PORT" && [[ ! -f "$NGINX_SITE" ]]; then
    die "Port $APP_PORT is already in use."
  fi
}

install_os_prerequisites() {
  command_exists apt-get || die "Only apt-based systems are supported by this installer right now."

  export DEBIAN_FRONTEND=noninteractive
  # Broken third-party repos (Docker, NVIDIA, Chrome, etc.) cause apt-get update
  # to return exit code 100. Treat that as a warning — the cached lists are enough.
  apt-get update -y >/dev/null 2>&1 || warn "some apt sources threw a tantrum — rolling with cached package lists, should be fine"
  # Core utilities — safe to install unconditionally on any apt system.
  run_silent apt-get install -y \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    sudo

  # nginx — skip if already present (nginx.org repo, BunkerWeb, OpenResty, etc. all conflict
  # with Ubuntu's nginx package but provide a compatible binary).
  if ! command_exists nginx; then
    apt-get install -y nginx >/dev/null 2>&1 || true
  fi

  # nodejs — skip if already present (NodeSource, nvm, volta, fnm all conflict
  # with Ubuntu's nodejs package but provide a compatible binary).
  if ! command_exists node && ! command_exists nodejs; then
    apt-get install -y nodejs >/dev/null 2>&1 || true
  fi

  # npm is bundled with NodeSource nodejs. Only fall back to the apt package
  # on systems where nodejs was installed without npm (older Ubuntu apt nodejs).
  if ! command_exists npm; then
    apt-get install -y npm >/dev/null 2>&1 || true
  fi

  command_exists python3 || die "python3 is required."
  command_exists git || die "git is required."
  command_exists nginx || die "nginx is required — install nginx and try again."
  command_exists node || command_exists nodejs || die "Node.js is required — install Node.js and try again."
  command_exists npm || die "npm is required — install Node.js with npm included and try again."
}

ensure_service_account() {
  if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    run_silent useradd --system --home "$INSTALL_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"
  fi
}

ensure_layout() {
  mkdir -p "$RELEASES_DIR" "$SHARED_DIR" "$BIN_DIR" "$TMP_DIR"
  chown root:root "$INSTALL_ROOT" "$RELEASES_DIR" "$BIN_DIR" "$TMP_DIR"
  chmod 755 "$INSTALL_ROOT" "$RELEASES_DIR" "$BIN_DIR" "$TMP_DIR"

  chown "$SERVICE_USER:$SERVICE_GROUP" "$SHARED_DIR"
  chmod 750 "$SHARED_DIR"
}

ensure_backend_env() {
  if [[ -f "$BACKEND_ENV_FILE" ]]; then
    chmod 640 "$BACKEND_ENV_FILE"
    chown root:"$SERVICE_GROUP" "$BACKEND_ENV_FILE"
    return 0
  fi

  local secret admin_password
  secret="$(generate_secret)"
  admin_password="$(generate_password)"

  cat > "$BACKEND_ENV_FILE" <<EOF
SECRET_KEY=$secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$admin_password
DATABASE_URL=sqlite+aiosqlite:////opt/carbonpanel/shared/carbonpanel.db
CORS_ORIGINS='["http://127.0.0.1:$APP_PORT","http://localhost:$APP_PORT"]'
METRICS_INTERVAL_SECONDS=1.0
PROCESS_LIMIT=25
CARBONPANEL_INSTALL_ROOT=$INSTALL_ROOT
EOF

  chmod 640 "$BACKEND_ENV_FILE"
  chown root:"$SERVICE_GROUP" "$BACKEND_ENV_FILE"

  cat > "$SHARED_DIR/first-install.txt" <<EOF
CarbonPanel initial credentials
===============================

URL: http://localhost:$APP_PORT
Username: admin
Password: $admin_password

This file is only written on first install.
Change the admin password after signing in.
EOF
  chmod 600 "$SHARED_DIR/first-install.txt"
  chown root:root "$SHARED_DIR/first-install.txt"
}

clone_release() {
  local ref="$1"
  local destination="$RELEASES_DIR/$2"

  run_silent git clone --depth 1 --branch "$ref" "$REPO_URL" "$destination" || \
    die "Failed to clone $REPO_URL at ref $ref. If you are behind a firewall, set your proxy first: export https_proxy=http://host:port"

  printf '%s\n' "$destination"
}

build_release() {
  local release_dir="$1"

  log "teaching python what's what..."
  note "spinning up a venv and pip installing — grab a coffee ☕"
  run_silent python3 -m venv "$release_dir/backend/.venv"
  run_silent "$release_dir/backend/.venv/bin/pip" install --upgrade pip setuptools wheel
  run_silent "$release_dir/backend/.venv/bin/pip" install -e "$release_dir/backend"

  log "bundling the frontend heat..."
  note "npm doing npm things — this one takes a sec 🌀"
  (
    cd "$release_dir/frontend"
    run_silent npm ci
    run_silent npm run build
  )

  run_silent install -m 0755 "$release_dir/scripts/install-carbonpanel.sh" "$CONTROL_SCRIPT"
}

write_nginx_config() {
  cat > "$NGINX_SITE" <<EOF
server {
    listen $APP_PORT;
    listen [::]:$APP_PORT;
    server_name _;

    root $CURRENT_LINK/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

  ln -sf "$NGINX_SITE" "$NGINX_SITE_LINK"
  run_silent nginx -t
}

write_backend_service() {
  cat > "/etc/systemd/system/$BACKEND_SERVICE" <<EOF
[Unit]
Description=CarbonPanel FastAPI backend
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CURRENT_LINK/backend
Environment=CARBONPANEL_INSTALL_ROOT=$INSTALL_ROOT
Environment=CARBONPANEL_BACKEND_PORT=$BACKEND_PORT
EnvironmentFile=$BACKEND_ENV_FILE
ExecStart=$CURRENT_LINK/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
}

write_update_services() {
  cat > "/etc/systemd/system/$UPDATE_CHECK_SERVICE" <<EOF
[Unit]
Description=CarbonPanel GitHub update check
After=network-online.target

[Service]
Type=oneshot
Environment=CARBONPANEL_INSTALL_ROOT=$INSTALL_ROOT
Environment=CARBONPANEL_REPO_URL=$REPO_URL
Environment=APP_PORT=$APP_PORT
Environment=CARBONPANEL_BACKEND_PORT=$BACKEND_PORT
ExecStart=$CONTROL_SCRIPT check
EOF

  cat > "/etc/systemd/system/$UPDATE_CHECK_TIMER" <<EOF
[Unit]
Description=Run CarbonPanel update checks daily

[Timer]
OnCalendar=daily
RandomizedDelaySec=30m
Persistent=true
Unit=$UPDATE_CHECK_SERVICE

[Install]
WantedBy=timers.target
EOF

  cat > "/etc/systemd/system/$UPDATE_SERVICE" <<EOF
[Unit]
Description=CarbonPanel interactive updater
After=network-online.target

[Service]
Type=oneshot
Environment=CARBONPANEL_INSTALL_ROOT=$INSTALL_ROOT
Environment=CARBONPANEL_REPO_URL=$REPO_URL
Environment=APP_PORT=$APP_PORT
Environment=CARBONPANEL_BACKEND_PORT=$BACKEND_PORT
ExecStart=$CONTROL_SCRIPT update
EOF

  cat > "$SUDOERS_FILE" <<EOF
$SERVICE_USER ALL=(root) NOPASSWD: /usr/bin/systemctl start $UPDATE_CHECK_SERVICE, /usr/bin/systemctl start $UPDATE_SERVICE
EOF
  chmod 440 "$SUDOERS_FILE"
}

systemd_reload_enable() {
  run_silent systemctl daemon-reload
  run_silent systemctl enable --now "$BACKEND_SERVICE"
  run_silent systemctl enable --now nginx
  run_silent systemctl enable --now "$UPDATE_CHECK_TIMER"
}

wait_for_http() {
  local url="$1"
  local attempt=0

  while (( attempt < 20 )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done

  return 1
}

run_database_tasks() {
  local release_dir="$1"
  local first_install="$2"

  (
    load_backend_env
    cd "$release_dir/backend"
    run_silent ./.venv/bin/alembic upgrade head
  )

  (
    load_backend_env
    cd "$release_dir/backend"
    run_silent ./.venv/bin/python -m app.scripts.seed_admin
  )
}

switch_symlink() {
  local link_path="$1"
  local target="$2"
  ln -sfn "$target" "$link_path"
}

backup_sqlite_db() {
  local db_path backup_path
  db_path="$(sqlite_db_path)"

  if [[ -z "$db_path" || ! -f "$db_path" ]]; then
    printf '\n'
    return 0
  fi

  backup_path="$TMP_DIR/db-backup-$(date -u +%Y%m%d%H%M%S).sqlite3"
  cp "$db_path" "$backup_path"
  printf '%s\n' "$backup_path"
}

restore_sqlite_db() {
  local backup_path="$1"
  local db_path

  [[ -n "$backup_path" ]] || return 0
  [[ -f "$backup_path" ]] || return 0

  db_path="$(sqlite_db_path)"
  [[ -n "$db_path" ]] || return 0

  cp "$backup_path" "$db_path"
  chown "$SERVICE_USER:$SERVICE_GROUP" "$db_path"
}

chown_shared_db() {
  local db_path
  db_path="$(sqlite_db_path)"
  if [[ -n "$db_path" && -f "$db_path" ]]; then
    chown "$SERVICE_USER:$SERVICE_GROUP" "$db_path"
    chmod 660 "$db_path"
  fi
}

cleanup_old_releases() {
  local keep_targets
  keep_targets="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
  keep_targets+=" $(readlink -f "$PREVIOUS_LINK" 2>/dev/null || true)"

  mapfile -t release_paths < <(find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d | sort -r)
  local count=0
  local release_path
  for release_path in "${release_paths[@]}"; do
    count=$((count + 1))
    if [[ " $keep_targets " == *" $release_path "* ]]; then
      continue
    fi
    if (( count > 4 )); then
      rm -rf "$release_path"
    fi
  done
}

persist_success_status() {
  local version="$1"
  local commit="$2"
  local source_type="$3"
  local checked_at="$4"
  local release_url="$5"

  CP_STATUS_REPO_URL="$REPO_URL" \
  CP_STATUS_CURRENT_VERSION="$version" \
  CP_STATUS_CURRENT_COMMIT="$commit" \
  CP_STATUS_CURRENT_SOURCE_TYPE="$source_type" \
  CP_STATUS_LATEST_VERSION="$version" \
  CP_STATUS_LATEST_COMMIT="$commit" \
  CP_STATUS_LATEST_SOURCE_TYPE="$source_type" \
  CP_STATUS_CHECKED_AT="$checked_at" \
  CP_STATUS_STATUS="installed" \
  CP_STATUS_ERROR="" \
  CP_STATUS_RELEASE_URL="$release_url" \
  CP_STATUS_NOTES_URL="$release_url" \
  CP_STATUS_UPDATE_AVAILABLE="false" \
  write_json_file "$STATUS_FILE"

  chmod 644 "$STATUS_FILE"
}

deploy_release() {
  local release_dir="$1"
  local version="$2"
  local commit="$3"
  local source_type="$4"
  local release_url="$5"
  local installed_at="$6"
  local current_target previous_target db_backup first_install

  current_target="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"
  previous_target="$(readlink -f "$PREVIOUS_LINK" 2>/dev/null || true)"
  first_install="false"
  [[ -z "$current_target" ]] && first_install="true"

  db_backup="$(backup_sqlite_db)"

  write_release_metadata "$release_dir" "$version" "$commit" "$source_type" "$installed_at"

  if [[ -n "$current_target" ]]; then
    switch_symlink "$PREVIOUS_LINK" "$current_target"
  fi

  switch_symlink "$CURRENT_LINK" "$release_dir"

  if ! run_database_tasks "$release_dir" "$first_install"; then
    warn "database step choked — rolling back, don't panic"
    [[ -n "$current_target" ]] && switch_symlink "$CURRENT_LINK" "$current_target"
    restore_sqlite_db "$db_backup"
    [[ -n "$previous_target" ]] && switch_symlink "$PREVIOUS_LINK" "$previous_target"
    return 1
  fi

  write_nginx_config
  write_backend_service
  write_update_services
  run_silent systemctl daemon-reload
  run_silent systemctl restart "$BACKEND_SERVICE"
  run_silent systemctl restart nginx

  if ! wait_for_http "http://127.0.0.1:$BACKEND_PORT/docs"; then
    warn "health check came back dead — rolling back to the last good version"
    [[ -n "$current_target" ]] && switch_symlink "$CURRENT_LINK" "$current_target"
    restore_sqlite_db "$db_backup"
    run_silent systemctl daemon-reload
    run_silent systemctl restart "$BACKEND_SERVICE" || true
    run_silent systemctl restart nginx || true
    [[ -n "$previous_target" ]] && switch_symlink "$PREVIOUS_LINK" "$previous_target"
    return 1
  fi

  chown_shared_db
  persist_success_status "$version" "$commit" "$source_type" "$installed_at" "$release_url"
  cleanup_old_releases
}

check_for_updates() {
  local source_type ref release_url checked_at current_version current_commit current_source_type latest_dir latest_commit update_available status_value error_value
  mapfile -t resolved < <(resolve_requested_reference)
  source_type="${resolved[0]}"
  ref="${resolved[1]}"
  release_url="${resolved[2]}"
  checked_at="$(now_iso)"

  current_version="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version)"
  current_commit="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" commit)"
  current_source_type="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" source_type)"

  latest_dir="$TMP_DIR/check-$(safe_name "$ref")"
  rm -rf "$latest_dir"
  run_silent git clone --depth 1 --branch "$ref" "$REPO_URL" "$latest_dir" || die "Unable to fetch latest version metadata."
  latest_commit="$(git -C "$latest_dir" rev-parse HEAD)"
  rm -rf "$latest_dir"

  update_available="false"
  status_value="up_to_date"
  error_value=""

  if [[ "$source_type" == "release" || "$source_type" == "tag" ]]; then
    if [[ "$current_version" != "$ref" || "$current_commit" != "$latest_commit" ]]; then
      update_available="true"
      status_value="update_available"
    fi
  elif [[ -z "$current_version" ]]; then
    status_value="not_installed"
  fi

  CP_STATUS_REPO_URL="$REPO_URL" \
  CP_STATUS_CURRENT_VERSION="$current_version" \
  CP_STATUS_CURRENT_COMMIT="$current_commit" \
  CP_STATUS_CURRENT_SOURCE_TYPE="$current_source_type" \
  CP_STATUS_LATEST_VERSION="$ref" \
  CP_STATUS_LATEST_COMMIT="$latest_commit" \
  CP_STATUS_LATEST_SOURCE_TYPE="$source_type" \
  CP_STATUS_CHECKED_AT="$checked_at" \
  CP_STATUS_STATUS="$status_value" \
  CP_STATUS_ERROR="$error_value" \
  CP_STATUS_RELEASE_URL="$release_url" \
  CP_STATUS_NOTES_URL="$release_url" \
  CP_STATUS_UPDATE_AVAILABLE="$update_available" \
  write_json_file "$STATUS_FILE"

  chmod 644 "$STATUS_FILE"

  if [[ "$update_available" == "true" ]]; then
    ok "new drop available: ${BOLD}${ref}${NC} — hit update to grab it 🆕"
  else
    ok "you're on the latest — no updates needed ✨"
  fi
}

install_or_update() {
  local install_mode="$1"
  local source_type ref release_url release_id release_dir commit installed_at

  log "sniffing for port squatters on :${APP_PORT}..."
  ensure_port_available
  log "grabbing system dependencies from apt..."
  install_os_prerequisites
  log "conjuring the carbonpanel service account..."
  ensure_service_account
  log "staking out territory on disk..."
  ensure_layout
  log "locking in your secrets and config..."
  ensure_backend_env

  log "asking github what's poppin..."
  mapfile -t resolved < <(resolve_requested_reference)
  source_type="${resolved[0]}"
  ref="${resolved[1]:-}"
  release_url="${resolved[2]:-}"

  [[ -n "$ref" ]] || die "couldn't figure out what version to install — check your internet connection and that ${REPO_URL} is reachable"

  log "yanking the code down (${BOLD}${ref}${NC})..."
  release_id="$(date -u +%Y%m%d%H%M%S)-$(safe_name "$ref")"
  release_dir="$(clone_release "$ref" "$release_id")"
  commit="$(git -C "$release_dir" rev-parse HEAD)"
  installed_at="$(now_iso)"

  CP_STATUS_REPO_URL="$REPO_URL" \
  CP_STATUS_CURRENT_VERSION="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version)" \
  CP_STATUS_CURRENT_COMMIT="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" commit)" \
  CP_STATUS_CURRENT_SOURCE_TYPE="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" source_type)" \
  CP_STATUS_LATEST_VERSION="$ref" \
  CP_STATUS_LATEST_COMMIT="$commit" \
  CP_STATUS_LATEST_SOURCE_TYPE="$source_type" \
  CP_STATUS_CHECKED_AT="$installed_at" \
  CP_STATUS_STATUS="installing" \
  CP_STATUS_ERROR="" \
  CP_STATUS_RELEASE_URL="$release_url" \
  CP_STATUS_NOTES_URL="$release_url" \
  CP_STATUS_UPDATE_AVAILABLE="false" \
  write_json_file "$STATUS_FILE"
  chmod 644 "$STATUS_FILE"

  build_release "$release_dir"

  if ! deploy_release "$release_dir" "$ref" "$commit" "$source_type" "$release_url" "$installed_at"; then
    CP_STATUS_REPO_URL="$REPO_URL" \
    CP_STATUS_CURRENT_VERSION="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version)" \
    CP_STATUS_CURRENT_COMMIT="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" commit)" \
    CP_STATUS_CURRENT_SOURCE_TYPE="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" source_type)" \
    CP_STATUS_LATEST_VERSION="$ref" \
    CP_STATUS_LATEST_COMMIT="$commit" \
    CP_STATUS_LATEST_SOURCE_TYPE="$source_type" \
    CP_STATUS_CHECKED_AT="$installed_at" \
    CP_STATUS_STATUS="rollback_complete" \
    CP_STATUS_ERROR="Update failed and the previous release was restored." \
    CP_STATUS_RELEASE_URL="$release_url" \
    CP_STATUS_NOTES_URL="$release_url" \
    CP_STATUS_UPDATE_AVAILABLE="true" \
    write_json_file "$STATUS_FILE"
    chmod 644 "$STATUS_FILE"
    die "Deployment failed and rollback was applied."
  fi

  systemd_reload_enable
  check_for_updates

  ok "carbonpanel ${ref} is live! (${commit:0:8})"
  if [[ -f "$SHARED_DIR/first-install.txt" && "$install_mode" == "install" ]]; then
    printf "\n"
    printf "  ${GREEN}${BOLD}🎉  you're in!${NC}\n"
    note "credentials → ${BOLD}${SHARED_DIR}/first-install.txt${NC}"
    note "panel       → ${BOLD}http://your-server-ip:${APP_PORT}${NC}"
    printf "\n"
  fi
}

rollback_release() {
  require_root

  local previous_target current_target
  previous_target="$(readlink -f "$PREVIOUS_LINK" 2>/dev/null || true)"
  current_target="$(readlink -f "$CURRENT_LINK" 2>/dev/null || true)"

  [[ -n "$previous_target" ]] || die "No previous release is available for rollback."

  switch_symlink "$CURRENT_LINK" "$previous_target"
  if [[ -n "$current_target" ]]; then
    switch_symlink "$PREVIOUS_LINK" "$current_target"
  fi

  run_silent systemctl daemon-reload
  run_silent systemctl restart "$BACKEND_SERVICE"
  run_silent systemctl restart nginx
  check_for_updates

  ok "rolled back to $(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version) — crisis averted 😅"
}

print_current_version() {
  local current_version current_commit installed_at slug api_base
  local release_json release_tag latest_version status_label short_commit

  # Read what's currently installed from the release metadata file
  current_version="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version)"
  current_commit="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" commit)"
  installed_at="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" installed_at)"

  # Live GitHub check — don't rely on cached STATUS_FILE which may be stale/missing
  slug="$(repo_slug)"
  api_base="https://api.github.com/repos/$slug"
  note "pinging github for the latest..."
  release_json="$(github_api_get "$api_base/releases/latest" 2>/dev/null || true)"
  release_tag="$(printf '%s' "$release_json" | json_query tag_name 2>/dev/null || true)"
  if [[ -z "$release_tag" || "$release_tag" == "null" ]]; then
    local tags_json
    tags_json="$(github_api_get "$api_base/tags?per_page=1" 2>/dev/null || true)"
    release_tag="$(printf '%s' "$tags_json" | json_query 0.name 2>/dev/null || true)"
  fi
  [[ -z "$release_tag" || "$release_tag" == "null" ]] && release_tag=""
  latest_version="${release_tag:-unknown}"

  # Determine status
  if [[ -z "$current_version" ]]; then
    if [[ -L "$CURRENT_LINK" ]]; then
      status_label="${YELLOW}installed (pre-dates version tracking)${NC}"
    else
      status_label="${DIM}not installed${NC}"
    fi
  elif [[ "$latest_version" == "unknown" ]]; then
    status_label="${DIM}installed — could not reach github${NC}"
  elif [[ "$current_version" == "$latest_version" ]]; then
    status_label="${GREEN}${BOLD}✓ up to date${NC}"
  else
    status_label="${YELLOW}${BOLD}⬆ update available${NC}"
  fi

  short_commit="${current_commit:0:12}"

  printf "\n"
  printf "  ${CYAN}${BOLD}version info${NC}\n"
  printf "  ${DIM}────────────────────────────────────────${NC}\n"
  printf "  installed   ${BOLD}%s${NC}\n" "${current_version:-unknown}"
  [[ -n "$short_commit" ]] && printf "  commit      ${DIM}%s${NC}\n" "$short_commit"
  [[ -n "$installed_at" ]] && printf "  since       ${DIM}%s${NC}\n" "$installed_at"
  printf "  latest      ${BOLD}%s${NC}\n" "$latest_version"
  printf "  status      "
  printf "${status_label}\n"
  printf "\n"
}

show_menu() {
  local installed_version=""
  if [[ -f "$CURRENT_LINK/.carbonpanel-release.json" ]]; then
    installed_version="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version)"
  fi

  printf "\n"
  printf "  ${CYAN}${BOLD}⚡  carbonpanel${NC}  ${DIM}— server monitoring${NC}\n"
  printf "\n"
  printf "  ${DIM}────────────────────────────────────────${NC}\n"
  if [[ -n "$installed_version" ]]; then
    printf "  ${GREEN}✓${NC}  running ${BOLD}%s${NC}\n" "$installed_version"
  else
    printf "  ${YELLOW}not installed yet${NC}  ${DIM}— fresh slate 🧼${NC}\n"
  fi
  printf "  ${DIM}────────────────────────────────────────${NC}\n"
  printf "\n"
  printf "  ${CYAN}${BOLD}1${NC}  install        ${DIM}cook a fresh one${NC}\n"
  printf "  ${CYAN}${BOLD}2${NC}  update         ${DIM}grab the latest heat${NC}\n"
  printf "  ${CYAN}${BOLD}3${NC}  rollback       ${DIM}hit the oops button${NC}\n"
  printf "  ${CYAN}${BOLD}4${NC}  uninstall      ${DIM}scorched earth 🔥${NC}\n"
  printf "  ${CYAN}${BOLD}5${NC}  version info   ${DIM}see what's poppin${NC}\n"
  printf "\n"
  printf "  ${BOLD}pick one [1-5]:${NC} "
  read -r choice
  printf '\n'
  case "$choice" in
    1) COMMAND="install" ;;
    2) COMMAND="update" ;;
    3) COMMAND="rollback" ;;
    4) COMMAND="uninstall" ;;
    5) COMMAND="current-version" ;;
    *) die "that's not a valid option bud — pick a number between 1 and 5" ;;
  esac
}

uninstall_carbonpanel() {
  require_root

  if [[ ! -d "$INSTALL_ROOT" ]]; then
    die "CarbonPanel does not appear to be installed (${INSTALL_ROOT} not found)."
  fi

  local installed_version db_path db_backup
  installed_version="$(read_json_file_field "$CURRENT_LINK/.carbonpanel-release.json" version 2>/dev/null || true)"

  printf "\n"
  printf "  ${RED}${BOLD}☠   SCORCHED EARTH MODE  ☠${NC}\n"
  [[ -n "$installed_version" ]] && printf "  ${DIM}  currently running: %s${NC}\n" "$installed_version"
  printf "\n"
  printf "  ${YELLOW}this will permanently delete carbonpanel,\n"
  printf "  its services, and all data. no undo button.${NC}\n"
  printf "\n"
  printf "  ${BOLD}are you sure? [y/N]:${NC} "
  read -r confirm
  [[ "${confirm,,}" == "y" ]] || { printf "\n  ${GREEN}✓${NC}  smart move — nothing was touched\n\n"; exit 0; }

  db_path=""
  if [[ -f "$BACKEND_ENV_FILE" ]]; then
    db_path="$(sqlite_db_path 2>/dev/null || true)"
  fi

  if [[ -n "$db_path" && -f "$db_path" ]]; then
    printf "  ${BOLD}back up the database first? [Y/n]:${NC} "
    read -r do_backup
    if [[ "${do_backup,,}" != "n" ]]; then
      db_backup="/tmp/carbonpanel-db-$(date -u +%Y%m%d%H%M%S).sqlite3"
      cp "$db_path" "$db_backup"
      ok "database saved to ${BOLD}${db_backup}${NC} — just in case 🛟"
    fi
  fi

  # Only CarbonPanel's own systemd units are removed.
  # nginx, npm, nodejs, and any other system services are left untouched.
  log "yeeting carbonpanel services into the void..."
  for svc in "$UPDATE_CHECK_TIMER" "$UPDATE_CHECK_SERVICE" "$UPDATE_SERVICE" "$BACKEND_SERVICE"; do
    systemctl stop "$svc" >/dev/null 2>&1 || true
    systemctl disable "$svc" >/dev/null 2>&1 || true
    rm -f "/etc/systemd/system/$svc"
  done
  run_silent systemctl daemon-reload

  # Remove only CarbonPanel's nginx site config — nginx itself is not stopped or removed.
  log "scrubbing our nginx footprint (nginx itself stays up) ..."
  rm -f "$NGINX_SITE" "$NGINX_SITE_LINK"
  nginx -t >/dev/null 2>&1 && systemctl reload nginx >/dev/null 2>&1 || true

  log "revoking the sudo backstage pass..."
  rm -f "$SUDOERS_FILE"

  log "carpet bombing ${INSTALL_ROOT}..."
  rm -rf "$INSTALL_ROOT"

  printf "  ${BOLD}remove the '%s' system user too? [y/N]:${NC} " "$SERVICE_USER"
  read -r remove_user
  if [[ "${remove_user,,}" == "y" ]]; then
    userdel "$SERVICE_USER" >/dev/null 2>&1 || true
    ok "service user gone"
  fi

  printf "\n"
  ok "carbonpanel has been yeeted into the void 💨"
  [[ -n "${db_backup:-}" ]] && note "db backup → ${BOLD}${db_backup}${NC}"
  printf "\n"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)
      REQUESTED_REF="${2:-}"
      shift 2
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

# When invoked via pipe (curl | sudo bash) stdin is the pipe, not the terminal.
# Reopen stdin from /dev/tty so interactive prompts work.
# Note: do NOT add 2>/dev/null here — it would permanently suppress all stderr.
exec </dev/tty || true

[[ -z "$COMMAND" ]] && show_menu

case "$COMMAND" in
  install)
    require_root
    install_or_update "install"
    ;;
  update)
    require_root
    install_or_update "update"
    ;;
  check)
    require_root
    ensure_layout
    check_for_updates
    ;;
  rollback)
    rollback_release
    ;;
  uninstall)
    uninstall_carbonpanel
    ;;
  current-version)
    print_current_version
    ;;
  *)
    die "Unknown command: $COMMAND"
    ;;
esac
