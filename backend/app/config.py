from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str = "sqlite:///./nexusai.db"
    allowed_origins: str = "http://localhost:3000"
    # Google Gemini — powers every AI narration and sentiment classification.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_timeout_seconds: int = 30
    jwt_secret_key: str = "nexusai-sme-growth-os-super-secret-key-2026"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days
    debug: bool = True

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
