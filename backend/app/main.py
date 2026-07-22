from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "Starting %s | bg_provider=%s | model=%s | Real-ESRGAN ×%s",
        settings.app_name,
        settings.bg_provider,
        settings.birefnet_model if settings.bg_provider == "local" else "remove.bg",
        settings.realesrgan_scale,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI image pipeline for commercial printing presses",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
        "bg_engine": settings.bg_provider,
        "upscaler": "Real-ESRGAN",
    }
