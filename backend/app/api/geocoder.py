import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.dependencies import require_user
from app.models.user import User

router = APIRouter(prefix="/api/geocoder", tags=["geocoder"])


@router.get("/autocomplete")
async def address_autocomplete(
    q: str = Query(min_length=3, max_length=300),
    limit: int = Query(5, ge=1, le=10),
    _current_user: User = Depends(require_user),
):
    if not settings.GEOCODER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Геокодер не включён в настройках сервера",
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.GEOCODER_URL}/search",
                params={
                    "q": q,
                    "format": "json",
                    "limit": limit,
                    "addressdetails": 1,
                    "accept-language": "ru",
                },
                headers={"User-Agent": settings.APP_NAME},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data:
            results.append({
                "display_name": item.get("display_name", ""),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "type": item.get("type", ""),
            })

        return {"results": results}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Геокодер не отвечает")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Ошибка геокодера")


@router.get("/normalize")
async def normalize_address_via_geocoder(
    address: str = Query(min_length=5, max_length=2000),
    _current_user: User = Depends(require_user),
):
    if not settings.GEOCODER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Геокодер не включён в настройках сервера",
        )

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.GEOCODER_URL}/search",
                params={
                    "q": address,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                    "accept-language": "ru",
                },
                headers={"User-Agent": settings.APP_NAME},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data:
            return {"normalized": None, "message": "Адрес не найден в геокодере"}

        item = data[0]
        return {
            "normalized": item.get("display_name", ""),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
        }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Геокодер не отвечает")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Ошибка геокодера")
