from google.genai.types import ThinkingConfig
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.google.gemini_live import GeminiLiveLLMService

from app.config.gemini import GeminiConfig


def create_gemini_service(
    api_key: str,
    config: GeminiConfig,
    tools: ToolsSchema | None = None,
) -> GeminiLiveLLMService:
    """Factory function to create a configured GeminiLiveLLMService."""
    return GeminiLiveLLMService(
        api_key=api_key,
        settings=GeminiLiveLLMService.Settings(
            model=config.model,
            voice=config.voice,
            thinking=ThinkingConfig(thinking_budget=config.thinking_budget),
        ),
        system_instruction=config.system_instruction,
        tools=tools,
    )
