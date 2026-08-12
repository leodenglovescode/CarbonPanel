import json

import pytest

from app.api.webhooks import WebhookResponse
from app.core.crypto import decrypt
from app.models.types import EncryptedString
from app.models.webhook import Webhook
from app.services import webhook_service


def _channel(**overrides) -> Webhook:
    values = {
        "id": "channel-id",
        "label": "Alerts",
        "kind": "webhook",
        "url": "https://hooks.example.test/carbonpanel",
        "enabled": True,
        "events": "alert.cpu,alert.ram,alert.disk",
    }
    values.update(overrides)
    return Webhook(**values)


def test_notification_credentials_are_encrypted_at_the_orm_boundary() -> None:
    column = EncryptedString()
    ciphertext = column.process_bind_param("super-secret", None)

    assert ciphertext != "super-secret"
    assert decrypt(ciphertext) == "super-secret"
    assert column.process_result_value(ciphertext, None) == "super-secret"


def test_notification_response_never_returns_credentials() -> None:
    channel = _channel(
        kind="ntfy",
        url="http://127.0.0.1:8080",
        topic="carbonpanel",
        token="secret-token",
    )

    payload = WebhookResponse.from_orm_obj(channel).model_dump()

    assert payload["has_token"] is True
    assert "token" not in payload
    assert "smtp_username" not in payload
    assert "smtp_password" not in payload
    assert "secret-token" not in json.dumps(payload)


def test_ntfy_accepts_local_server_but_generic_webhook_keeps_loopback_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        webhook_service,
        "_real_getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", args[1] or 0))],
    )

    normalized = webhook_service.validate_channel_config(
        kind="ntfy",
        url="http://127.0.0.1:8080/",
        topic="carbonpanel-alerts",
    )
    assert normalized == "http://127.0.0.1:8080"
    assert webhook_service._validate_http_host(normalized, allow_loopback=True)[1] == "127.0.0.1"

    with pytest.raises(ValueError, match="blocked address"):
        webhook_service._validate_http_host(
            "http://127.0.0.1:8080/hook",
            allow_loopback=False,
        )


def test_ntfy_request_uses_root_json_api_and_bearer_token() -> None:
    channel = _channel(
        kind="ntfy",
        url="http://127.0.0.1:8080",
        topic="carbonpanel-alerts",
        token="tk_example",
    )

    request = webhook_service._request_for(
        channel,
        "alert.cpu",
        {
            "metric": "cpu",
            "label": "CPU usage",
            "value": 94,
            "threshold": 90,
            "message": "CPU is hot",
            "severity": "critical",
            "unit": "%",
        },
    )
    body = json.loads(request.data)

    assert request.full_url == "http://127.0.0.1:8080"
    assert request.headers["Authorization"] == "Bearer tk_example"
    assert body == {
        "topic": "carbonpanel-alerts",
        "title": "[CRITICAL] CarbonPanel CPU usage alert",
        "message": "CPU is hot",
        "priority": 5,
        "tags": ["rotating_light", "carbonpanel"],
    }


def test_smtp_authentication_requires_encrypted_transport() -> None:
    with pytest.raises(ValueError, match="requires STARTTLS or SSL/TLS"):
        webhook_service.validate_channel_config(
            kind="email",
            smtp_host="mail.internal",
            smtp_port=25,
            smtp_security="none",
            smtp_username="carbonpanel",
            smtp_password="secret",
            email_from="carbonpanel@example.com",
            email_to="admin@example.com",
        )


def test_email_delivery_uses_starttls_login_and_plain_text_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, context):
            calls.append("starttls")

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            calls.append(("message", message))

    monkeypatch.setattr(
        webhook_service,
        "_resolve_target",
        lambda *args, **kwargs: ("mail.local", "10.0.0.2"),
    )
    monkeypatch.setattr(webhook_service.smtplib, "SMTP", FakeSMTP)

    channel = _channel(
        kind="email",
        url="",
        smtp_host="mail.local",
        smtp_port=587,
        smtp_security="starttls",
        smtp_username="carbonpanel",
        smtp_password="secret",
        email_from="carbonpanel@example.com",
        email_to="admin@example.com",
    )
    assert webhook_service._deliver_email(channel, "test", {}) == 250

    assert ("login", "carbonpanel", "secret") in calls
    sent = next(call[1] for call in calls if isinstance(call, tuple) and call[0] == "message")
    assert sent["Subject"] == "CarbonPanel test"
    assert sent["To"] == "admin@example.com"
    assert "Notification delivery is working." in sent.get_content()


def test_alert_preferences_choose_sensitive_threshold_duration_and_disk_scope() -> None:
    class Row:
        def __init__(self, prefs_json: str):
            self.prefs_json = prefs_json

    config = __import__(
        "app.services.alert_service",
        fromlist=["_config_from_preferences"],
    )._config_from_preferences(
        [
            Row(
                '{"alerts":{"cpu":90,"ram":0,"disk":85,"gpuTemp":80,"diskScope":"physical","durations":{"cpu":20},"severities":{"gpuTemp":"critical"}}}'
            ),
            Row(
                '{"alerts":{"cpu":75,"ram":80,"disk":0,"networkRx":12.5,"diskScope":"all","durations":{"cpu":15,"networkRx":30},"severities":{"networkRx":"info"}}}'
            ),
        ]
    )

    assert config.cpu == 75
    assert config.ram == 80
    assert config.disk == 85
    assert config.gpu_temp == 80
    assert config.network_rx == 12.5
    assert config.severity("gpuTemp") == "critical"
    assert config.severity("networkRx") == "info"
    assert config.duration("cpu") == 15
    assert config.duration("networkRx") == 30
    assert config.duration("disk") == 10
    assert config.disk_scope == "all"


@pytest.mark.asyncio
async def test_server_alert_evaluator_delivers_once_until_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from app.services.alert_service import AlertConfig, AlertEvaluator

    evaluator = AlertEvaluator()

    async def load_config():
        return AlertConfig(cpu=80, durations={"cpu": 0})

    class Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            return False

    deliveries: list[str] = []

    async def fire_event(db, event, payload):
        deliveries.append(event)
        return [webhook_service.DeliveryResult("channel-id", True, status=200)]

    monkeypatch.setattr(evaluator, "_load_config", load_config)
    monkeypatch.setattr("app.services.alert_service.AsyncSessionLocal", Session)
    monkeypatch.setattr(webhook_service, "fire_event", fire_event)

    high = SimpleNamespace(
        cpu=SimpleNamespace(aggregate=90),
        memory=SimpleNamespace(percent=20),
        disks=[],
        gpu=SimpleNamespace(available=False, devices=[]),
        network=[],
    )
    recovered = SimpleNamespace(
        cpu=SimpleNamespace(aggregate=70),
        memory=SimpleNamespace(percent=20),
        disks=[],
        gpu=SimpleNamespace(available=False, devices=[]),
        network=[],
    )

    await evaluator.check(high)
    await evaluator.check(high)
    assert deliveries == ["alert.cpu"]

    await evaluator.check(recovered)
    evaluator._last_attempt.clear()
    await evaluator.check(high)
    assert deliveries == ["alert.cpu", "alert.cpu"]


@pytest.mark.asyncio
async def test_server_alert_requires_one_continuous_breach_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from app.services.alert_service import AlertConfig, AlertEvaluator

    evaluator = AlertEvaluator()
    now = 100.0

    async def load_config():
        return AlertConfig(cpu=80, durations={"cpu": 10})

    class Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            return False

    deliveries: list[dict] = []

    async def fire_event(db, event, payload):
        deliveries.append(payload)
        return [webhook_service.DeliveryResult("channel-id", True, status=200)]

    monkeypatch.setattr(evaluator, "_load_config", load_config)
    monkeypatch.setattr("app.services.alert_service.AsyncSessionLocal", Session)
    monkeypatch.setattr("app.services.alert_service.time.monotonic", lambda: now)
    monkeypatch.setattr(webhook_service, "fire_event", fire_event)

    def snapshot(cpu: float):
        return SimpleNamespace(
            cpu=SimpleNamespace(aggregate=cpu),
            memory=SimpleNamespace(percent=20),
            disks=[],
            gpu=SimpleNamespace(available=False, devices=[]),
            network=[],
        )

    await evaluator.check(snapshot(95))
    now = 102.0
    await evaluator.check(snapshot(40))
    now = 103.0
    await evaluator.check(snapshot(95))
    now = 112.9
    await evaluator.check(snapshot(95))
    assert deliveries == []

    now = 113.0
    await evaluator.check(snapshot(95))
    await evaluator.check(snapshot(95))

    assert len(deliveries) == 1
    assert deliveries[0]["duration_seconds"] == 10
    assert deliveries[0]["message"].endswith("for at least 10 seconds.")


def test_expanded_notification_event_catalog() -> None:
    assert webhook_service.EVENT_NAMES == (
        "alert.cpu",
        "alert.ram",
        "alert.disk",
        "alert.gpu",
        "alert.gpu_temperature",
        "alert.network_rx",
        "alert.network_tx",
    )


@pytest.mark.asyncio
async def test_gpu_and_network_alerts_preserve_rule_severity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from app.services.alert_service import AlertConfig, AlertEvaluator

    evaluator = AlertEvaluator()
    config = AlertConfig(
        gpu_usage=80,
        gpu_temp=75,
        network_rx=10,
        network_tx=20,
        severities={
            "gpuUsage": "warning",
            "gpuTemp": "critical",
            "networkRx": "info",
            "networkTx": "critical",
        },
        durations={
            "gpuUsage": 0,
            "gpuTemp": 0,
            "networkRx": 0,
            "networkTx": 0,
        },
    )

    async def load_config():
        return config

    class Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *args):
            return False

    deliveries: list[tuple[str, dict]] = []

    async def fire_event(db, event, payload):
        deliveries.append((event, payload))
        return [webhook_service.DeliveryResult("channel-id", True, status=200)]

    monkeypatch.setattr(evaluator, "_load_config", load_config)
    monkeypatch.setattr("app.services.alert_service.AsyncSessionLocal", Session)
    monkeypatch.setattr(webhook_service, "fire_event", fire_event)

    snapshot = SimpleNamespace(
        cpu=SimpleNamespace(aggregate=10),
        memory=SimpleNamespace(percent=20),
        disks=[],
        gpu=SimpleNamespace(
            available=True,
            devices=[
                SimpleNamespace(
                    index=0,
                    name="Test GPU",
                    utilization_percent=90,
                    temperature_c=85,
                )
            ],
        ),
        network=[SimpleNamespace(interface="eth0", rx_mb_s=12.5, tx_mb_s=25.5)],
    )

    await evaluator.check(snapshot)

    assert [event for event, _ in deliveries] == [
        "alert.gpu",
        "alert.gpu_temperature",
        "alert.network_rx",
        "alert.network_tx",
    ]
    assert [payload["severity"] for _, payload in deliveries] == [
        "warning",
        "critical",
        "info",
        "critical",
    ]
    assert deliveries[2][1]["unit"] == "MB/s"
    assert deliveries[1][1]["unit"] == "°C"
