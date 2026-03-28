import time

from loguru import logger

from app.retriever.result import RetrievalResult
from app.retriever.strategies.base import RetrieverStrategy


class RetrieverAgent:
    """Orchestrator that delegates to a pluggable retrieval strategy."""

    def __init__(self, strategy: RetrieverStrategy):
        self._strategy = strategy

    async def search(self, query: str) -> RetrievalResult:
        """Search for context relevant to the query."""
        t0 = time.perf_counter()
        result = await self._strategy.retrieve(query)
        elapsed = (time.perf_counter() - t0) * 1000

        logger.info(
            f"RetrieverAgent | {elapsed:.0f}ms | confidence={result.confidence:.2f} "
            f"| sources={result.sources} | low={result.is_low_confidence} "
            f"| {len(result.context)} chars"
        )
        return result
