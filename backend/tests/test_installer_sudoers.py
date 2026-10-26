"""Exercise the installer's policy without running installation or needing root."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


INSTALLER = Path(__file__).resolve().parents[2] / "scripts/install-carbonpanel.sh"


def _shell_setup() -> str:
    source = INSTALLER.read_text()
    names = ("SERVICE_USER", "UPDATE_CHECK_SERVICE", "UPDATE_SERVICE", "DOCKER_HELPER")
    assignments = [re.search(rf"^{name}=.*$", source, re.M)[0] for name in names]
    functions = [
        re.search(rf"^{name}\(\) \{{\n.*?^\}}", source, re.M | re.S)[0]
        for name in ("sudoers_rules", "write_sudoers")
    ]
    return (
        "set -euo pipefail\n"
        + "\n".join(assignments + functions)
        + "\nwrite_docker_helper() { :; }\n"
    )


def test_policy_passes_installed_visudo(tmp_path):
    visudo = shutil.which("visudo")
    if not visudo:
        pytest.skip("visudo is not installed")
    result = subprocess.run(
        ["bash", "-c", _shell_setup() + "sudoers_rules"],
        check=True, capture_output=True, text=True,
    )
    policy = tmp_path / "policy"
    policy.write_text(result.stdout)
    validation = subprocess.run([visudo, "-cf", str(policy)], capture_output=True, text=True)
    assert validation.returncode == 0, validation.stdout + validation.stderr
    # Guard the least-privilege journal rule and the retained Docker controls.
    assert "--no-pager -n 150 --output=short-iso," in result.stdout
    assert "/usr/local/libexec/carbonpanel-docker" in result.stdout
    assert "*" not in result.stdout
    assert "/usr/bin/docker" not in result.stdout


@pytest.mark.parametrize("valid", [True, False])
def test_policy_replacement_is_validated(tmp_path, valid):
    policy = tmp_path / "policy"
    policy.write_text("existing policy\n")
    script = _shell_setup() + '''
SUDOERS_FILE="$1"
VALIDATION_STATUS="$2"
die() { printf '%s\\n' "$*" >&2; exit 1; }
# Stub ownership for unprivileged test runs; chmod and rename remain real.
chown() { :; }
visudo() {
  [[ "$1" == -cf && "$2" != "$SUDOERS_FILE" ]]
  [[ -s "$2" ]]
  return "$VALIDATION_STATUS"
}
write_sudoers
'''
    result = subprocess.run(
        ["bash", "-c", script, "test", str(policy), "0" if valid else "1"],
        capture_output=True, text=True,
    )
    if valid:
        assert result.returncode == 0, result.stderr
        assert "NOPASSWD:" in policy.read_text()
        assert policy.stat().st_mode & 0o777 == 0o440
    else:
        assert result.returncode != 0
        assert "was not replaced" in result.stderr
        assert policy.read_text() == "existing policy\n"
    assert list(tmp_path.iterdir()) == [policy]


@pytest.fixture
def docker_helper(tmp_path):
    source = INSTALLER.read_text().split("<<'HELPER'\n", 1)[1].split("\nHELPER", 1)[0]
    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        "#!/usr/bin/python3\nimport json, os, sys\n"
        "print(json.dumps({'args': sys.argv[1:], 'env': dict(os.environ)}))\n"
    )
    fake_docker.chmod(0o755)
    helper = tmp_path / "helper"
    helper.write_text(source.replace("/usr/bin/docker", str(fake_docker)))
    return helper


@pytest.mark.parametrize("args", [
    ["start", "abc123"], ["stop", "web-1"], ["restart", "web_1.2"],
    ["stats", "--no-stream", "--format", "{{json .}}", "abc123", "def456"],
    ["ps", "-a", "--format",
     "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.State}}|{{.Ports}}|{{.CreatedAt}}"],
])
def test_docker_helper_accepts_only_fixed_operations(docker_helper, args):
    result = subprocess.run(
        ["bash", str(docker_helper), *args], capture_output=True, text=True,
        env={"DOCKER_HOST": "tcp://untrusted:2375", "DOCKER_CONFIG": "/tmp/untrusted"},
    )
    assert result.returncode == 0, result.stderr
    executed = json.loads(result.stdout)
    assert "DOCKER_HOST" not in executed["env"]
    assert "DOCKER_CONFIG" not in executed["env"]
    assert executed["env"]["HOME"] == "/root"
    if args[0] in ("start", "stop", "restart"):
        assert executed["args"] == [args[0], "--", args[1]]
    elif args[0] == "stats":
        assert executed["args"] == [*args[:4], "--", *args[4:]]
    else:
        assert executed["args"] == args


@pytest.mark.parametrize("args", [
    [], ["run", "alpine"], ["exec", "web", "sh"],
    ["start", "--help"], ["start", "web", "other"],
    ["start", "--checkpoint-dir=/tmp/evil"], ["start", "web;id"],
    ["restart", "web other"], ["stop", "a" * 129], ["stop", "网页"],
    ["stats", "--no-stream", "--format", "{{json .}}"],
    ["stats", "--no-stream", "--format", "{{json .}}", "--all"],
    ["stats", "--no-stream", "--format", "{{json .}}", "web", "--all"],
    ["ps", "-a", "--format", "{{json .}}"],
    ["ps", "-a", "--format", "x", "--help"],
])
def test_docker_helper_rejects_options_and_arbitrary_commands(docker_helper, args):
    result = subprocess.run(["bash", str(docker_helper), *args], capture_output=True, text=True)
    assert result.returncode == 2
    assert "Unsupported CarbonPanel Docker request" in result.stderr
    assert not result.stdout


@pytest.mark.parametrize("valid", [True, False])
def test_documented_repair_command(tmp_path, valid):
    docs = INSTALLER.parents[1] / "docs/SUDOERS.md"
    command = docs.read_text().split("```bash\n", 1)[1].split("\n```", 1)[0]
    policy = tmp_path / "policy"
    original = (
        "carbonpanel ALL=(root) NOPASSWD: /usr/bin/journalctl -u "
        "carbonpanel-update.service --no-pager -n * --output=short-iso, "
        "/usr/bin/docker start *\n"
    )
    if not valid:
        original += "carbonpanel ALL=(root) NOPASSWD: /usr/bin/docker start web*\n"
    policy.write_text(original)
    policy.chmod(0o440)
    command = command.removeprefix("sudo ").replace(
        "/etc/sudoers.d/carbonpanel-updater", str(policy)
    )
    if not shutil.which("visudo"):
        pytest.skip("visudo is not installed")
    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)
    if not valid:
        assert result.returncode != 0
        assert policy.read_text() == original
        assert list(tmp_path.iterdir()) == [policy]
        return
    assert result.returncode == 0, result.stderr
    assert "-n 150 --output=short-iso" in policy.read_text()
    assert policy.stat().st_mode & 0o777 == 0o440
    backups = list(tmp_path.glob("policy.backup.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == original
    assert len(list(tmp_path.iterdir())) == 2


def test_release_policy_snapshot_repairs_journal_and_restores(tmp_path):
    if not shutil.which("visudo"):
        pytest.skip("visudo is not installed")
    policy = tmp_path / "policy"
    policy.write_text(
        "carbonpanel ALL=(root) NOPASSWD: /usr/bin/journalctl "
        "--no-pager -n * --output=short-iso, /usr/bin/docker start *\n"
    )
    release = tmp_path / "release"
    release.mkdir()
    source = INSTALLER.read_text()
    functions = "\n".join(
        re.search(rf"^{name}\(\) \{{\n.*?^\}}", source, re.M | re.S)[0]
        for name in ("save_release_sudoers", "restore_release_sudoers")
    )
    script = "set -euo pipefail\n" + functions + '''
SUDOERS_FILE="$1"
chown() { :; }
die() { echo "$*" >&2; exit 1; }
save_release_sudoers "$2"
echo 'replacement policy' > "$SUDOERS_FILE"
restore_release_sudoers "$2"
'''
    result = subprocess.run(
        ["bash", "-c", script, "test", str(policy), str(release)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "-n 150 --output=short-iso" in policy.read_text()
    assert "/usr/bin/docker start *" in policy.read_text()
    assert policy.stat().st_mode & 0o777 == 0o440
