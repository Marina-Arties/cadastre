"""Создание администратора при первом запуске."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.user import User
from app.utils.security import hash_password


async def seed_admin():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == "admin@cadastre.ru"))
        existing = result.scalar_one_or_none()
        if existing:
            existing.is_admin = True
            print(f"Администратор готов: admin@cadastre.ru / Admin123")
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
            print(f"Администратор создан: admin@cadastre.ru / Admin123")
        await session.commit()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_admin())
