from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.property import Property
from app.services.normalization import normalize_address
from app.services.trigram import trigram_similarity

FUZZY_THRESHOLD = 0.7


async def check_duplicate(db: AsyncSession, address: str) -> Property | None:
    normalized = normalize_address(address)
    result = await db.execute(
        select(Property).where(Property.normalized_address == normalized)
    )
    exact = result.scalar_one_or_none()
    if exact:
        return exact
    return None


async def check_duplicate_fuzzy(db: AsyncSession, address: str, threshold: float = FUZZY_THRESHOLD) -> Property | None:
    exact = await check_duplicate(db, address)
    if exact:
        return exact

    normalized = normalize_address(address)

    if "postgresql" in settings.DATABASE_URL:
        sim = func.similarity(Property.normalized_address, normalized)
        result = await db.execute(
            select(Property)
            .where(sim > threshold)
            .order_by(sim.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    result = await db.execute(
        select(Property)
    )
    candidates = result.scalars().all()

    best_match = None
    best_score = 0.0
    for prop in candidates:
        score = trigram_similarity(prop.normalized_address, normalized)
        if score > best_score:
            best_score = score
            best_match = prop

    if best_score >= threshold:
        return best_match
    return None
