from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.webhook import Webhook
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreate(BaseModel):
    label: str = ""
    url: str
    enabled: bool = True
    events: list[str] = ["alert.cpu", "alert.ram", "alert.disk"]


class WebhookUpdate(BaseModel):
    label: str | None = None
    url: str | None = None
    enabled: bool | None = None
    events: list[str] | None = None


class WebhookResponse(BaseModel):
    id: str
    label: str
    url: str
    enabled: bool
    events: list[str]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: Webhook) -> "WebhookResponse":
        return cls(
            id=obj.id,
            label=obj.label,
            url=obj.url,
            enabled=obj.enabled,
            events=obj.events.split(",") if obj.events else [],
        )


class TriggerRequest(BaseModel):
    event: str
    metric: str
    value: float
    threshold: float


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hooks = await webhook_service.get_all(db)
    return [WebhookResponse.from_orm_obj(h) for h in hooks]


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    body: WebhookCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hook = Webhook(
        label=body.label,
        url=body.url,
        enabled=body.enabled,
        events=",".join(body.events),
    )
    db.add(hook)
    await db.commit()
    await db.refresh(hook)
    return WebhookResponse.from_orm_obj(hook)


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    hook = result.scalar_one_or_none()
    if not hook:
        raise HTTPException(404, "Webhook not found")
    if body.label is not None:
        hook.label = body.label
    if body.url is not None:
        hook.url = body.url
    if body.enabled is not None:
        hook.enabled = body.enabled
    if body.events is not None:
        hook.events = ",".join(body.events)
    await db.commit()
    await db.refresh(hook)
    return WebhookResponse.from_orm_obj(hook)


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    hook = result.scalar_one_or_none()
    if not hook:
        raise HTTPException(404, "Webhook not found")
    await db.delete(hook)
    await db.commit()
    return {"success": True}


@router.post("/trigger")
async def trigger_webhook(
    body: TriggerRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await webhook_service.fire_event(db, body.event, {
        "metric": body.metric,
        "value": body.value,
        "threshold": body.threshold,
    })
    return {"success": True}
