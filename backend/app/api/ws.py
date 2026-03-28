from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.runner import PipelineRunner

from app.config.settings import Settings
from app.core.pipeline_factory import PipelineFactory
from app.core.session_manager import SessionManager
from app.transport.websocket_transport import create_websocket_transport

ws_router = APIRouter()


def create_ws_router(
    session_manager: SessionManager,
    settings: Settings,
) -> APIRouter:
    @ws_router.websocket("/ws/{session_id}")
    async def websocket_voice(websocket: WebSocket, session_id: str):
        await websocket.accept()
        logger.info(f"WebSocket connected: {session_id}")

        transport = create_websocket_transport(websocket)
        task = PipelineFactory.create(transport, settings)
        session = session_manager.create_session(task)

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info(f"Client connected to session {session.session_id}")
            session.state = "active"
            await task.queue_frames([LLMRunFrame()])

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info(f"Client disconnected from session {session.session_id}")
            await task.cancel()

        try:
            runner = PipelineRunner(handle_sigint=False)
            await runner.run(task)
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Pipeline error in session {session_id}: {e}")
        finally:
            await session_manager.remove_session(session.session_id)

    return ws_router
