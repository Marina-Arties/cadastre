from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=2, max_length=100)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: str
    email: str
    nickname: str
    full_name: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: datetime
    properties_count: int = 0
    rating: float = 0.0

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=2, max_length=100)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=128)


class UserAdminView(BaseModel):
    id: str
    email: str
    nickname: str
    full_name: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: datetime
    properties_count: int = 0
    rating: float = 0.0

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
