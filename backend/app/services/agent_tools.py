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
        logger.info(f"Tool call: search_knowledge_base({question[:80]})")
        try:
            result = await chroma.search_all(question)
            await params.result_callback(result)
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            await params.result_callback(f"Knowledge base search failed: {e}")

    async def handle_execute_sql(params: FunctionCallParams):
        sql = params.arguments.get("sql", "")
        logger.info(f"Tool call: execute_sql({sql[:80]})")
        try:
            result = await sql_executor.execute(sql)
            await params.result_callback(result)
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            await params.result_callback(f"SQL execution failed: {e}")

    llm.register_function("search_knowledge_base", handle_search_kb)
    llm.register_function("execute_sql", handle_execute_sql)
    logger.info("Agent tools registered: search_knowledge_base, execute_sql")
