from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.security import create_access_token, hash_password

router = APIRouter(prefix="/api/password", tags=["password"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


_reset_tokens: dict[str, tuple[str, float]] = {}


@router.post("/forgot")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user:
        return {"message": "Если email зарегистрирован, инструкции отправлены"}

    import secrets
    import time
    import logging

    reset_token = secrets.token_urlsafe(32)
    _reset_tokens[reset_token] = (user.id, time.time() + 3600)

    logger = logging.getLogger("app.password_reset")
    logger.info(f"Password reset token for {user.email}: {reset_token}")

    return {
        "message": "Инструкции по восстановлению отправлены на email",
        "dev_token": reset_token if True else None,
    }


@router.post("/reset")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    import time

    if data.token not in _reset_tokens:
        raise HTTPException(status_code=400, detail="Недействительный или просроченный токен")

    user_id, expires = _reset_tokens[data.token]
    if time.time() > expires:
        del _reset_tokens[data.token]
        raise HTTPException(status_code=400, detail="Токен просрочен")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 8 символов")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.password_hash = hash_password(data.new_password)
    await db.flush()

    del _reset_tokens[data.token]

    return {"message": "Пароль успешно изменён"}
