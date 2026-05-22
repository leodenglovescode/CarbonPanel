import asyncio
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


async def get_all(db: AsyncSession) -> list[Webhook]:
    result = await db.execute(select(Webhook))
    return list(result.scalars().all())


def _post_sync(url: str, body: str) -> None:
    data = body.encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Content-Length": str(len(data))},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception as exc:
        logger.warning("Webhook delivery failed for %s: %s", url, exc)


async def fire_event(db: AsyncSession, event: str, payload: dict[str, Any]) -> None:
    hooks = await get_all(db)
    enabled = [h for h in hooks if h.enabled and event in h.events.split(",")]
    if not enabled:
        return

    body = json.dumps({
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    })

    loop = asyncio.get_event_loop()
    await asyncio.gather(
        *[loop.run_in_executor(None, _post_sync, h.url, body) for h in enabled],
        return_exceptions=True,
    )
