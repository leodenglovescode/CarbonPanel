from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.webhook import Webhook
from app.services import webhook_service

router = APIRouter(tags=["notifications"])


class WebhookCreate(BaseModel):
    label: str = Field(default="", max_length=120)
    kind: str = "webhook"
    url: str = ""
    topic: str | None = None
    token: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_security: str | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: str | None = None
    enabled: bool = True
    events: list[str] = Field(
        default_factory=lambda: list(webhook_service.EVENT_NAMES)
    )


class WebhookUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    kind: str | None = None
    url: str | None = None
    topic: str | None = None
    token: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_security: str | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: str | None = None
    enabled: bool | None = None
    events: list[str] | None = None


class WebhookResponse(BaseModel):
    id: str
    label: str
    kind: str
    url: str
    topic: str | None
    has_token: bool
    smtp_host: str | None
    smtp_port: int | None
    smtp_security: str | None
    has_smtp_credentials: bool
    email_from: str | None
    email_to: str | None
    enabled: bool
    events: list[str]

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: Webhook) -> "WebhookResponse":
        return cls(
            id=obj.id,
            label=obj.label,
            kind=obj.kind,
            url=obj.url,
            topic=obj.topic,
            has_token=bool(obj.token),
            smtp_host=obj.smtp_host,
            smtp_port=obj.smtp_port,
            smtp_security=obj.smtp_security,
            has_smtp_credentials=bool(obj.smtp_username and obj.smtp_password),
            email_from=obj.email_from,
            email_to=obj.email_to,
            enabled=obj.enabled,
            events=obj.events.split(",") if obj.events else [],
        )


class TriggerRequest(BaseModel):
    event: str
    metric: str
    value: float
    threshold: float
    message: str | None = Field(default=None, max_length=1000)
    severity: Literal["info", "warning", "critical"] = "warning"
    unit: str = Field(default="%", max_length=16)
    label: str | None = Field(default=None, max_length=120)


def _validate_events(events: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(events))
    if not normalized or any(event not in webhook_service.EVENTS for event in normalized):
        raise HTTPException(422, "Select at least one valid alert event")
    return normalized


def _validated_config(
    *,
    kind: str,
    url: str,
    topic: str | None,
    smtp_host: str | None,
    smtp_port: int | None,
    smtp_security: str | None,
    smtp_username: str | None,
    smtp_password: str | None,
    email_from: str | None,
    email_to: str | None,
) -> str:
    try:
        return webhook_service.validate_channel_config(
            kind=kind,
            url=url,
            topic=topic,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_security=smtp_security,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            email_from=email_from,
            email_to=email_to,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hooks = await webhook_service.get_all(db)
    return [WebhookResponse.from_orm_obj(hook) for hook in hooks]


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    body: WebhookCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = _validated_config(
        kind=body.kind,
        url=body.url,
        topic=body.topic,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_security=body.smtp_security,
        smtp_username=body.smtp_username,
        smtp_password=body.smtp_password,
        email_from=body.email_from,
        email_to=body.email_to,
    )
    hook = Webhook(
        label=body.label,
        kind=body.kind,
        url=url,
        topic=body.topic,
        token=body.token.strip() if body.token and body.token.strip() else None,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_security=body.smtp_security,
        smtp_username=body.smtp_username,
        smtp_password=body.smtp_password,
        email_from=body.email_from,
        email_to=body.email_to,
        enabled=body.enabled,
        events=",".join(_validate_events(body.events)),
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
        raise HTTPException(404, "Notification channel not found")

    def updated(name: str):
        value = getattr(body, name)
        return value if value is not None else getattr(hook, name)

    url = _validated_config(
        kind=updated("kind"),
        url=updated("url"),
        topic=updated("topic"),
        smtp_host=updated("smtp_host"),
        smtp_port=updated("smtp_port"),
        smtp_security=updated("smtp_security"),
        smtp_username=updated("smtp_username"),
        smtp_password=updated("smtp_password"),
        email_from=updated("email_from"),
        email_to=updated("email_to"),
    )

    for field in (
        "label",
        "kind",
        "topic",
        "smtp_host",
        "smtp_port",
        "smtp_security",
        "smtp_username",
        "smtp_password",
        "email_from",
        "email_to",
        "enabled",
    ):
        value = getattr(body, field)
        if value is not None:
            setattr(hook, field, value)
    if body.url is not None:
        hook.url = url
    if body.token is not None:
        hook.token = body.token.strip() or None
    if body.events is not None:
        hook.events = ",".join(_validate_events(body.events))

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
        raise HTTPException(404, "Notification channel not found")
    await db.delete(hook)
    await db.commit()
    return {"success": True}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    hook = result.scalar_one_or_none()
    if not hook:
        raise HTTPException(404, "Notification channel not found")
    delivery = await webhook_service.deliver_channel(
        hook,
        "test",
        {"metric": "manual", "value": 0, "threshold": 0, "severity": "info", "unit": ""},
    )
    if not delivery.success:
        raise HTTPException(502, delivery.error or "Notification delivery failed")
    return {"success": True, "status": delivery.status}


@router.post("/trigger")
async def trigger_webhook(
    body: TriggerRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.event not in webhook_service.EVENTS:
        raise HTTPException(422, "Unknown notification event")
    results = await webhook_service.fire_event(
        db,
        body.event,
        {
            "metric": body.metric,
            "value": body.value,
            "threshold": body.threshold,
            "message": body.message,
            "severity": body.severity,
            "unit": body.unit,
            "label": body.label,
        },
    )
    failed = [result for result in results if not result.success]
    if results and len(failed) == len(results):
        raise HTTPException(502, failed[0].error or "Notification delivery failed")
    return {
        "success": True,
        "delivered": len(results) - len(failed),
        "failed": len(failed),
    }
