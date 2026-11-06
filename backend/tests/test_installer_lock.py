"""The updater owns its lock; daemonized children must never retain it."""
import os
import re
import signal
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install-carbonpanel.sh'


def function(name):
    return re.search(rf'^{name}\(\) \{{\n.*?^\}}', INSTALLER.read_text(), re.M | re.S)[0]


@pytest.mark.parametrize('launcher', ['service_command restart backend', 'run_silent daemon'])
def test_daemon_does_not_keep_installer_lock(tmp_path, launcher):
    lock = tmp_path / 'update.lock'
    pid_file = tmp_path / 'daemon.pid'
    script = '\n'.join(function(name) for name in ('run_silent', 'service_command'))
    script += '''
uses_systemd() { return 1; }
daemon() {
  test -z "${CARBONPANEL_LOCK_HELD:-}"
  sleep 30 </dev/null >/dev/null 2>&1 &
  echo "$!" > "$2"
}
service() { daemon unused "$PID_FILE"; }
PID_FILE="$2"
exec 9>"$1"
flock -n 9
export CARBONPANEL_LOCK_HELD=true
'''
    if launcher == 'run_silent daemon':
        launcher += ' unused "$PID_FILE"'
    script += launcher + '''
# Closing the child's descriptor must not release the installer's own lock.
if flock -n "$1" true; then exit 42; fi
'''
    try:
        result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(lock), str(pid_file)],
                                capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, result.stderr
        os.kill(int(pid_file.read_text()), 0)  # Child outlives the installer.
        assert subprocess.run(['flock', '-n', str(lock), 'true']).returncode == 0
    finally:
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGTERM)
            except ProcessLookupError:
                pass
