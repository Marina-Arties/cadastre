from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    address: str = Field(min_length=5, max_length=2000)
    name: str = Field(min_length=1, max_length=500)
    link: Optional[str] = Field(None, max_length=2000)
    extra_data: Optional[dict[str, Any]] = None


class PropertyUpdate(BaseModel):
    address: Optional[str] = Field(None, min_length=5, max_length=2000)
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    link: Optional[str] = Field(None, max_length=2000)
    extra_data: Optional[dict[str, Any]] = None


class PropertyResponse(BaseModel):
    id: str
    address: str
    normalized_address: str
    name: str
    link: Optional[str]
    extra_data: Optional[dict[str, Any]] = None
    user_id: str
    user_nickname: str = ""
    geo_lat: Optional[float]
    geo_lon: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    page_size: int
    pages: int
