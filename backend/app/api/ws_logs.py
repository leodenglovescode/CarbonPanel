import asyncio
import json
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token

router = APIRouter(tags=["websocket"])

_PRESET_SOURCES: dict[str, list[str]] = {
    "syslog":   ["tail", "-n", "100", "-f", "/var/log/syslog"],
    "auth":     ["tail", "-n", "100", "-f", "/var/log/auth.log"],
    "kern":     ["tail", "-n", "100", "-f", "/var/log/kern.log"],
    "journalctl": ["journalctl", "-n", "100", "-f", "--no-pager", "--output=short-iso"],
}

_MAX_CUSTOM_PATH_LEN = 256


_ALLOWED_LOG_ROOT = "/var/log"  # matches the log-viewer UI's own "/var/log/..." hint


def _resolve_source(source: str) -> list[str] | None:
    if source in _PRESET_SOURCES:
        return _PRESET_SOURCES[source]
    # Custom absolute file path — must resolve under /var/log, not just look
    # like an absolute path (a bare ".." check doesn't stop e.g. symlinks or
    # already-absolute sensitive paths like /etc/shadow).
    if source.startswith("/") and len(source) <= _MAX_CUSTOM_PATH_LEN:
        resolved = os.path.realpath(source)
        if resolved == _ALLOWED_LOG_ROOT or resolved.startswith(_ALLOWED_LOG_ROOT + os.sep):
            if os.path.isfile(resolved):
                return ["tail", "-n", "100", "-f", resolved]
    return None


@router.websocket("/ws/logs")
async def logs_ws(ws: WebSocket, token: str = "", source: str = "journalctl"):
    try:
        payload = decode_token(token)
        if payload.get("scope") != "full":
            await ws.close(code=4001)
            return
    except ValueError:
        await ws.close(code=4001)
        return

    cmd = _resolve_source(source)
    if cmd is None:
        await ws.accept()
        await ws.send_text(json.dumps({"type": "error", "msg": f"Unknown source: {source}"}))
        await ws.close()
        return

    await ws.accept()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    async def _read_lines() -> None:
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip("\n")
            try:
                await ws.send_text(json.dumps({"type": "line", "text": line}))
            except Exception:
                break

    async def _wait_disconnect() -> None:
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    read_task = asyncio.create_task(_read_lines())
    disc_task = asyncio.create_task(_wait_disconnect())

    done, pending = await asyncio.wait(
        [read_task, disc_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for t in pending:
        t.cancel()

    if proc.returncode is None:
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
        except asyncio.TimeoutError:
            proc.kill()

    try:
        await ws.close()
    except Exception:
        pass
