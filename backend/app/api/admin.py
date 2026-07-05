from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_admin
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyUpdate, PropertyResponse
from app.schemas.user import UserAdminUpdate, UserAdminView
from app.services.audit import get_logs, log_action
from app.services.deduplication import check_duplicate_fuzzy
from app.services.rating import calculate_user_rating
from app.services.normalization import normalize_address

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str = Query("", max_length=200),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.nickname.ilike(search_term)) | (User.email.ilike(search_term))
        )
        count_query = count_query.where(
            (User.nickname.ilike(search_term)) | (User.email.ilike(search_term))
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(User.created_at.desc()))
    rows = result.scalars().all()

    items = []
    for u in rows:
        rating = await calculate_user_rating(db, u.id)
        props_count_result = await db.execute(
            select(func.count(Property.id)).where(Property.user_id == u.id)
        )
        props_count = props_count_result.scalar() or 0
        items.append(UserAdminView(
            id=u.id,
            email=u.email,
            nickname=u.nickname,
            full_name=u.full_name,
            is_admin=u.is_admin,
            is_active=u.is_active,
            created_at=u.created_at,
            properties_count=props_count,
            rating=rating,
        ))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserAdminUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.flush()
    await log_action(
        db, current_user.id, current_user.nickname,
        "update_user",
        target_type="user", target_id=user_id,
        details=f"is_admin={data.is_admin}, is_active={data.is_active}",
        ip_address=request.client.host if request.client else None,
    )
    return {"message": "Пользователь обновлён"}


@router.get("/properties")
async def list_all_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Property).options(selectinload(Property.user))
    count_query = select(func.count(Property.id))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size

    result = await db.execute(
        query.order_by(Property.created_at.desc()).offset(offset).limit(page_size)
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
            user_nickname=p.user.nickname if p.user else "",
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


@router.put("/properties/{property_id}", response_model=PropertyResponse)
async def admin_update_property(
    property_id: str,
    data: PropertyUpdate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(Property.id == property_id).options(selectinload(Property.user))
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объект не найден")

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

    await db.flush()
    await db.refresh(prop)

    await log_action(
        db, current_user.id, current_user.nickname,
        "update_property",
        target_type="property", target_id=prop.id,
        details=f"name={prop.name}, address={prop.address}",
        ip_address=request.client.host if request.client else None,
    )

    return PropertyResponse(
        id=prop.id,
        address=prop.address,
        normalized_address=prop.normalized_address,
        name=prop.name,
        link=prop.link,
        user_id=prop.user_id,
        user_nickname=prop.user.nickname if prop.user else "",
        geo_lat=prop.geo_lat,
        geo_lon=prop.geo_lon,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
    )


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_property(
    property_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Объект не найден")
    await db.delete(prop)
    await log_action(
        db, current_user.id, current_user.nickname,
        "delete_property",
        target_type="property", target_id=property_id,
        details=f"name={prop.name}, address={prop.address}",
        ip_address=request.client.host if request.client else None,
    )


@router.get("/logs")
async def get_admin_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str = Query("", max_length=100),
    user_id: str = Query("", max_length=36),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_logs(db, page=page, page_size=page_size, action=action or None, user_id=user_id or None)
