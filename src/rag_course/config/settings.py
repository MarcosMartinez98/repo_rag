# src/rag_course/config/settings.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración global del sistema RAG.
    Todos los valores se leen del entorno o de un archivo .env.
    SecretStr encripta el valor en logs/repr, nunca lo expone en texto plano.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Cohere
    cohere_api_key: SecretStr = Field(..., description="API key de Cohere")
    cohere_llm_model: str = Field(
        default="command-r-plus-08-2024", description="Modelo LLM"
    )
    cohere_embed_model: str = Field(
        default="embed-multilingual-v3.0",
        description="Modelo de embeddings",
    )
    cohere_rerank_model: str = Field(default="rerank-multilingual-v3.0")

    # ChromaDB
    chroma_persist_directory: str = Field(default="./chroma_db")
    chroma_collection_name: str = Field(default="rag_course")

    # Chunking
    chunk_size: int = Field(default=512, ge=64, le=4096)
    chunk_overlap: int = Field(default=64, ge=0)
    parent_chunk_size: int = Field(default=2048)  # Módulo 3

    # Retrieval
    top_k_retrieval: int = Field(default=10)
    top_k_rerank: int = Field(default=4)


# Singleton global (importar desde aquí en toda la app)
settings = Settings()  # type: ignore[call-arg]
