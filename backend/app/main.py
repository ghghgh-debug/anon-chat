"""
Main FastAPI application — entry point.

Assembles all API routers, starts the Telegram bot webhook,
and configures middleware (CORS, rate limiting, media serving).
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import time

from app.core.config import get_settings
from app.api import users, chat, admin, payments
from app.db.session import engine
from app.db.base import Base

settings = get_settings()


# --- Rate limiting (simple in-memory, replace with Redis in production) ---

rate_limit_store: dict[str, list[float]] = {}

RATE_LIMITS = {
    "/chat/search": (1, 5),       # 1 request per 5 seconds
    "/chat/report": (1, 60),      # 1 report per minute
    "/chat/rate": (5, 60),        # 5 ratings per minute
    "/chat/heartbeat": (1, 10),   # 1 heartbeat per 10 seconds
}


async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware."""
    path = request.url.path
    
    for pattern, (max_requests, window) in RATE_LIMITS.items():
        if path.startswith(pattern):
            # Use Authorization header as key (unique per user)
            auth = request.headers.get("Authorization", "anonymous")
            key = f"{auth}:{pattern}"
            
            now = time.time()
            if key not in rate_limit_store:
                rate_limit_store[key] = []
            
            # Clean old entries
            rate_limit_store[key] = [t for t in rate_limit_store[key] if now - t < window]
            
            if len(rate_limit_store[key]) >= max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                )
            
            rate_limit_store[key].append(now)
            break
    
    return await call_next(request)


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create upload directory
    os.makedirs(settings.MEDIA_UPLOAD_DIR, exist_ok=True)
    
    yield
    
    # Cleanup
    from app.services.matching import matching_service
    await matching_service.close()
    await engine.dispose()


# --- Create app ---

app = FastAPI(
    title="AnonChat TMA API",
    description="Telegram Mini App — Anonymous Chat API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.middleware("http")(rate_limit_middleware)

# Static files (media uploads)
if os.path.exists(settings.MEDIA_UPLOAD_DIR):
    app.mount("/media", StaticFiles(directory=settings.MEDIA_UPLOAD_DIR), name="media")

# API routers
app.include_router(users.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(payments.router, prefix="/api")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "app": settings.APP_NAME}


# --- Telegram Bot webhook endpoint ---

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Receive Telegram Bot updates via webhook.
    This endpoint is called by Telegram servers.
    """
    from aiogram import Bot
    from app.bot.handlers import bot, get_dispatcher
    
    dp = get_dispatcher()
    update = await request.json()
    
    from aiogram.types import Update
    tg_update = Update(**update)
    await dp.feed_update(bot, tg_update)
    
    return {"ok": True}
