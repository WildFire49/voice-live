import asyncio

from loguru import logger

from app.retriever.reranker import ScoredDocument
from app.retriever.result import RetrievalResult
from app.retriever.searchers.chroma_searcher import ChromaSearcher
from app.retriever.strategies.base import RetrieverStrategy

LOW_CONFIDENCE_THRESHOLD = 0.55


class SQLRetrieverStrategy(RetrieverStrategy):
    """Retrieval strategy for SQL query generation.

    Searches three ChromaDB collections in parallel:
    - examples: few-shot SQL query examples
    - rules: business rules for metric calculation
    - schema: table/view/column definitions with enum values
    """

    def __init__(
        self,
        examples_searcher: ChromaSearcher,
        rules_searcher: ChromaSearcher,
        schema_searcher: ChromaSearcher | None = None,
    ):
        self._examples = examples_searcher
        self._rules = rules_searcher
        self._schema = schema_searcher

    async def retrieve(self, query: str) -> RetrievalResult:
        # Search all collections in parallel
        tasks = [
            self._examples.search(query),
            self._rules.search(query),
        ]
        if self._schema:
            tasks.append(self._schema.search(query))

        results = await asyncio.gather(*tasks)

        example_docs: list[ScoredDocument] = results[0]
        rule_docs: list[ScoredDocument] = results[1]
        schema_docs: list[ScoredDocument] = results[2] if self._schema else []

        # Build formatted context
        sections = []
        sources = []

        if schema_docs:
            sections.append(
                "## Database Schema\n"
                + "\n---\n".join(d.text for d in schema_docs)
            )
            sources.append("schema")

        if example_docs:
            sections.append(
                "## Few-Shot SQL Examples\n"
                + "\n---\n".join(d.text for d in example_docs)
            )
            sources.append("examples")

        if rule_docs:
            sections.append(
                "## Business Rules\n"
                + "\n---\n".join(d.text for d in rule_docs)
            )
            sources.append("rules")

        # Confidence from best score across all results
        all_docs = example_docs + rule_docs + schema_docs
        best_score = max((d.final_score for d in all_docs), default=0.0)
        is_low = best_score < LOW_CONFIDENCE_THRESHOLD

        context = "\n\n".join(sections) if sections else "No relevant context found."

        if is_low:
            context = f"[LOW_CONFIDENCE]\n{context}"

        logger.info(
            f"SQLRetriever | confidence={best_score:.2f} low={is_low} "
            f"| examples={len(example_docs)} rules={len(rule_docs)} schema={len(schema_docs)}"
        )

        return RetrievalResult(
            context=context,
            confidence=best_score,
            is_low_confidence=is_low,
            sources=sources,
        )
