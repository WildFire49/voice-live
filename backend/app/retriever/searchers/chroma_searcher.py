import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

from app.retriever.reranker import ScoredDocument, rerank

ARCTIC_MODEL = "Snowflake/snowflake-arctic-embed-m"


class ChromaSearcher:
    """Generic ChromaDB searcher with hybrid semantic+keyword reranking."""

    def __init__(
        self,
        collection_name: str,
        client: chromadb.ClientAPI,
        embedding_function: SentenceTransformerEmbeddingFunction | None = None,
    ):
        ef = embedding_function or SentenceTransformerEmbeddingFunction(
            model_name=ARCTIC_MODEL,
        )
        self._collection = client.get_collection(collection_name, embedding_function=ef)
        self._name = collection_name
        logger.info(f"ChromaSearcher ready: {collection_name}")

    @property
    def name(self) -> str:
        return self._name

    async def search(
        self,
        query: str,
        n_candidates: int = 10,
        n_results: int = 5,
    ) -> list[ScoredDocument]:
        """Search the collection with hybrid reranking.

        Fetches n_candidates by semantic similarity, then reranks using
        blended semantic + keyword scoring, returning top n_results.
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=n_candidates,
            include=["documents", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return []

        return rerank(query, documents, distances, n_results=n_results)

    async def search_raw(self, query: str, n_results: int = 5) -> str:
        """Simple search returning joined text (backward-compat helper)."""
        scored = await self.search(query, n_candidates=n_results, n_results=n_results)
        if not scored:
            return f"No relevant results found in {self._name}."
        return "\n---\n".join(doc.text for doc in scored)


def create_chroma_client(
    local_path: str = "",
    host: str = "",
    port: int = 8000,
) -> chromadb.ClientAPI:
    """Create a ChromaDB client (local or remote)."""
    if host:
        client = chromadb.HttpClient(host=host, port=port)
        logger.info(f"ChromaDB remote client: {host}:{port}")
    elif local_path:
        client = chromadb.PersistentClient(path=local_path)
        logger.info(f"ChromaDB local client: {local_path}")
    else:
        raise ValueError("Either host or local_path must be provided")
    return client
