from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    user_id: str,
    user_nickname: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
):
    entry = AuditLog(
        user_id=user_id,
        user_nickname=user_nickname,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)


async def get_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    user_id: str | None = None,
):
    from sqlalchemy import func

    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    offset = (page - 1) * page_size

    result = await db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    )
    rows = result.scalars().all()

    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_nickname": r.user_nickname,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "details": r.details,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat(),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }
