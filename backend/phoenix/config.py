from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "1.0.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PHOENIX_", env_file=".env", extra="ignore")

    data_dir: Path = Path("./data")
    database_url: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Sandbox execution of COBOL: docker | queue | disabled
    cobol_executor: str = "docker"
    runner_image: str = "cobol-phoenix-runner:latest"
    queue_dir: Path | None = None

    # Import limits
    max_upload_mb: int = 25
    max_uncompressed_mb: int = 100
    max_files: int = 2000
    max_file_kb: int = 2048
    max_compression_ratio: int = 100
    allow_github_import: bool = True
    allow_local_import: bool = False
    local_import_root: Path | None = None

    # Verification
    max_cases: int = 220
    mutation_limit: int = 60
    worker_threads: int = 2

    # Optional LLM provider for explanations: none | openai-compatible | anthropic
    llm_provider: str = "none"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_s: float = 30.0

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.data_dir / 'phoenix.db').resolve()}"

    @property
    def queue_path(self) -> Path:
        return self.queue_dir or (self.data_dir / "queue")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s
