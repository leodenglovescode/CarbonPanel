"""Seed the admin user. Run with: python -m app.scripts.seed_admin"""

import asyncio
import uuid

from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.database import AsyncSessionLocal, engine
from app.models.user import User


async def seed() -> None:
    async with engine.begin() as conn:
        from app.database import Base
        import app.models.user  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_username))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"User '{settings.admin_username}' already exists — skipping.")
            return

        user = User(
            id=str(uuid.uuid4()),
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(user)
        await db.commit()
        print(f"Created admin user '{settings.admin_username}'.")


if __name__ == "__main__":
    asyncio.run(seed())
