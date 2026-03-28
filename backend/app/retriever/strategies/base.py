from abc import ABC, abstractmethod

from app.retriever.result import RetrievalResult


class RetrieverStrategy(ABC):
    """Base class for retrieval strategies."""

    @abstractmethod
    async def retrieve(self, query: str) -> RetrievalResult:
        """Retrieve relevant context for the given query."""
