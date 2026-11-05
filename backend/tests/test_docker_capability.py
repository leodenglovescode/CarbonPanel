"""Navigation uses installation, never daemon state or container count."""
import pytest

from app.schemas.metrics import SystemMetrics
from app.services.metrics import system


@pytest.mark.parametrize('binary, expected', [(None, False), ('/usr/bin/docker', True)])
def test_host_detection_reports_docker_installation(monkeypatch, binary, expected):
    monkeypatch.setattr(system.shutil, 'which', lambda name: binary if name == 'docker' else None)
    monkeypatch.setattr(system.psutil, 'boot_time', lambda: 1000.0)
    boot_time, installed = system._host_info()
    assert boot_time == 1000.0
    assert installed is expected


def test_uncollected_system_snapshot_does_not_claim_docker_is_missing():
    snapshot = SystemMetrics(hostname='', uptime_seconds=0, boot_time_ts=0)
    assert snapshot.docker_installed is None
