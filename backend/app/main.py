import logging
from collections import defaultdict, deque
from time import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.api import admin, agent, analytics, auth, conversations, documents, tools
from app.core.config import get_settings
from app.database.session import Base, engine, SessionLocal
from app.models import entities

settings = get_settings()
logger = logging.getLogger("voicepilot")

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="VoicePilot AI", version="0.1.0", docs_url="/docs", redoc_url="/redoc", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, same_site="lax", https_only=settings.environment == "production")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hits: dict[str, deque] = defaultdict(deque)
RATE_LIMIT = 120
WINDOW = 60


@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        key = request.client.host if request.client else "unknown"
        bucket = hits[key]
        current = time()
        while bucket and bucket[0] < current - WINDOW:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT:
            return JSONResponse({"detail": "Too many requests"}, status_code=429)
        bucket.append(current)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    message = str(first.get("msg", "Invalid input")).replace("Value error, ", "")
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    return JSONResponse({"detail": f"{field}: {message}" if field else message}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse({"detail": "Something went wrong on our side"}, status_code=500)


for module in (auth, conversations, agent, documents, tools, analytics, admin):
    app.include_router(module.router)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "environment": settings.environment,
        "llm_configured": bool(settings.llm_api_key),
        "oauth": {"google": bool(settings.google_client_id), "github": bool(settings.github_client_id), "microsoft": bool(settings.microsoft_client_id)},
    }
