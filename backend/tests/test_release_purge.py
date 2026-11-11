"""Exercise destructive cleanup against isolated installation trees only."""
import importlib.util
import fcntl
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
spec = importlib.util.spec_from_file_location('release_purge', SCRIPTS / 'purge-releases.py')
purge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = purge
spec.loader.exec_module(purge)


def release(root, number, *, build=False):
    path = root / 'releases' / f'20261111{number:06d}-master'
    path.mkdir(parents=True)
    metadata = {
        'repo_url': 'https://github.com/leodenglovescode/CarbonPanel',
        'version': 'master', 'commit': 'a' * 40,
        'installed_at': '2026-11-11T00:00:00Z', 'source_type': 'branch',
    }
    marker = '.carbonpanel-build.json' if build else '.carbonpanel-release.json'
    (path / marker).write_text(json.dumps(metadata))
    (path / 'payload').write_text('release files')
    return path


@pytest.fixture
def installation(tmp_path):
    root = tmp_path / 'install with spaces'
    current = release(root, 5)
    previous = release(root, 1)  # Age/order must never override protection.
    (root / 'current').symlink_to(current)
    (root / 'previous').symlink_to(previous)
    shared = root / 'shared'
    shared.mkdir()
    (shared / 'panel.db').write_text('user data')
    return root


def test_purge_retains_active_rollback_and_shared_data(installation):
    old = [release(installation, n, build=n == 4) for n in (2, 3, 4)]
    assert purge.purge_releases(installation) == 3
    assert all(not path.exists() for path in old)
    assert (installation / 'current' / 'payload').is_file()
    assert (installation / 'previous' / 'payload').is_file()
    assert (installation / 'shared' / 'panel.db').read_text() == 'user data'
    assert purge.purge_releases(installation) == 0


def test_dry_run_has_no_side_effects(installation, capsys):
    old = release(installation, 2)
    assert purge.purge_releases(installation, dry_run=True) == 1
    assert old.is_dir()
    assert f'Would remove: {old}' in capsys.readouterr().out


@pytest.mark.parametrize('metadata', ['[]', '{}', 'invalid', '{"source_type": []}'])
def test_unrecognized_directories_and_symlinks_are_preserved(installation, tmp_path, metadata):
    unknown = release(installation, 2)
    (unknown / '.carbonpanel-release.json').write_text(metadata)
    arbitrary = installation / 'releases' / 'personal-files'
    arbitrary.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'keep').touch()
    (installation / 'releases' / '20261111000003-master').symlink_to(outside)
    assert purge.purge_releases(installation) == 0
    assert unknown.exists() and arbitrary.exists() and (outside / 'keep').exists()


def test_nested_symlink_does_not_delete_external_data(installation, tmp_path):
    old = release(installation, 2)
    outside = tmp_path / 'external-data'
    outside.mkdir()
    (outside / 'keep').touch()
    (old / 'data').symlink_to(outside)
    purge.purge_releases(installation)
    assert (outside / 'keep').exists()
    assert not old.exists()


@pytest.mark.parametrize('link_name', ['current', 'previous'])
@pytest.mark.parametrize('target', ['outside', 'missing', 'directory'])
def test_invalid_protected_links_refuse_all_deletion(installation, tmp_path, link_name, target):
    old = release(installation, 2)
    link = installation / link_name
    link.unlink()
    if target == 'directory':
        link.mkdir()
    else:
        destination = tmp_path / target
        if target == 'outside':
            destination.mkdir()
        link.symlink_to(destination)
    with pytest.raises((ValueError, OSError)):
        purge.purge_releases(installation)
    assert old.exists()


def test_first_install_needs_no_previous_link(installation):
    (installation / 'previous').unlink()
    assert purge.purge_releases(installation) == 1


def test_symlinked_releases_directory_refuses_deletion(installation):
    releases = installation / 'releases'
    releases.rename(installation / 'elsewhere')
    releases.symlink_to(installation / 'elsewhere')
    with pytest.raises(ValueError, match='real directory'):
        purge.purge_releases(installation)


def test_mounts_abort_before_any_deletion(installation, monkeypatch):
    first = release(installation, 2)
    mounted = release(installation, 3) / 'mounted-data'
    mounted.mkdir()
    monkeypatch.setattr(purge, 'mount_points', lambda: {mounted})
    with pytest.raises(ValueError, match='mounted directory'):
        purge.purge_releases(installation)
    assert first.exists() and mounted.exists()


def test_changed_release_is_not_deleted(installation, monkeypatch):
    old = release(installation, 2)
    original = purge.protected_releases
    calls = 0

    def replace_candidate(root, releases):
        nonlocal calls
        calls += 1
        if calls == 2:
            old.rename(old.with_name('saved'))
            old.symlink_to(installation / 'shared')
        return original(root, releases)

    monkeypatch.setattr(purge, 'protected_releases', replace_candidate)
    with pytest.raises(RuntimeError, match='changed during purge'):
        purge.purge_releases(installation)
    assert (installation / 'shared' / 'panel.db').exists()


@pytest.mark.parametrize('exit_code', [0, 7])
def test_bootstrap_clone_removed_after_updater_exits(tmp_path, exit_code):
    bootstrap = tmp_path / 'bootstrap'
    (bootstrap / 'scripts').mkdir(parents=True)
    (bootstrap / 'scripts' / 'install-carbonpanel.sh').write_text(f'exit {exit_code}\n')
    installer = (SCRIPTS / 'install-carbonpanel.sh').read_text()
    function = re.search(r'^bootstrap_installer\(\) \(\n.*?^\)', installer, re.M | re.S)[0]
    script = function + '\nbootstrap_installer "$1" update master\n'
    result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(bootstrap)],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == exit_code, result.stderr
    assert not bootstrap.exists()


def test_manual_purge_respects_update_lock(tmp_path):
    installer = (SCRIPTS / 'install-carbonpanel.sh').read_text()
    functions = '\n'.join(
        re.search(rf'^{name}\(\) \{{\n.*?^\}}', installer, re.M | re.S)[0]
        for name in ('acquire_update_lock', 'purge_old_releases')
    )
    script = '''
SHARED_DIR="$1"
UPDATE_LOCK_FILE="$1/update.lock"
UPDATE_LOCK_HELD=false
PURGE_DRY_RUN=true
require_root() { :; }
die() { echo "$*" >&2; exit 1; }
cleanup_old_releases() { echo "purge $*"; }
'''
    script += functions + '\npurge_old_releases\n'
    command = ['bash', '-eu', '-c', script, 'test', str(tmp_path)]
    with (tmp_path / 'update.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        assert result.returncode == 1
        assert 'already running' in result.stderr
        assert 'purge --dry-run' not in result.stdout
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert 'purge --dry-run' in result.stdout


def test_cli_reports_invalid_layout_without_deleting(tmp_path):
    old = release(tmp_path, 2)
    result = subprocess.run([sys.executable, str(SCRIPTS / 'purge-releases.py'), str(tmp_path)],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 1
    assert 'Purge failed:' in result.stderr
    assert old.exists()
