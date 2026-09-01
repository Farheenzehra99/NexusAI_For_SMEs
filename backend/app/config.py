from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str = "sqlite:///./nexusai.db"
    allowed_origins: str = "http://localhost:3000"
    # Google Gemini — powers every AI narration and sentiment classification.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    llm_timeout_seconds: int = 30
    debug: bool = True

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
