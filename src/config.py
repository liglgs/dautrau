from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "MedReview VMEC-03"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3100,http://127.0.0.1:3100"
    )

    # LLM
    openai_api_key: str = ""
    gemini_api_key: str = ""
    gemini_api_key_2: str = ""
    gemini_api_key_3: str = ""
    gemini_api_key_4: str = ""
    gemini_api_key_5: str = ""
    gemini_api_key_6: str = ""
    gemini_api_key_7: str = ""
    gemini_api_key_8: str = ""
    gemini_base_url: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    model_provider: Literal["auto", "openai_compatible", "openai", "gemini"] = "auto"
    model_name: str = ""
    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    model_input_usd_per_million: float | None = Field(default=None, ge=0)
    model_output_usd_per_million: float | None = Field(default=None, ge=0)

    @property
    def gemini_keys(self) -> list[str]:
        raw = [
            self.gemini_api_key,
            self.gemini_api_key_2,
            self.gemini_api_key_3,
            self.gemini_api_key_4,
            self.gemini_api_key_5,
            self.gemini_api_key_6,
            self.gemini_api_key_7,
            self.gemini_api_key_8,
        ]
        return [k.strip() for k in raw if k and k.strip()]

    # MVP điều tra an toàn thuốc (P-066)
    investigator_token: str = ""
    reviewer_token: str = ""
    mvp_db_path: str = "data/mvp.sqlite3"
    mvp_evidence_mode: Literal["fixture", "person3_demo", "person3"] = "fixture"
    mvp_dictionary_path: str = "data/dictionaries/mvp_candidates_2026_10_02.json"
    mvp_person3_demo_scenario: Literal[
        "match", "route_mismatch", "missing_scope", "imprecise_null",
        "fake_quote", "contradiction", "ambiguous_brand", "faers_only",
    ] = "match"
    mvp_source_mode: Literal["fixture", "live"] = "fixture"
    mvp_pubmed_mode: Literal["api", "local"] = "api"
    mvp_pubmed_corpus_root: str = "data/pubmed-local"
    mvp_snapshot_root: str = "data/snapshots"
    mvp_source_max_documents: int = Field(default=5, ge=1, le=20)

    # Database
    database_url: str = "postgresql+psycopg://medreview:medreview@localhost:5432/medreview"
    session_cookie_secure: bool = False
    research_token: str = ""

    # Kho ELT (PostgreSQL) — mặc định suy ra từ database_url với tên csdl vigilens_elt
    elt_database_url: str = ""

    # Vector Store / RAG
    rag_enabled: bool = True
    rag_chroma_dir: str = "./data/chroma"
    rag_collection: str = "vigilens_docs"
    rag_embedding_provider: Literal["auto", "gemini", "hash"] = "auto"
    rag_embedding_model: str = "gemini-embedding-001"
    rag_top_k: int = Field(default=6, ge=1, le=50)

    @field_validator("database_url")
    @classmethod
    def modern_postgres_driver(cls, value: str) -> str:
        return value.replace("postgresql://", "postgresql+psycopg://", 1) if value.startswith("postgresql://") else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
