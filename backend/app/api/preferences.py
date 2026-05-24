import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_preferences import UserPreferences

router = APIRouter(prefix="/settings", tags=["preferences"])


class PrefsPayload(BaseModel):
    prefs: dict


@router.get("/preferences", response_model=PrefsPayload)
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"prefs": {}}
    return {"prefs": json.loads(row.prefs_json)}


@router.put("/preferences", response_model=PrefsPayload)
async def save_preferences(
    body: PrefsPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row:
        row.prefs_json = json.dumps(body.prefs)
    else:
        row = UserPreferences(user_id=user.id, prefs_json=json.dumps(body.prefs))
    db.add(row)
    await db.commit()
    return {"prefs": body.prefs}
