from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str
    host: str = "0.0.0.0"
    port: int = 8000
    gemini_model: str = "gemini-3.1-flash-live-preview"
    gemini_voice: str = "Charon"
    allowed_origins: list[str] = ["http://localhost:3000"]
    enable_silero_vad: bool = True

    # RAG Agent config
    chroma_host: str = ""
    chroma_port: int = 8000
    chroma_local_path: str = ""
    chroma_examples_collection: str = ""
    chroma_rules_collection: str = ""
    sql_api_url: str = ""
    sql_api_key: str = ""
    sql_connection_id: str = ""

    @property
    def agent_tools_enabled(self) -> bool:
        has_chroma = bool(self.chroma_host or self.chroma_local_path)
        return bool(has_chroma and self.sql_api_url)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
