import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import update_runtime


def _configure_paths(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    shared = root / "shared"
    shared.mkdir()
    current = root / "current"
    current.mkdir()
    (current / ".carbonpanel-release.json").write_text(
        json.dumps(
            {
                "version": "master",
                "commit": "installed-commit",
                "source_type": "branch",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(update_runtime, "INSTALL_ROOT", root)
    monkeypatch.setattr(update_runtime, "SHARED_DIR", shared)
    monkeypatch.setattr(
        update_runtime,
        "CURRENT_METADATA_PATH",
        current / ".carbonpanel-release.json",
    )
    monkeypatch.setattr(
        update_runtime,
        "UPDATE_STATUS_PATH",
        shared / "update-status.json",
    )


def test_oneshot_activating_counts_as_in_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        update_runtime.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="activating\n",
            stderr="",
            returncode=3,
        ),
    )

    assert update_runtime._service_is_active(update_runtime.UPDATE_SERVICE)


def test_trigger_check_creates_correlated_queued_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(update_runtime, "_service_unit_exists", lambda _: True)
    monkeypatch.setattr(update_runtime, "_run_systemctl_start", lambda _: None)

    check_id = update_runtime.trigger_update_check()
    status = json.loads(update_runtime.UPDATE_STATUS_PATH.read_text(encoding="utf-8"))

    assert status["check_id"] == check_id
    assert status["check_state"] == "queued"
    assert status["status"] == "checking"


def test_trigger_failure_is_recorded_for_the_same_operation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(update_runtime, "_service_unit_exists", lambda _: True)

    def fail_start(_: str) -> None:
        raise RuntimeError("systemd refused the job")

    monkeypatch.setattr(update_runtime, "_run_systemctl_start", fail_start)

    with pytest.raises(RuntimeError, match="refused"):
        update_runtime.trigger_update_install()

    status = update_runtime.get_system_version_status()
    assert status["operation_state"] == "failed"
    assert status["status"] == "update_failed"
    assert status["error"] == "systemd refused the job"
    assert status["restart_pending"] is False
    assert status["restart_performed"] is False


def test_recent_queued_operation_covers_systemd_activation_gap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(update_runtime, "_service_is_active", lambda _: False)

    update_runtime._begin_operation("update")

    assert update_runtime.is_update_in_progress()


@pytest.mark.parametrize(('action', 'trigger'), [
    ('check', update_runtime.trigger_update_check),
    ('update', update_runtime.trigger_update_install),
])
def test_sysv_trigger_uses_supervisor_operation_id(monkeypatch, action, trigger):
    monkeypatch.setenv('CARBONPANEL_INIT_SYSTEM', 'sysv')
    monkeypatch.setattr(update_runtime, '_sysv_helper_available', lambda: True)
    monkeypatch.setattr(update_runtime, '_begin_operation',
                        lambda _: pytest.fail('SysV queue is owned by the root supervisor'))
    calls = []
    def helper(request):
        calls.append(request)
        return json.dumps({'operation_id': 'queued-job', 'kind': action, 'running': True})
    monkeypatch.setattr(update_runtime, '_sysv_helper_output', helper)
    monkeypatch.setattr(update_runtime.subprocess, 'run',
                        lambda *a, **kw: pytest.fail('systemctl invoked on SysV'))
    assert trigger() == 'queued-job'
    assert calls == [action]


@pytest.mark.parametrize(('kind', 'checking', 'updating'), [
    ('check', True, False), ('update', False, True), ('external', True, True),
])
def test_sysv_progress_uses_live_supervisor_lock(monkeypatch, kind, checking, updating):
    monkeypatch.setenv('CARBONPANEL_INIT_SYSTEM', 'sysv')
    monkeypatch.setattr(update_runtime, '_sysv_status',
                        lambda: {'running': True, 'kind': kind})
    monkeypatch.setattr(update_runtime, '_queued_operation_is_recent', lambda *a: False)
    assert update_runtime.is_check_in_progress() is checking
    assert update_runtime.is_update_in_progress() is updating


def test_sysv_timeout_recovers_acknowledged_job(monkeypatch):
    monkeypatch.setenv('CARBONPANEL_INIT_SYSTEM', 'sysv')
    monkeypatch.setattr(update_runtime, '_sysv_helper_available', lambda: True)
    def timeout(_):
        raise RuntimeError('acknowledgement timed out')
    monkeypatch.setattr(update_runtime, '_sysv_helper_output', timeout)
    monkeypatch.setattr(update_runtime, '_sysv_status', lambda: {
        'running': True, 'kind': 'update', 'operation_id': 'still-running',
    })
    assert update_runtime.trigger_update_install() == 'still-running'


def test_sysv_logs_are_read_through_fixed_helper(monkeypatch):
    calls = []
    def helper(action):
        calls.append(action)
        return 'first line\n\nlast line\n'
    monkeypatch.setattr(update_runtime, '_sysv_helper_output', helper)
    assert update_runtime.sysv_update_logs() == ['first line', 'last line']
    assert calls == ['logs']


def test_sysv_status_errors_are_visible_and_disable_update_button(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setenv('CARBONPANEL_INIT_SYSTEM', 'sysv')
    monkeypatch.setattr(update_runtime, '_sysv_helper_available', lambda: True)
    monkeypatch.setattr(update_runtime, '_sysv_status',
                        lambda: {'error': 'sudo rule is missing'})
    status = update_runtime.get_system_version_status()
    assert status['browser_updates_available'] is False
    assert status['error'] == 'sudo rule is missing'


def test_sysv_version_status_reads_supervisor_once(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setenv('CARBONPANEL_INIT_SYSTEM', 'sysv')
    monkeypatch.setattr(update_runtime, '_sysv_helper_available', lambda: True)
    calls = []
    def state():
        calls.append(True)
        return {'running': True, 'kind': 'update'}
    monkeypatch.setattr(update_runtime, '_sysv_status', state)
    status = update_runtime.get_system_version_status()
    assert status['browser_updates_available'] is True
    assert status['update_in_progress'] is True
    assert status['check_in_progress'] is False
    assert calls == [True]


def test_sysv_subprocess_captures_errors_and_uses_fixed_command(monkeypatch):
    import asyncio
    captured = []
    async def communicate():
        return b'', b'Permission denied by sudo'
    async def spawn(*args, **kwargs):
        captured.append((args, kwargs))
        return SimpleNamespace(returncode=1, communicate=communicate)
    monkeypatch.setattr(update_runtime.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    with pytest.raises(RuntimeError, match='Permission denied by sudo'):
        asyncio.run(update_runtime._sysv_helper_output_async('update'))
    args, options = captured[0]
    assert args == ('/usr/bin/sudo', '-n', str(update_runtime.SYSV_HELPER), 'update')
    assert options['stdout'] == asyncio.subprocess.PIPE
    assert options['stderr'] == asyncio.subprocess.PIPE
