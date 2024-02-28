from fastapi import APIRouter

from src.auth.router import router as auth_router
from src.users.router import router as users_router
from src.services.router import router as services_router
from src.media.router import router as media_router

api_router = APIRouter(prefix="/api/v2")
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(services_router, prefix="/services", tags=["Services"])
api_router.include_router(media_router, prefix="/media", tags=["Media"])
