from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str
    host: str = "0.0.0.0"
    port: int = 8000
    gemini_model: str = "gemini-3.1-flash-live-preview"
    gemini_voice: str = "Charon"
    allowed_origins: list[str] = ["http://localhost:3000"]
    enable_silero_vad: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
