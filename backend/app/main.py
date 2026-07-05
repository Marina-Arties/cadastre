from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import admin, auth, export, geocoder, import_, leaderboard, password_reset, properties, users
from app.config import settings
from app.database import Base, engine

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATE_DIR = Path(__file__).parent / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "postgresql" in settings.DATABASE_URL:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    from app.seed import ensure_admin
    await ensure_admin()
    yield
    await engine.dispose()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(leaderboard.router)
app.include_router(export.router)
app.include_router(import_.router)
app.include_router(geocoder.router)
app.include_router(password_reset.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = TEMPLATE_DIR / "index.html"
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8")
        return HTMLResponse(
            content=content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return HTMLResponse(content="<h1>App is running</h1>", status_code=200)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">\xf0\x9f\x8f\xa0</text></svg>'
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
