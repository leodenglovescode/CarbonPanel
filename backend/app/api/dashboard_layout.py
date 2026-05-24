import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.dashboard_layout import DashboardLayout
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class LayoutPayload(BaseModel):
    layout: dict


@router.get("/layout", response_model=LayoutPayload | None)
async def get_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DashboardLayout).where(DashboardLayout.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None
    return {"layout": json.loads(row.layout_json)}


@router.put("/layout", response_model=LayoutPayload)
async def save_layout(
    body: LayoutPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DashboardLayout).where(DashboardLayout.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row:
        row.layout_json = json.dumps(body.layout)
    else:
        row = DashboardLayout(user_id=user.id, layout_json=json.dumps(body.layout))
    db.add(row)
    await db.commit()
    return {"layout": body.layout}
