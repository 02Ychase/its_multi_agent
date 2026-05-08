from pydantic_settings import BaseSettings,SettingsConfigDict
import os

class Settings(BaseSettings):
    # LLM 配置
    API_KEY: str = os.environ.get("API_KEY")
    BASE_URL: str = os.environ.get("BASE_URL")
    MODEL: str = os.environ.get("MODEL")

    # 嵌入模型配置（独立于LLM）
    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL")
    EMBEDDING_API_KEY: str = os.environ.get("EMBEDDING_API_KEY")
    EMBEDDING_BASE_URL: str = os.environ.get("EMBEDDING_BASE_URL")

    
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
    TOP_K_TITLE: int = 5

    # BM25 retrieval configuration
    TOP_K_BM25: int = 10

    # HyDE configuration
    HYDE_ENABLED: bool = True

    # Reranker configuration
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_ENABLED: bool = True

    # Upload validation
    MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024  # 20MB
    UPLOAD_ALLOWED_EXTENSIONS: str = ".md,.txt,.docx,.pdf"

    # MySQL configuration
    MYSQL_HOST: str = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.environ.get("MYSQL_DATABASE", "its_db")

    model_config = SettingsConfigDict(
        env_file=os.path.join(_project_root, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# 必须要实例化
settings = Settings()
