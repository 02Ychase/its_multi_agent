from pydantic_settings import BaseSettings,SettingsConfigDict
import os

class Settings(BaseSettings):
    API_KEY: str = os.environ.get("API_KEY")
    BASE_URL: str = os.environ.get("BASE_URL")
    MODEL: str = os.environ.get("MODEL")
    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL")

    
    # knowledge/config
    KNOWLEDGE_BASE_URL:str=os.environ.get("KNOWLEDGE_BASE_URL")

    _current_dir = os.path.dirname(os.path.abspath(__file__))
    # knowledge
    _project_root = os.path.dirname(_current_dir)
    
    VECTOR_STORE_PATH: str = os.path.join(_project_root, "chroma_kb1")
    
    # Default directories
    CRAWL_OUTPUT_DIR: str = os.path.join(_project_root, "data", "crawl")
    # Using 'data/crawl' as the default location for markdown files
    MD_FOLDER_PATH: str = CRAWL_OUTPUT_DIR
    TMP_MD_FOLDER_PATH:str= os.path.join(_project_root, "data", "tmp")
    # Text splitting configuration
    CHUNK_SIZE: int = 3000
    CHUNK_OVERLAP: int = 200

    # Retrieval configuration
    TOP_ROUGH: int = 50
    TOP_FINAL: int = 5

    # BM25 retrieval configuration
    TOP_K_BM25: int = 10

    # HyDE configuration
    HYDE_ENABLED: bool = True

    # Reranker configuration
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=os.path.join(_project_root, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# 必须要实例化
settings = Settings()
