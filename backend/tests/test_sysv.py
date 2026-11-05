"""Generate and exercise installer service scripts without host changes."""
import re
import subprocess
from pathlib import Path

import pytest

from app.services import update_runtime

INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install-carbonpanel.sh'


def function(name):
    return re.search(rf'^{name}\(\) \{{\n.*?^\}}', INSTALLER.read_text(), re.M | re.S)[0]


def test_sysv_service_dispatch():
    script = function('service_command') + '''
uses_systemd() { return 1; }
service() { printf '%s\\n' "$*"; }
service_command daemon-reload
service_command restart carbonpanel-backend.service
service_command reload nginx
'''
    result = subprocess.run(['bash', '-eu', '-c', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ['carbonpanel-backend restart', 'nginx reload']


def test_generated_sysv_service_and_launcher(tmp_path):
    init = tmp_path / 'init'
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    script = function('write_sysv_service').replace('/etc/init.d/carbonpanel-backend', str(init))
    script = '''set -eu
BIN_DIR="$1/bin"
BACKEND_ENV_FILE="$1/backend.env"
INSTALL_ROOT="$1"
BACKEND_PORT=8788
CURRENT_LINK="$1/current"
SHARED_DIR="$1/shared"
SERVICE_USER=carbonpanel
SERVICE_GROUP=carbonpanel
command_exists() { return 0; }
chown() { :; }
''' + script + '\nwrite_sysv_service\n'
    result = subprocess.run(['bash', '-c', script, 'test', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for path in [init, bin_dir / 'carbonpanel-backend']:
        validation = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
        assert validation.returncode == 0, validation.stderr
    content = init.read_text()
    assert '$remote_fs $network' in content
    assert 'case "$1"' in content
    assert '--chuid "carbonpanel:carbonpanel"' in content
    assert '--retry TERM/30/KILL/5' in content
    assert 'CARBONPANEL_INIT_SYSTEM=sysv' in (bin_dir / 'carbonpanel-backend').read_text()


@pytest.mark.parametrize('args', [[], ['lvremove'], ['lvs', '--options'], ['pvs;id'], ['--help']])
def test_lvm_helper_rejects_other_commands(tmp_path, args):
    helper = INSTALLER.read_text().split("<<'LVM_HELPER'\n", 1)[1].split('\nLVM_HELPER', 1)[0]
    path = tmp_path / 'helper'
    path.write_text(helper)
    result = subprocess.run(['sh', str(path), *args], capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == ''


def test_sysv_browser_updates_require_installed_helper(monkeypatch):
    monkeypatch.setenv('CARBONPANEL_INIT_SYSTEM', 'sysv')
    monkeypatch.setattr(update_runtime.subprocess, 'run', lambda *a, **kw: pytest.fail('systemctl invoked'))
    monkeypatch.setattr(update_runtime, '_sysv_status', lambda: {})
    monkeypatch.setattr(update_runtime, '_sysv_helper_available', lambda: False)
    assert not update_runtime._service_is_active('carbonpanel-update.service')
    with pytest.raises(RuntimeError, match='Run carbonpanelctl update over SSH once'):
        update_runtime.trigger_update_check()
    with pytest.raises(RuntimeError, match='Run carbonpanelctl update over SSH once'):
        update_runtime.trigger_update_install()


def test_installer_provisions_sysv_updater_and_root_configuration(tmp_path):
    repository = INSTALLER.parent.parent
    prefix = tmp_path / 'system'
    module_dir = prefix / 'libexec'
    config_dir = prefix / 'etc'
    script = function('write_sysv_updater')
    script = script.replace('/usr/local/libexec', str(module_dir))
    script = script.replace('/etc/carbonpanel', str(config_dir))
    script = script.replace('install -d -o root -g root', 'install -d')
    script = script.replace('install -o root -g root', 'install')
    script = script.replace('os.chown(temporary, 0, 0)', 'pass # ownership stub for unprivileged test')
    setup = '''set -eu
CURRENT_LINK="$1"
INSTALL_ROOT="$2/custom install"
REPO_URL=https://example.com/panel
APP_PORT=9898
BACKEND_PORT=9899
'''
    result = subprocess.run(['bash', '-c', setup + script + '\nwrite_sysv_updater\n',
                             'test', str(repository), str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    import json
    config = config_dir / 'updater.json'
    assert json.loads(config.read_text()) == dict(
        install_root=str(tmp_path / 'custom install'), repo_url='https://example.com/panel',
        app_port='9898', backend_port='9899',
    )
    assert config.stat().st_mode & 0o777 == 0o600
    helper = module_dir / 'carbonpanel-updater'
    assert helper.stat().st_mode & 0o777 == 0o755
    assert helper.read_text() == (repository / 'scripts/sysv-updater.py').read_text()
