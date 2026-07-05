from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.user import User


async def calculate_user_rating(db: AsyncSession, user_id: str) -> float:
    result = await db.execute(
        select(func.count(Property.id).label("count"), func.count(Property.geo_lat).label("geo_count"))
        .where(Property.user_id == user_id)
    )
    row = result.one()
    count = row.count or 0
    geo_count = row.geo_count or 0
    return float(count + geo_count * 0.5)
