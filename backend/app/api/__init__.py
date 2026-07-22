from fastapi import APIRouter

from app.api.routes import router as process_router

api_router = APIRouter()
api_router.include_router(process_router)
