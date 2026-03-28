from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import create_router
from app.api.ws import create_ws_router
from app.config.settings import settings
from app.core.session_manager import SessionManager

session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting voice assistant server")
    yield
    logger.info("Shutting down — cleaning up sessions")
    await session_manager.cleanup_all()


app = FastAPI(title="Gemini Voice Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_router(session_manager))
app.include_router(create_ws_router(session_manager, settings))


@app.post("/connect")
async def connect():
    """RTVI client calls this to get a WebSocket URL."""
    session_id = str(uuid4())
    return {"wsUrl": f"ws://localhost:{settings.port}/ws/{session_id}"}
