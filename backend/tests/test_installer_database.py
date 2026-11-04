"""Regression checks for root-created SQLite files and backend startup order."""
import re
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install-carbonpanel.sh'


def function(name):
    return re.search(rf'^{name}\(\) \{{\n.*?^\}}', INSTALLER.read_text(), re.M | re.S)[0]


@pytest.mark.parametrize('sidecars', [False, True])
def test_database_permissions_include_recovery_sidecars(tmp_path, sidecars):
    database = tmp_path / 'panel.db'
    files = [database]
    if sidecars:
        files += [Path(str(database) + suffix) for suffix in ['-wal', '-shm', '-journal']]
    for path in files:
        path.touch(mode=0o600)
    unrelated = tmp_path / 'backend.env'
    unrelated.touch(mode=0o640)
    script = '''set -eu
SERVICE_USER=carbonpanel
SERVICE_GROUP=carbonpanel
sqlite_db_path() { printf '%s\\n' "$DATABASE"; }
chown() { printf '%s\\n' "$*"; }
'''
    script += function('chown_shared_db') + '\nDATABASE="$1"\nchown_shared_db\n'
    result = subprocess.run(['bash', '-c', script, 'test', str(database)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for path in files:
        assert path.stat().st_mode & 0o777 == 0o660
        assert f'carbonpanel:carbonpanel {path}' in result.stdout.splitlines()
    assert unrelated.stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize('healthy', [True, False])
def test_deployment_repairs_database_before_backend_opens_it(tmp_path, healthy):
    # Execute the real deployment function with package/service operations
    # stubbed. Startup refuses to proceed until root-created DBs are repaired.
    script = '''set -eu
CURRENT_LINK="$1/current"
PREVIOUS_LINK="$1/previous"
BACKEND_SERVICE=carbonpanel-backend.service
BACKEND_PORT=8788
printf 'root-created' > "$1/owner"
backup_sqlite_db() { :; }
save_release_sudoers() { :; }
write_release_metadata() { :; }
switch_symlink() { :; }
set_update_progress() { :; }
run_database_tasks() { printf 'root-created' > "$ROOT/owner"; }
chown_shared_db() { printf 'service-writable' > "$ROOT/owner"; }
write_nginx_config() { :; }
write_backend_service() { :; }
write_update_services() { :; }
warn() { :; }
restore_release_sudoers() { :; }
restore_sqlite_db() { printf 'root-created' > "$ROOT/owner"; }
persist_success_status() { :; }
cleanup_old_releases() { :; }
run_silent() { "$@"; }
service_command() {
  if [[ "$1" == restart && "$2" == "$BACKEND_SERVICE" ]]; then
    [[ "$(cat "$ROOT/owner")" == service-writable ]] || exit 17
    echo backend-started
  fi
}
wait_for_http() { return "$HEALTH_STATUS"; }
ROOT="$1"
HEALTH_STATUS="$2"
'''
    script += function('deploy_release') + '\ndeploy_release release master commit branch url now\n'
    result = subprocess.run(['bash', '-c', script, 'test', str(tmp_path),
                             '0' if healthy else '1'], capture_output=True, text=True)
    assert result.returncode == (0 if healthy else 1), result.stderr
    assert result.stdout.splitlines().count('backend-started') == (1 if healthy else 2)
