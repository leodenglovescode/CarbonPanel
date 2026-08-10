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
