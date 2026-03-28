from fastapi import APIRouter

from app.config.settings import settings
from app.core.session_manager import SessionManager

router = APIRouter()


def create_router(session_manager: SessionManager) -> APIRouter:
    @router.get("/health")
    async def health():
        return {
            "status": "ok",
            "active_sessions": session_manager.active_count,
        }

    @router.get("/config")
    async def config():
        return {
            "model": settings.gemini_model,
            "voice": settings.gemini_voice,
        }

    return router
