import asyncio
import os
from urllib.parse import quote
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import get_current_user
from app.services import file_browser as browser

router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(get_current_user)])


class FileStreamResponse(StreamingResponse):
    def __init__(self, content, source, **kwargs):
        self.source = source
        super().__init__(content, **kwargs)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Also runs if the client disconnects before the iterator starts.
            self.source.close()


@router.get("")
async def list_files(
    path: str = "/",
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    search: str = Query("", max_length=200),
    sort: Literal["name", "modified", "size", "kind"] = "name",
    descending: bool = False,
    show_hidden: bool = True,
):
    try:
        return await asyncio.to_thread(
            browser.list_directory, path, offset, limit, search, sort, descending, show_hidden
        )
    except browser.BrowserError as exc:
        raise HTTPException(exc.status, exc.detail)


@router.get("/preview", response_class=HTMLResponse)
async def preview_text(path: str):
    try:
        content = await asyncio.to_thread(browser.rendered_text, path)
    except browser.BrowserError as exc:
        raise HTTPException(exc.status, exc.detail)
    return HTMLResponse(
        content,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "sandbox; default-src 'none'; style-src 'unsafe-inline'; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
            ),
        },
    )


@router.api_route("/content", methods=["GET", "HEAD"])
async def file_content(request: Request, path: str, download: bool = False):
    try:
        resolved, descriptor, info = await asyncio.to_thread(browser.open_path, path)
    except browser.BrowserError as exc:
        raise HTTPException(exc.status, exc.detail)
    try:
        start, end, partial = browser.byte_range(request.headers.get("range"), info.st_size)
    except browser.BrowserError as exc:
        os.close(descriptor)
        raise HTTPException(
            exc.status, exc.detail, headers={"Content-Range": f"bytes */{info.st_size}"}
        )
    kind, mime = browser.kind(str(resolved))
    attachment = download or kind not in ("image", "video", "audio")
    headers = {
        "Accept-Ranges": "bytes",
        "X-Accel-Buffering": "no",
        "Content-Length": str(max(0, end - start + 1)),
        "Content-Disposition": (
            f'{"attachment" if attachment else "inline"}; filename="download"; '
            f"filename*=UTF-8''{quote(resolved.name, safe='')}"
        ),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{info.st_size}"
    status = 206 if partial else 200
    if request.method == "HEAD":
        os.close(descriptor)
        return Response(status_code=status, headers=headers, media_type=mime)

    source = os.fdopen(descriptor, "rb")

    async def chunks():
        await run_in_threadpool(source.seek, start)
        remaining = max(0, end - start + 1)
        while remaining:
            chunk = await run_in_threadpool(source.read, min(256 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk

    return FileStreamResponse(
        chunks(),
        source,
        status_code=status,
        media_type=mime if not attachment else "application/octet-stream",
        headers=headers,
    )
