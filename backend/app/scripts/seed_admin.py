"""Seed the admin user. Run with: python -m app.scripts.seed_admin"""

import argparse
import asyncio
import uuid

from sqlalchemy import select

import app.models.user  # noqa: F401
from app.config import settings
from app.core.security import hash_password
from app.database import AsyncSessionLocal, Base, engine
from app.models.user import User


async def seed(reset_password: bool = False) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        existing = result.scalar_one_or_none()
        if existing:
            if reset_password:
                existing.password_hash = hash_password(settings.admin_password)
                await db.commit()
                print(f"Reset password for '{settings.admin_username}'.")
            else:
                print(
                    f"Admin user '{settings.admin_username}' already exists; "
                    "password left unchanged."
                )
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
    parser = argparse.ArgumentParser(description="Create the initial CarbonPanel admin user.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Explicitly replace an existing admin password with ADMIN_PASSWORD.",
    )
    args = parser.parse_args()
    asyncio.run(seed(reset_password=args.reset_password))
