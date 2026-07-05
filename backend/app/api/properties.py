import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_user, require_admin
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyListResponse, PropertyResponse, PropertyUpdate
from app.services.deduplication import check_duplicate_fuzzy
from app.services.normalization import normalize_address

rate_limit_store: dict[str, list[float]] = defaultdict(list)

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = Query("created_at", pattern="^(id|name|address|created_at|user_nickname)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
    user_id: str = Query("", max_length=36),
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Property)
    count_query = select(func.count(Property.id))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Property.normalized_address.ilike(search_term),
                Property.name.ilike(search_term),
                Property.address.ilike(search_term),
            )
        )
        count_query = count_query.where(
            or_(
                Property.normalized_address.ilike(search_term),
                Property.name.ilike(search_term),
                Property.address.ilike(search_term),
            )
        )

    if user_id and current_user and current_user.is_admin:
        query = query.where(Property.user_id == user_id)
        count_query = count_query.where(Property.user_id == user_id)

    sort_column = getattr(Property, sort_by, Property.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).options(selectinload(Property.user))

    result = await db.execute(query)
    rows = result.scalars().all()

    items = []
    for p in rows:
        items.append(PropertyResponse(
            id=p.id,
            address=p.address,
            normalized_address=p.normalized_address,
            name=p.name,
            link=p.link,
            extra_data=p.extra_data,
            user_id=p.user_id,
            user_nickname=p.user.nickname if p.user else "",
            geo_lat=p.geo_lat,
            geo_lon=p.geo_lon,
            created_at=p.created_at,
            updated_at=p.updated_at,
        ))

    return PropertyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    data: PropertyCreate,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    now = time.time()
    window = 60.0
    max_requests = 10
    requests = rate_limit_store[current_user.id]
    requests = [t for t in requests if now - t < window]
    rate_limit_store[current_user.id] = requests
    if len(requests) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Не более {max_requests} объектов в минуту",
        )
    requests.append(now)

    duplicate = await check_duplicate_fuzzy(db, data.address)
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            "message": "Объект с таким адресом уже существует",
            "existing_id": duplicate.id,
        })

    normalized = normalize_address(data.address)
    prop = Property(
        address=data.address,
        normalized_address=normalized,
        name=data.name,
        link=data.link,
        extra_data=data.extra_data,
        user_id=current_user.id,
    )
    db.add(prop)
    await db.flush()
    await db.refresh(prop)

    return PropertyResponse(
        id=prop.id,
        address=prop.address,
        normalized_address=prop.normalized_address,
        name=prop.name,
        link=prop.link,
        extra_data=prop.extra_data,
        user_id=prop.user_id,
        user_nickname=current_user.nickname,
        geo_lat=prop.geo_lat,
        geo_lon=prop.geo_lon,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    )


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(Property.id == property_id).options(selectinload(Property.user))
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объект не найден")

    return PropertyResponse(
        id=prop.id,
        address=prop.address,
        normalized_address=prop.normalized_address,
        name=prop.name,
        link=prop.link,
        extra_data=prop.extra_data,
        user_id=prop.user_id,
        user_nickname=prop.user.nickname if prop.user else "",
        geo_lat=prop.geo_lat,
        geo_lon=prop.geo_lon,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    )


async def _can_edit(prop: Property, current_user: User) -> bool:
    if current_user.is_admin:
        return True
    if prop.user_id != current_user.id:
        return False
    now = datetime.now(timezone.utc)
    created = prop.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    elapsed = now - created
    return elapsed < timedelta(hours=24)


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: str,
    data: PropertyUpdate,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(Property.id == property_id).options(selectinload(Property.user))
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объект не найден")

    if not await _can_edit(prop, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на редактирование")

    if data.address is not None:
        duplicate = await check_duplicate_fuzzy(db, data.address)
        if duplicate and duplicate.id != prop.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
                "message": "Объект с таким адресом уже существует",
                "existing_id": duplicate.id,
            })
        prop.address = data.address
        prop.normalized_address = normalize_address(data.address)
    if data.name is not None:
        prop.name = data.name
    if data.link is not None:
        prop.link = data.link
    if data.extra_data is not None:
        prop.extra_data = data.extra_data
    prop.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(prop)

    return PropertyResponse(
        id=prop.id,
        address=prop.address,
        normalized_address=prop.normalized_address,
        name=prop.name,
        link=prop.link,
        extra_data=prop.extra_data,
        user_id=prop.user_id,
        user_nickname=prop.user.nickname if prop.user else "",
        geo_lat=prop.geo_lat,
        geo_lon=prop.geo_lon,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объект не найден")

    if not await _can_edit(prop, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на удаление")

    await db.delete(prop)
