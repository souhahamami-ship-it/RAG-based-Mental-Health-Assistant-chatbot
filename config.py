"""
Centralized, validated configuration.
Fail fast at startup if required secrets are missing, instead of failing
on the first request.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    groq_timeout_s: float = float(os.getenv("GROQ_TIMEOUT_S", "20"))

    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500")
        )
    )

    data_dir: str = os.getenv("DATA_DIR", "data")

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    reranker_model: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    retrieval_k: int = int(os.getenv("RETRIEVAL_K", "10"))
    final_k: int = int(os.getenv("FINAL_K", "3"))
    # Chunks scoring below this after reranking are dropped rather than
    # force-fed to the model as "relevant knowledge".
    min_rerank_score: float = float(os.getenv("MIN_RERANK_SCORE", "-2.0"))

    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "10"))

    # Session store
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 2)))  # 2h
    session_sweep_interval_s: int = int(os.getenv("SESSION_SWEEP_INTERVAL_S", "300"))
    max_active_sessions: int = int(os.getenv("MAX_ACTIVE_SESSIONS", "5000"))

    max_message_chars: int = int(os.getenv("MAX_MESSAGE_CHARS", "4000"))

    def validate(self) -> None:
        missing = []
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


settings = Settings()
