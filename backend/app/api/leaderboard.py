from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.property import Property
from app.models.user import User

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("")
async def get_leaderboard(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    subq = (
        select(
            Property.user_id,
            func.count(Property.id).label("prop_count"),
            func.count(Property.geo_lat).label("geo_count"),
        )
        .group_by(Property.user_id)
        .subquery()
    )

    query = (
        select(
            User.id,
            User.nickname,
            User.created_at,
            func.coalesce(subq.c.prop_count, 0).label("properties_count"),
            (func.coalesce(subq.c.prop_count, 0) + func.coalesce(subq.c.geo_count, 0) * 0.5).label("rating"),
        )
        .outerjoin(subq, User.id == subq.c.user_id)
        .where(User.is_active == True)
        .order_by(func.coalesce(subq.c.prop_count, 0).desc())
    )

    count_query = (
        select(func.count(User.id))
        .outerjoin(subq, User.id == subq.c.user_id)
        .where(User.is_active == True)
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size

    result = await db.execute(query.offset(offset).limit(page_size))
    rows = result.all()

    items = []
    rank_start = offset + 1
    for i, row in enumerate(rows):
        items.append({
            "rank": rank_start + i,
            "user_id": row[0],
            "nickname": row[1],
            "created_at": row[2].isoformat(),
            "properties_count": int(row[3]),
            "rating": float(row[4]),
        })

    pages = max(1, (total + page_size - 1) // page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
