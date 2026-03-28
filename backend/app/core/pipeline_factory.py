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
            from app.services.agent_tools import register_tools
            from app.services.chroma_service import ChromaService
            from app.services.sql_executor import SQLExecutor

            chroma = ChromaService(
                examples_collection=settings.chroma_examples_collection,
                rules_collection=settings.chroma_rules_collection,
                local_path=settings.chroma_local_path,
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            sql_executor = SQLExecutor(
                api_url=settings.sql_api_url,
                api_key=settings.sql_api_key,
                connection_id=settings.sql_connection_id,
            )
            register_tools(llm, chroma, sql_executor)
            logger.info("Agent mode: RAG tools registered")

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
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        logger.info(f"Pipeline created with model={gemini_config.model}")
        return task
