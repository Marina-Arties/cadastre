import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.user import User
from app.utils.security import hash_password


async def ensure_admin():
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@cadastre.ru")
        )
        existing = result.scalar_one_or_none()
        if existing:
            if not existing.is_admin:
                existing.is_admin = True
                await session.commit()
        else:
            admin = User(
                id=str(uuid.uuid4()),
                email="admin@cadastre.ru",
                password_hash=hash_password("Admin123"),
                nickname="admin",
                full_name="Администратор",
                is_admin=True,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(admin)
            await session.commit()
