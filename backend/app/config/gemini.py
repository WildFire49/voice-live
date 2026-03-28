from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiConfig:
    model: str
    voice: str
    system_instruction: str = "You are a helpful voice assistant."
    thinking_budget: int = 0

    @classmethod
    def from_settings(cls, settings) -> "GeminiConfig":
        return cls(model=settings.gemini_model, voice=settings.gemini_voice)
