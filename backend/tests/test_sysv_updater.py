"""Exercise the detached updater using only fake installers under tmp_path."""
import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/sysv-updater.py'
spec = importlib.util.spec_from_file_location('sysv_updater', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.fixture
def installed(tmp_path, monkeypatch):
    shared = tmp_path / 'shared'
    shared.mkdir()
    runtime = tmp_path / 'run'
    runtime.mkdir(mode=0o700)
    monkeypatch.setattr(helper, 'RUNTIME', runtime)
    config = dict(install_root=str(tmp_path), repo_url='https://example.com/panel',
                  app_port='8787', backend_port='8788')
    return tmp_path, shared, runtime, config


def test_stale_job_does_not_count_as_running(installed):
    root, shared, runtime, _ = installed
    operation_id = helper.queue_operation(shared, 'update')
    helper.write_json(runtime / 'job.json', dict(
        kind='update', operation_id=operation_id, running=True, pid=os.getpid(),
    ))
    assert helper.running_status(shared) == {'running': False, 'kind': None}
    status = helper.read_json(shared / 'update-status.json')
    assert status['operation_id'] == operation_id
    assert status['operation_state'] == 'failed'
    assert status['restart_pending'] is False


def test_external_cli_lock_blocks_web_updates(installed):
    _, shared, _, config = installed
    descriptor = helper.lock_file(shared / 'update.lock')
    try:
        assert helper.running_status(shared) == {'running': True, 'kind': 'external'}
        with pytest.raises(RuntimeError, match='already running'):
            helper.launch(config, shared / 'unused', shared, 'update')
        assert not (shared / 'update-status.json').exists()
    finally:
        os.close(descriptor)


def test_lock_file_rejects_symlinks(installed):
    root, _, _, _ = installed
    target = root / 'target'
    target.write_text('unchanged')
    link = root / 'link'
    link.symlink_to(target)
    with pytest.raises(OSError):
        helper.lock_file(link)
    assert target.read_text() == 'unchanged'


def test_untrusted_configuration_rejected(monkeypatch):
    class Untrusted:
        def stat(self):
            return type('Info', (), dict(st_uid=0, st_mode=0o100666))()
    with pytest.raises(RuntimeError, match='not writable'):
        helper.trusted(Untrusted())


def test_updater_environment_is_not_inherited(installed, monkeypatch):
    _, _, _, config = installed
    for key in ('BASH_ENV', 'PYTHONPATH', 'CARBONPANEL_REEXECED', 'http_proxy'):
        monkeypatch.setenv(key, '/tmp/untrusted')
    environment = helper.job_environment(config)
    assert not {'BASH_ENV', 'PYTHONPATH', 'CARBONPANEL_REEXECED', 'http_proxy'} & environment.keys()
    assert environment['CARBONPANEL_LOCK_HELD'] == 'true'
    assert '127.0.0.1' in environment['no_proxy']


def test_logs_are_bounded(installed):
    _, _, runtime, _ = installed
    (runtime / 'updater.log').write_text(''.join(f'line {i}\n' for i in range(500)))
    lines = helper.logs().splitlines()
    assert len(lines) == 150
    assert lines[0] == 'line 350' and lines[-1] == 'line 499'


@pytest.mark.parametrize('args', [[], ['install'], ['update', '--ref', 'other'], ['logs', '/etc/passwd']])
def test_helper_cli_rejects_extra_or_unrecognized_arguments(args):
    result = subprocess.run([sys.executable, '-I', str(SCRIPT), *args],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert 'Expected exactly one of' in result.stderr


# Real fork/session/pipe coverage: the trigger process exits while its detached
# supervisor keeps running. These do not use sudo, real services, or root paths.
@pytest.mark.parametrize('exit_code', [0, 7])
@pytest.mark.parametrize('action', ['check', 'update'])
def test_detached_job_survives_trigger_exit_and_preserves_correlation(installed, exit_code, action):
    root, shared, runtime, config = installed
    control = root / 'fake-control'
    control.write_text('''#!/bin/bash
set -eu
printf 'updater started\\n'
printf 'stderr captured\\n' >&2
while [[ ! -f "$CARBONPANEL_INSTALL_ROOT/release" ]]; do sleep 0.02; done
exit ''' + str(exit_code) + '\n')
    harness = root / 'harness.py'
    harness.write_text(
        'import importlib.util,json,sys\nfrom pathlib import Path\n'
        'spec=importlib.util.spec_from_file_location("updater",sys.argv[1])\n'
        'h=importlib.util.module_from_spec(spec); spec.loader.exec_module(h)\n'
        'root=Path(sys.argv[2]); h.RUNTIME=root/"run"\n'
        'config=json.loads(sys.argv[3])\n'
        'print(json.dumps(h.launch(config,root/"fake-control",root/"shared",sys.argv[4])))\n'
    )
    try:
        result = subprocess.run([sys.executable, str(harness), str(SCRIPT), str(root),
                                 json.dumps(config), action], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        ack = json.loads(result.stdout)
        assert ack['kind'] == action
        prefix = 'operation' if action == 'update' else 'check'
        assert helper.running_status(shared)['operation_id'] == ack['operation_id']
        queued = helper.read_json(shared / 'update-status.json')
        assert queued[prefix + '_id'] == ack['operation_id']
        assert queued[prefix + '_state'] == 'queued'
        with pytest.raises(RuntimeError, match='already running'):
            helper.launch(config, control, shared, 'check' if action == 'update' else 'update')
        # The supervisor holds the CLI lock, but it was not inherited by the
        # fake installer (or, in production, the newly started backend).
        descriptor = os.open(shared / 'update.lock', os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)
    finally:
        (root / 'release').touch()
        deadline = time.monotonic() + 5
        while helper.running_status(shared)['running'] and time.monotonic() < deadline:
            time.sleep(0.02)
    assert not helper.running_status(shared)['running']
    state = helper.read_json(shared / 'update-status.json')
    assert state[prefix + '_state'] == ('failed' if exit_code else 'succeeded')
    if action == 'update':
        assert state['restart_pending'] is False
    output = helper.logs()
    assert 'updater started' in output and 'stderr captured' in output
    if exit_code:
        assert '7' in state['error']


def test_reboot_without_runtime_record_finalizes_abandoned_operation(installed):
    _, shared, _, _ = installed
    operation_id = helper.queue_operation(shared, 'update')
    assert helper.running_status(shared)['running'] is False
    status = helper.read_json(shared / 'update-status.json')
    assert status['operation_id'] == operation_id
    assert status['operation_state'] == 'failed'
    assert 'stopped' in status['error']
