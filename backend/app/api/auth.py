import re
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_user
from app.models.property import Property
from app.models.user import User
from app.schemas.user import TokenResponse, UserLogin, UserProfile, UserRegister
from app.services.rating import calculate_user_rating
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

login_attempts: dict[str, list[float]] = defaultdict(list)
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Пароль должен быть не менее 8 символов"
    if len(password) > 128:
        return "Пароль слишком длинный"
    if not re.search(r"[a-z]", password):
        return "Пароль должен содержать строчную букву"
    if not re.search(r"[A-Z]", password):
        return "Пароль должен содержать заглавную букву"
    if not re.search(r"\d", password):
        return "Пароль должен содержать цифру"
    return None


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    pw_error = validate_password_strength(data.password)
    if pw_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_error)

    existing = await db.execute(select(User).where(
        (User.email == data.email) | (User.nickname == data.nickname)
    ))
    user = existing.scalar_one_or_none()
    if user:
        if user.email == data.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже зарегистрирован")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Никнейм уже занят")

    new_user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        nickname=data.nickname,
        full_name=data.full_name,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    access_token = create_access_token({"sub": new_user.id})
    rating = await calculate_user_rating(db, new_user.id)
    return TokenResponse(
        access_token=access_token,
        user=UserProfile(
            id=new_user.id,
            email=new_user.email,
            nickname=new_user.nickname,
            full_name=new_user.full_name,
            is_admin=new_user.is_admin,
            is_active=new_user.is_active,
            created_at=new_user.created_at,
            properties_count=0,
            rating=rating,
        ),
    )


def check_login_rate_limit(client_ip: str) -> None:
    now = time.time()
    window = 60.0
    max_attempts = 5
    attempts = [t for t in login_attempts[client_ip] if now - t < window]
    login_attempts[client_ip] = attempts
    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Подождите минуту.",
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        login_attempts[client_ip].append(time.time())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт заблокирован")

    login_attempts.pop(client_ip, None)

    access_token = create_access_token({"sub": user.id})
    rating = await calculate_user_rating(db, user.id)
    count_query = select(func.count(Property.id)).where(Property.user_id == user.id)
    count_result = await db.execute(count_query)
    props_count = count_result.scalar() or 0
    return TokenResponse(
        access_token=access_token,
        user=UserProfile(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            full_name=user.full_name,
            is_admin=user.is_admin,
            is_active=user.is_active,
            created_at=user.created_at,
            properties_count=props_count,
            rating=rating,
        ),
    )


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    rating = await calculate_user_rating(db, current_user.id)
    count_query = select(func.count(Property.id)).where(Property.user_id == current_user.id)
    count_result = await db.execute(count_query)
    props_count = count_result.scalar() or 0
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
