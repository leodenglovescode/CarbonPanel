from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.device import Device
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceOut(BaseModel):
    id: str
    name: str
    ip_address: str | None
    last_seen: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[DeviceOut])
async def list_devices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device)
        .where(Device.user_id == user.id, Device.revoked == False)  # noqa: E712
        .order_by(Device.last_seen.desc())
    )
    return result.scalars().all()


@router.delete("/{device_id}")
async def revoke_device(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.revoked = True
    db.add(device)
    await db.commit()
    return {"success": True}
