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

        llm = create_gemini_service(settings.google_api_key, gemini_config)

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
