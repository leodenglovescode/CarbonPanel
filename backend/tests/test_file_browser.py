import asyncio
import os
from types import SimpleNamespace

import httpx
from fastapi import FastAPI

from app.api.files import router
from app.core.dependencies import get_current_user
from app.services import file_browser as browser


def client_app(auth=True):
    app = FastAPI()
    app.include_router(router)
    if auth:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    return app


def request(method, path, auth=True, **kwargs):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=client_app(auth)), base_url="https://panel.test"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run())


def test_authenticated_read_only_surface(tmp_path):
    (tmp_path / "hello.txt").write_text("hello")
    assert request("GET", "/files", auth=False).status_code == 401
    assert (
        request(
            "GET", "/files/preview", auth=False, params={"path": str(tmp_path / "hello.txt")}
        ).status_code
        == 401
    )
    assert (
        request(
            "GET", "/files/content", auth=False, params={"path": str(tmp_path / "hello.txt")}
        ).status_code
        == 401
    )
    assert request("DELETE", "/files/content").status_code == 405
    assert request("POST", "/files").status_code == 405
    assert request("PUT", "/files/content").status_code == 405


def test_listing_sort_pagination_symlinks_and_specials(tmp_path):
    (tmp_path / "z-dir").mkdir()
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "link").symlink_to(tmp_path / "a.txt")
    (tmp_path / "device-link").symlink_to("/dev/zero")
    os.mkfifo(tmp_path / "pipe")
    response = request("GET", "/files", params={"path": str(tmp_path), "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert [e["name"] for e in data["entries"]] == ["z-dir", "a.txt"]
    assert data["has_more"] and data["total"] == 3
    data = browser.list_directory(str(tmp_path), offset=2)
    assert data["entries"][0]["symlink"] is True


def test_regular_files_only_and_no_permission_elevation(tmp_path):
    unreadable = tmp_path / "secret"
    unreadable.write_text("secret")
    unreadable.chmod(0)
    try:
        if os.geteuid() != 0:
            assert (
                request("GET", "/files/content", params={"path": str(unreadable)}).status_code
                == 403
            )
    finally:
        unreadable.chmod(0o600)
    for path in ["/dev/zero", "/proc/self/environ", "/sys/kernel", str(tmp_path)]:
        assert request("GET", "/files/content", params={"path": path}).status_code in (400, 403)
    assert request("GET", "/files", params={"path": "relative"}).status_code == 400
    assert request("GET", "/files", params={"path": str(tmp_path / "absent")}).status_code == 404
    os.mkfifo(tmp_path / "fifo")
    assert (
        request("GET", "/files/content", params={"path": str(tmp_path / "fifo")}).status_code == 400
    )


def test_stream_range_head_and_unicode_filename(tmp_path):
    path = tmp_path / "video 测试.mp4"
    path.write_bytes(b"0123456789")
    params = {"path": str(path)}
    response = request("GET", "/files/content", params=params, headers={"Range": "bytes=2-5"})
    assert response.status_code == 206 and response.content == b"2345"
    assert response.headers["content-range"] == "bytes 2-5/10"
    assert response.headers["content-type"] == "video/mp4"
    response = request("GET", "/files/content", params=params, headers={"Range": "bytes=-3"})
    assert response.content == b"789"
    response = request("HEAD", "/files/content", params=params)
    assert response.status_code == 200 and response.content == b""
    assert response.headers["content-length"] == "10"
    for value in ["bytes=12-", "bytes=6-2", "bytes=0-1,3-4", "bytes=-0", "invalid"]:
        response = request("GET", "/files/content", params=params, headers={"Range": value})
        assert response.status_code == 416
        assert response.headers["content-range"] == "bytes */10"
    response = request("GET", "/files/content", params={**params, "download": True})
    assert response.content == b"0123456789"
    assert response.headers["content-type"] == "application/octet-stream"
    assert "filename*=UTF-8''" in response.headers["content-disposition"]


def test_markdown_code_and_active_content_are_safe(tmp_path):
    md = tmp_path / "readme.md"
    md.write_text(
        '# Hello\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```python\nprint("hi")\n```\n<script>alert(1)</script>\n![x](https://outside.test/a.png)\n[x](javascript:alert(1))'
    )
    response = request("GET", "/files/preview", params={"path": str(md)})
    assert response.status_code == 200
    assert "<h1>Hello</h1>" in response.text and "<table>" in response.text
    assert "<script>" not in response.text and "<img" not in response.text
    assert 'href="javascript:' not in response.text
    assert "sandbox" in response.headers["content-security-policy"]
    code = tmp_path / "sample.py"
    code.write_text('print("hello")\n')
    assert "<span" in browser.rendered_text(str(code))
    svg = tmp_path / "unsafe.svg"
    svg.write_text('<svg onload="alert(1)"></svg>')
    assert (
        request("GET", "/files/content", params={"path": str(svg)}).headers["content-type"]
        == "application/octet-stream"
    )
    assert "<svg onload" not in browser.rendered_text(str(svg))


def test_preview_limits_and_empty_download(tmp_path):
    path = tmp_path / "binary"
    path.write_bytes(b"a\x00b")
    assert request("GET", "/files/preview", params={"path": str(path)}).status_code == 415
    path.write_bytes(b"a" * (browser.MAX_TEXT_BYTES + 1))
    assert request("GET", "/files/preview", params={"path": str(path)}).status_code == 413
    path.write_bytes(b"")
    assert request("GET", "/files/content", params={"path": str(path)}).content == b""
    assert (
        request(
            "GET", "/files/content", params={"path": str(path)}, headers={"Range": "bytes=0-"}
        ).status_code
        == 416
    )


def test_open_descriptor_survives_path_replacement(tmp_path):
    path = tmp_path / "file.txt"
    path.write_bytes(b"original")
    _, fd, _ = browser.open_path(str(path))
    path.unlink()
    path.symlink_to("/dev/zero")
    try:
        assert os.read(fd, 32) == b"original"
    finally:
        os.close(fd)


def test_download_closed_if_client_disconnects_before_first_chunk():
    import io
    from app.api.files import FileStreamResponse

    source = io.BytesIO(b"hello")

    async def content():
        yield source.read()

    async def disconnected_send(message):
        raise OSError("Client disconnected")

    async def receive():
        return {"type": "http.disconnect"}

    response = FileStreamResponse(content(), source, media_type="application/octet-stream")

    async def run():
        try:
            await response(
                {"type": "http", "method": "GET", "asgi": {"spec_version": "2.4"}},
                receive,
                disconnected_send,
            )
        except Exception:
            pass

    asyncio.run(run())
    assert source.closed


def test_search_hidden_filter_and_sort_precede_pagination(tmp_path):
    for name in ("report-a.txt", "report-b.txt", "report-c.txt", "other.txt", ".report.txt"):
        (tmp_path / name).write_text(name)
    (tmp_path / "report-folder").mkdir()
    result = request(
        "GET",
        "/files",
        params={
            "path": str(tmp_path),
            "search": "REPORT",
            "show_hidden": False,
            "offset": 1,
            "limit": 2,
        },
    )
    assert result.status_code == 200
    data = result.json()
    assert data["total"] == 4
    assert [entry["name"] for entry in data["entries"]] == ["report-a.txt", "report-b.txt"]
    assert data["has_more"]
    assert (
        request("GET", "/files", params={"path": str(tmp_path), "sort": "invalid"}).status_code
        == 422
    )


def test_size_and_modified_order_keep_directories_first(tmp_path):
    (tmp_path / "folder").mkdir()
    (tmp_path / "small.txt").write_text("x")
    (tmp_path / "large.txt").write_text("x" * 20)
    os.utime(tmp_path / "small.txt", (200, 200))
    os.utime(tmp_path / "large.txt", (100, 100))
    for sort, expected in (
        ("size", ["folder", "large.txt", "small.txt"]),
        ("modified", ["folder", "small.txt", "large.txt"]),
    ):
        data = request(
            "GET", "/files", params={"path": str(tmp_path), "sort": sort, "descending": True}
        ).json()
        assert [entry["name"] for entry in data["entries"]] == expected
