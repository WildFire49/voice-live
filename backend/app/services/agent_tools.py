import time

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.google.gemini_live import GeminiLiveLLMService
from pipecat.services.llm_service import FunctionCallParams

from app.services.chroma_service import ChromaService
from app.services.sql_executor import SQLExecutor


TOOL_SCHEMAS = ToolsSchema(
    standard_tools=[
        FunctionSchema(
            name="search_knowledge_base",
            description=(
                "Search the knowledge base for relevant SQL examples and business rules. "
                "Call this FIRST when the user asks any data or analytics question. "
                "Returns few-shot SQL examples and business rules to help formulate accurate queries."
            ),
            properties={
                "question": {
                    "type": "string",
                    "description": "The user's data question to search for relevant context",
                },
            },
            required=["question"],
        ),
        FunctionSchema(
            name="execute_sql",
            description=(
                "Execute a SQL query against the DuckDB database. "
                "Use the examples and business rules from search_knowledge_base to write accurate SQL. "
                "Always validate your SQL against the business rules before executing."
            ),
            properties={
                "sql": {
                    "type": "string",
                    "description": "The SQL query to execute (DuckDB dialect)",
                },
            },
            required=["sql"],
        ),
    ]
)


def register_tools(
    llm: GeminiLiveLLMService,
    chroma: ChromaService,
    sql_executor: SQLExecutor,
) -> None:
    """Register function call handlers on the LLM service."""

    async def handle_search_kb(params: FunctionCallParams):
        question = params.arguments.get("question", "")
        logger.info(f"[KB] START search_knowledge_base | query: {question[:100]}")
        t0 = time.perf_counter()
        try:
            result = await chroma.search_all(question)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(f"[KB] DONE  search_knowledge_base | {elapsed:.0f}ms | {len(result)} chars returned")
            await params.result_callback(result)
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error(f"[KB] FAIL  search_knowledge_base | {elapsed:.0f}ms | {e}")
            await params.result_callback(f"Knowledge base search failed: {e}")

    async def handle_execute_sql(params: FunctionCallParams):
        sql = params.arguments.get("sql", "")
        logger.info(f"[SQL] START execute_sql | query: {sql[:120]}")
        t0 = time.perf_counter()
        try:
            result = await sql_executor.execute(sql)
            elapsed = (time.perf_counter() - t0) * 1000
            logger.info(f"[SQL] DONE  execute_sql | {elapsed:.0f}ms | {len(result)} chars returned")
            await params.result_callback(result)
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error(f"[SQL] FAIL  execute_sql | {elapsed:.0f}ms | {e}")
            await params.result_callback(f"SQL execution failed: {e}")

    llm.register_function("search_knowledge_base", handle_search_kb, cancel_on_interruption=False)
    llm.register_function("execute_sql", handle_execute_sql, cancel_on_interruption=False)
    logger.info("Agent tools registered: search_knowledge_base, execute_sql")
