import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.dependencies import get_current_user, require_auth
from app.models.user import User
from app.schemas.metrics import HistoryPoint
from app.services.metrics.collector import metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Top-level snapshot sections a caller may ask for. A phone drawing a CPU/RAM
# trace wants a few hundred bytes; the full snapshot carries per-core figures,
# every process, every disk and every NIC. At 2.5 requests/second over mobile
# data that difference decides whether polling is viable.
_SECTIONS = {"cpu", "memory", "gpu", "disks", "network", "processes", "system"}


@router.get("/history", response_model=list[HistoryPoint])
async def get_history(_: User = Depends(get_current_user)):
    return list(metrics_collector.history)


@router.get("/current")
async def get_current(
    request: Request,
    response: Response,
    fields: str | None = Query(
        default=None,
        description="Comma-separated sections to include, e.g. 'cpu,memory'. "
                    "Defaults to the full snapshot.",
    ),
    interval: float | None = Query(
        default=None, ge=0.4, le=30.0,
        description="Cadence this client intends to poll at. Keeps the shared "
                    "collector running fast enough to serve it.",
    ),
    sort: str = Query(default="cpu", pattern="^(cpu|memory)$"),
    limit: int = Query(default=25, ge=1, le=500),
    user_id: str = Depends(require_auth),
):
    """Latest metrics over the request/response API.

    Serves the collector's cached values — it never triggers collection, so the
    cost of a request is independent of how fast clients poll. Native clients
    use this instead of the WebSocket: the handshake's Origin check is built
    for browsers, and a phone has no business holding a socket open anyway.
    """
    # Registering the caller keeps the shared loop running at least as fast as
    # they poll. Keyed per user+client so several devices coexist; the entry
    # lapses on its own once they stop asking.
    origin = request.headers.get("x-device-id") or (
        request.client.host if request.client else "?"
    )
    metrics_collector.note_http_client(
        f"{user_id}:{origin}", interval=interval, sort_by=sort, limit=limit
    )

    snapshot = metrics_collector.snapshot(sort_by=sort, limit=limit)
    if snapshot is None:
        # The collector has not completed its first cycle yet.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics not collected yet",
        )

    data = snapshot.model_dump()

    if fields:
        wanted = {f.strip() for f in fields.split(",") if f.strip()}
        unknown = wanted - _SECTIONS
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown field(s): {', '.join(sorted(unknown))}. "
                       f"Valid: {', '.join(sorted(_SECTIONS))}",
            )
        data = {k: v for k, v in data.items() if k in wanted or k in ("type", "ts")}

    # Lets a client skip re-parsing an unchanged payload. Mostly a no-op when
    # polling faster than the collector runs, which is exactly when it helps.
    etag = hashlib.md5(repr(sorted(data.items())).encode()).hexdigest()[:16]
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-store"
    return data
