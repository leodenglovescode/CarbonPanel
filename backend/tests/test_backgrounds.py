import asyncio
import io
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image

from app.api.background_images import router
from app.core.dependencies import get_current_user
from app.services import settings_store


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("CARBONPANEL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings_store, "SETTINGS_FILE", tmp_path / "settings.json")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)

    def request(method, path, **kwargs):
        async def run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://panel.test"
            ) as client:
                return await client.request(method, "/settings/background-image" + path, **kwargs)

        return asyncio.run(run())

    return request, app


def photo():
    buffer = io.BytesIO()
    Image.new("RGB", (120, 240), "#447755").save(buffer, "PNG")
    return buffer.getvalue()


def test_apply_copy_and_discover_in_new_session(api):
    request, app = api
    response = request(
        "POST",
        "/apply?targets=android-app&targets=android-login&targets=app&targets=login",
        files={"file": ("crop.png", photo(), "image/png")},
    )
    assert response.status_code == 200
    config = response.json()
    assert all(row["type"] == "image" and row["version"] > 0 for row in config["targets"].values())
    # Public metadata allows first-time login rendering; private app images still require auth.
    app.dependency_overrides.clear()
    assert request("GET", "/config").json()["targets"]["login"]["version"] > 0
    assert request("GET", "/login").status_code == 200
    assert request("GET", "/android-login").status_code == 200
    assert request("GET", "/app").status_code == 401
    assert request("GET", "/android-app").status_code == 401
    assert request("PUT", "/config", json={"surfaceTransparency": 50}).status_code == 401


def test_display_settings_persist_and_images_reset(api):
    request, _ = api
    request("POST", "/app", files={"file": ("image.png", photo(), "image/png")})
    app_bg = request("GET", "/config").json()["targets"]["app"]
    app_bg.update(blur=4, overlay=20)
    assert (
        request(
            "PUT", "/config", json={"targets": {"app": app_bg}, "surfaceTransparency": 55}
        ).status_code
        == 200
    )
    assert (
        request(
            "POST",
            "/copy",
            json={"source": "app", "targets": ["login", "android-app", "android-login"]},
        ).status_code
        == 200
    )
    config = request("GET", "/config").json()
    assert config["surfaceTransparency"] == 55
    assert config["targets"]["android-app"]["blur"] == 4
    saved = request("GET", "/android-login")
    assert Image.open(io.BytesIO(saved.content)).size == (120, 240)
    request("DELETE", "/android-app")
    config = request("GET", "/config").json()
    assert config["targets"]["android-app"]["version"] == 0
    assert config["targets"]["android-app"]["type"] == "color"
    assert config["targets"]["app"]["version"] > 0


def test_validation_and_missing_copy(api):
    request, _ = api
    assert request("PUT", "/config", json={"surfaceTransparency": 101}).status_code == 422
    assert (
        request(
            "PUT", "/config", json={"targets": {"app": {"gradientStart": "url(evil)"}}}
        ).status_code
        == 422
    )
    assert (
        request("POST", "/apply?targets=other", files={"file": ("image.png", photo())}).status_code
        == 422
    )
    assert (
        request(
            "POST", "/apply?targets=app", files={"file": ("bad.jpg", b"not an image")}
        ).status_code
        == 400
    )
    request("PUT", "/config", json={"targets": {"app": {"type": "image"}}})
    assert request("POST", "/copy", json={"source": "app", "targets": ["login"]}).status_code == 404
