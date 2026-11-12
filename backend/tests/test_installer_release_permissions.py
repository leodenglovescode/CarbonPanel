"""Releases remain readable when the updater inherits a private umask."""
import re
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install-carbonpanel.sh'


def function(name):
    return re.search(rf'^{name}\(\) \{{\n.*?^\}}', INSTALLER.read_text(), re.M | re.S)[0]


@pytest.mark.parametrize('mask', ['077', '027'])
def test_clone_and_build_are_readable_without_relaxing_parent_umask(tmp_path, mask):
    repository = tmp_path / 'source'
    repository.mkdir()
    (repository / 'backend').mkdir()
    (repository / 'backend' / 'app.py').write_text('# application\n')
    executable = repository / 'start.sh'
    executable.write_text('#!/bin/sh\nexit 0\n')
    executable.chmod(0o755)
    for args in (
        ['init', '-b', 'master', str(repository)],
        ['-C', str(repository), 'add', '.'],
        ['-C', str(repository), '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
         'commit', '-m', 'Fixture'],
    ):
        subprocess.run(['git', *args], check=True, capture_output=True, text=True)
    releases = tmp_path / 'releases'
    releases.mkdir()
    script = '\n'.join(function(name) for name in ('clone_release', 'build_step'))
    script += '''
REPO_URL="$1/source"
RELEASES_DIR="$1/releases"
BUILD_STEP_CURRENT=0
BUILD_STEP_TOTAL=1
set_update_progress() { :; }
log() { :; }
die() { echo "$*" >&2; exit 1; }
umask "$2"
release="$(clone_release master test-release)"
artifact() {
  test -z "${CARBONPANEL_LOCK_HELD:-}"
  mkdir -p "$release/backend/.venv/lib" "$release/frontend/dist/assets"
  printf package > "$release/backend/.venv/lib/dependency.py"
  printf asset > "$release/frontend/dist/assets/app.js"
}
export CARBONPANEL_LOCK_HELD=true
build_step 50 fixture artifact
# Release permissions must not weaken the invoking shell's private file policy.
printf private > "$1/private-config"
'''
    result = subprocess.run(['bash', '-eu', '-c', script, 'test', str(tmp_path), mask],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    release = releases / 'test-release'
    for directory in (release, *(p for p in release.rglob('*') if p.is_dir())):
        assert directory.stat().st_mode & 0o005 == 0o005, directory
    for relative in ('backend/app.py', 'backend/.venv/lib/dependency.py',
                     'frontend/dist/assets/app.js', 'start.sh'):
        path = release / relative
        assert path.stat().st_mode & 0o004, path
        assert not path.stat().st_mode & 0o022, path
    assert (release / 'start.sh').stat().st_mode & 0o001
    expected = 0o600 if mask == '077' else 0o640
    assert (tmp_path / 'private-config').stat().st_mode & 0o777 == expected
