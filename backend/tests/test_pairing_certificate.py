"""Certificate binding must work for the unprivileged installed backend."""
import re
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api import pairing

INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install-carbonpanel.sh'


@pytest.mark.parametrize('reuse', [True, False])
def test_tls_directory_is_accessible_to_backend_group(tmp_path, reuse):
    function = re.search(r'^ensure_tls_cert\(\) \{\n.*?^\}',
                         INSTALLER.read_text(), re.M | re.S)[0]
    tls = tmp_path / 'tls'
    tls.mkdir()
    cert, key = tls / 'cert.pem', tls / 'key.pem'
    if reuse:
        cert.write_text('existing public certificate')
        key.write_text('existing private key')
        key.chmod(0o600)
    script = '''set -eu
TLS_DIR="$1/tls"
TLS_CERT="$TLS_DIR/cert.pem"
TLS_KEY="$TLS_DIR/key.pem"
SERVICE_GROUP=panel-test
chown() { printf 'ownership %s\\n' "$*"; }
openssl() {
  if [[ "$1" == x509 ]]; then return 0; fi
  printf 'new public certificate' > "$TLS_CERT"
  printf 'new private key' > "$TLS_KEY"
}
run_silent() { "$@"; }
hostname() { if [[ "${1:-}" == -I ]]; then echo 192.0.2.1; else echo panel; fi; }
die() { echo "$*" >&2; exit 1; }
'''
    result = subprocess.run(['bash', '-c', script + function + '\nensure_tls_cert\n',
                             'test', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert f'ownership root:panel-test {tls}' in result.stdout.splitlines()
    assert tls.stat().st_mode & 0o777 == 0o750
    assert key.stat().st_mode & 0o777 == 0o600
    if reuse:
        assert cert.read_text() == 'existing public certificate'
        assert key.read_text() == 'existing private key'
    else:
        assert cert.stat().st_mode & 0o777 == 0o644
        assert f'ownership root:root {key} {cert}' in result.stdout.splitlines()


def test_unreadable_certificate_explains_configuration_problem(monkeypatch):
    monkeypatch.setattr(pairing.settings, 'tls_cert_file', '/example/cert.pem')

    def denied(_):
        raise PermissionError('directory is not traversable')

    monkeypatch.setattr(Path, 'read_bytes', denied)
    with pytest.raises(HTTPException) as error:
        pairing._certificate_binding()
    assert error.value.status_code == 503
    assert 'backend user' in error.value.detail


def test_public_tls_without_configured_pin_is_supported(monkeypatch):
    monkeypatch.setattr(pairing.settings, 'tls_cert_file', None)
    assert pairing._certificate_binding() == (None, set())


@pytest.mark.asyncio
async def test_broken_certificate_does_not_issue_pairing_code(monkeypatch):
    from types import SimpleNamespace

    from starlette.requests import Request

    endpoint = 'https://192.0.2.1:8787'
    monkeypatch.setattr(pairing, '_discover', lambda _: [{'url': endpoint}])
    monkeypatch.setattr(pairing, 'verify_step_up', lambda *args: None)
    monkeypatch.setattr(pairing.brute_force, 'is_banned', lambda *args: False)
    monkeypatch.setattr(pairing.brute_force, 'record_success', lambda *args: None)

    def unavailable():
        raise HTTPException(503, 'Certificate unreadable')

    monkeypatch.setattr(pairing, '_certificate_binding', unavailable)
    monkeypatch.setattr(pairing.pairing, 'generate',
                        lambda *args: pytest.fail('Issued a code without certificate binding'))
    request = Request({'type': 'http', 'headers': []})
    with pytest.raises(HTTPException) as error:
        await pairing.start_pairing(
            pairing.StartRequest(current_password='example', endpoints=[endpoint]),
            request, SimpleNamespace(id='user', username='admin'),
        )
    assert error.value.status_code == 503
