from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.bookmark import Bookmark
from app.models.user import User

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


class BookmarkIn(BaseModel):
    title: str
    url: str
    icon_url: str | None = None
    sort_order: int = 0


class BookmarkOut(BookmarkIn):
    id: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BookmarkOut])
async def list_bookmarks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark)
        .where(Bookmark.user_id == user.id)
        .order_by(Bookmark.sort_order, Bookmark.id)
    )
    return result.scalars().all()


@router.post("", response_model=BookmarkOut, status_code=201)
async def create_bookmark(
    body: BookmarkIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bm = Bookmark(user_id=user.id, **body.model_dump())
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return bm


@router.put("/{bm_id}", response_model=BookmarkOut)
async def update_bookmark(
    bm_id: str,
    body: BookmarkIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bm_id, Bookmark.user_id == user.id)
    )
    bm = result.scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    for k, v in body.model_dump().items():
        setattr(bm, k, v)
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return bm


@router.delete("/{bm_id}")
async def delete_bookmark(
    bm_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bm_id, Bookmark.user_id == user.id)
    )
    bm = result.scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(bm)
    await db.commit()
    return {"success": True}
