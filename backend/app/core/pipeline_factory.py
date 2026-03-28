from loguru import logger
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.transports.base_transport import BaseTransport

from app.config.gemini import GeminiConfig
from app.config.settings import Settings
from app.services.gemini_service import create_gemini_service
from app.services.vad_service import create_vad_analyzer


class PipelineFactory:
    """Creates configured Pipecat pipelines for voice sessions."""

    @staticmethod
    def create(
        transport: BaseTransport,
        settings: Settings,
        gemini_config: GeminiConfig | None = None,
    ) -> PipelineTask:
        if gemini_config is None:
            gemini_config = GeminiConfig.from_settings(settings)

        # Build tools schema if agent mode is enabled
        tools = None
        if settings.agent_tools_enabled:
            from app.services.agent_tools import TOOL_SCHEMAS
            tools = TOOL_SCHEMAS

        llm = create_gemini_service(settings.google_api_key, gemini_config, tools=tools)

        # Register function call handlers if agent mode
        if settings.agent_tools_enabled:
            from app.retriever import RetrieverAgent
            from app.retriever.searchers.chroma_searcher import (
                ChromaSearcher,
                create_chroma_client,
            )
            from app.retriever.strategies.sql_strategy import SQLRetrieverStrategy
            from app.services.agent_tools import register_tools
            from app.services.sql_executor import SQLExecutor

            # Create shared ChromaDB client
            chroma_client = create_chroma_client(
                local_path=settings.chroma_local_path,
                host=settings.chroma_host,
                port=settings.chroma_port,
            )

            # Create searchers for each collection
            examples_searcher = ChromaSearcher(
                settings.chroma_examples_collection, chroma_client,
            )
            rules_searcher = ChromaSearcher(
                settings.chroma_rules_collection, chroma_client,
            )
            schema_searcher = None
            if settings.chroma_schema_collection:
                schema_searcher = ChromaSearcher(
                    settings.chroma_schema_collection, chroma_client,
                )

            # Assemble retriever with SQL strategy
            strategy = SQLRetrieverStrategy(
                examples_searcher=examples_searcher,
                rules_searcher=rules_searcher,
                schema_searcher=schema_searcher,
            )
            retriever = RetrieverAgent(strategy)

            sql_executor = SQLExecutor(
                api_url=settings.sql_api_url,
                api_key=settings.sql_api_key,
                connection_id=settings.sql_connection_id,
            )
            register_tools(llm, retriever, sql_executor)
            logger.info("Agent mode: RetrieverAgent with SQLRetrieverStrategy registered")

        user_params = LLMUserAggregatorParams()
        if settings.enable_silero_vad:
            vad = create_vad_analyzer()
            user_params = LLMUserAggregatorParams(vad_analyzer=vad)
            logger.info("Silero VAD enabled")
        else:
            logger.info("Silero VAD disabled — relying on Gemini server-side VAD")

        context = LLMContext()
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
            context,
            user_params=user_params,
        )

        pipeline = Pipeline(
            [
                transport.input(),
                user_aggregator,
                llm,
                transport.output(),
                assistant_aggregator,
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        logger.info(f"Pipeline created with model={gemini_config.model}")
        return task
