import asyncio
from uuid import uuid4

from loguru import logger
from pipecat.pipeline.task import PipelineTask

from app.core.events import SessionState


class Session:
    def __init__(self, session_id: str, task: PipelineTask):
        self.session_id = session_id
        self.task = task
        self.state = SessionState.CONNECTING


class SessionManager:
    """Tracks active voice sessions with cleanup."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, task: PipelineTask) -> Session:
        session_id = str(uuid4())
        session = Session(session_id, task)
        self._sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session

    async def remove_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session and session.task:
            try:
                await session.task.cancel()
            except Exception as e:
                logger.warning(f"Error cancelling session {session_id}: {e}")
        logger.info(f"Session removed: {session_id}")

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def cleanup_all(self) -> None:
        tasks = [self.remove_session(sid) for sid in list(self._sessions)]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All sessions cleaned up")
