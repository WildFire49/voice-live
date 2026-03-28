import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

ARCTIC_MODEL = "Snowflake/snowflake-arctic-embed-m"


class ChromaService:
    """Queries ChromaDB for few-shot examples and business rules."""

    def __init__(
        self,
        examples_collection: str,
        rules_collection: str,
        local_path: str = "",
        host: str = "",
        port: int = 8000,
    ):
        arctic_ef = SentenceTransformerEmbeddingFunction(model_name=ARCTIC_MODEL)

        if local_path:
            self._client = chromadb.PersistentClient(path=local_path)
            logger.info(f"ChromaDB local: {local_path} (Arctic embeddings)")
        else:
            self._client = chromadb.HttpClient(host=host, port=port)
            logger.info(f"ChromaDB remote: {host}:{port}")

        self._examples = self._client.get_collection(
            examples_collection, embedding_function=arctic_ef,
        )
        self._rules = self._client.get_collection(
            rules_collection, embedding_function=arctic_ef,
        )

    async def search_examples(self, question: str, n_results: int = 5) -> str:
        """Search few-shot SQL examples relevant to the question."""
        results = self._examples.query(query_texts=[question], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        if not docs:
            return "No relevant examples found."
        return "\n---\n".join(docs)

    async def search_rules(self, question: str, n_results: int = 5) -> str:
        """Search business rules relevant to the question."""
        results = self._rules.query(query_texts=[question], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        if not docs:
            return "No relevant business rules found."
        return "\n---\n".join(docs)

    async def search_all(self, question: str, n_results: int = 5) -> str:
        """Search both examples and rules, return combined context."""
        examples = await self.search_examples(question, n_results)
        rules = await self.search_rules(question, n_results)
        return f"## Few-Shot SQL Examples\n{examples}\n\n## Business Rules\n{rules}"
