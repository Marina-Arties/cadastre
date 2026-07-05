from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_user
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyResponse
from app.schemas.user import UserProfile, UserProfileUpdate
from app.services.rating import calculate_user_rating
from app.utils.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    rating = await calculate_user_rating(db, current_user.id)
    result = await db.execute(
        select(func.count(Property.id)).where(Property.user_id == current_user.id)
    )
    props_count = result.scalar() or 0
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        full_name=current_user.full_name,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        properties_count=props_count,
        rating=rating,
    )


@router.put("/me/profile", response_model=UserProfile)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if data.nickname is not None and data.nickname != current_user.nickname:
        existing = await db.execute(select(User).where(User.nickname == data.nickname))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Никнейм уже занят")
        current_user.nickname = data.nickname
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.password is not None:
        current_user.password_hash = hash_password(data.password)

    await db.flush()
    await db.refresh(current_user)

    rating = await calculate_user_rating(db, current_user.id)
    result = await db.execute(
        select(func.count(Property.id)).where(Property.user_id == current_user.id)
    )
    props_count = result.scalar() or 0
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        full_name=current_user.full_name,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        properties_count=props_count,
        rating=rating,
    )


@router.get("/me/properties")
async def get_my_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(func.count(Property.id)).where(Property.user_id == current_user.id)
    )
    total = count_result.scalar() or 0
    offset = (page - 1) * page_size

    result = await db.execute(
        select(Property)
        .where(Property.user_id == current_user.id)
        .order_by(Property.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .options(selectinload(Property.user))
    )
    rows = result.scalars().all()

    items = [
        PropertyResponse(
            id=p.id,
            address=p.address,
            normalized_address=p.normalized_address,
            name=p.name,
            link=p.link,
            user_id=p.user_id,
            user_nickname=current_user.nickname,
            geo_lat=p.geo_lat,
            geo_lon=p.geo_lon,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/me/check-add", response_model=bool)
async def check_add_property(
    address: str = Query(min_length=5, max_length=2000),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_user),
):
    from app.services.deduplication import check_duplicate_fuzzy
    duplicate = await check_duplicate_fuzzy(db, address)
    return duplicate is None
