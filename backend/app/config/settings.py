"""
应用配置管理模块

使用 pydantic-settings 进行配置管理，支持：
1. 自动从环境变量读取配置
2. 类型验证和转换
3. 默认值设置
4. 配置文档化
"""
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


class Settings(BaseSettings):
    """
    应用配置类

    配置项会自动从以下来源读取（优先级从高到低）：
    1. 环境变量
    2. .env 文件
    3. 默认值
    """

    # ==================== AI 服务配置 ====================

    # 主模型 API (MiMo)
    MAIN_API_KEY: str | None = Field(default=None, description="主模型 API Key")
    MAIN_BASE_URL: str | None = Field(default=None, description="主模型 Base URL")
    MAIN_MODEL_NAME: str | None = Field(default="MiMo-V2.5-Pro", description="主模型名称")

    # 子模型 API (MiniMax)
    SUB_API_KEY: str | None = Field(default=None, description="子模型 API Key")
    SUB_BASE_URL: str | None = Field(default=None, description="子模型 Base URL")
    SUB_MODEL_NAME: str | None = Field(default="MiniMax-m2.7", description="子模型名称")

    # ==================== 数据库配置 ====================

    MYSQL_HOST: str | None = Field(default="localhost", description="MySQL主机地址")
    MYSQL_PORT: int = Field(default=3306, description="MySQL端口")
    MYSQL_USER: str | None = Field(default="root", description="MySQL用户名")
    MYSQL_PASSWORD: str | None = Field(default="", description="MySQL密码")
    MYSQL_DATABASE: str | None = Field(default="its_db", description="MySQL数据库名")
    MYSQL_CHARSET: str = Field(default="utf8mb4", description="MySQL字符集")
    MYSQL_CONNECT_TIMEOUT: int = Field(default=10, description="MySQL连接超时（秒）")
    MYSQL_MAX_CONNECTIONS: int = Field(default=5, description="MySQL最大连接数")

    # ==================== 外部服务配置 ====================

    # 知识库服务
    KNOWLEDGE_BASE_URL: str | None = Field(
        default=None,
        description="知识库服务URL"
    )

    # 通义千问搜索服务
    DASHSCOPE_BASE_URL: str | None = Field(
        default=None,
        description="通义千问 DashScope Base URL"
    )
    DASHSCOPE_API_KEY: str | None = Field(
        default=None,
        description="通义千问 DashScope API Key"
    )

    # 百度地图服务
    BAIDUMAP_AK: str | None = Field(
        default=None,
        description="百度地图 AK (Access Key)"
    )

    # ==================== Langfuse 可观测性配置 ====================

    LANGFUSE_PUBLIC_KEY: str | None = Field(
        default=None,
        description="Langfuse Public Key"
    )
    LANGFUSE_SECRET_KEY: str | None = Field(
        default=None,
        description="Langfuse Secret Key"
    )
    LANGFUSE_HOST: str | None = Field(
        default="http://localhost:3001",
        description="Langfuse Server URL"
    )

    # ==================== JWT 认证配置 ====================

    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="JWT 签名密钥"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT 签名算法"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access Token 有效期（分钟）"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh Token 有效期（天）"
    )

    # ==================== CORS 配置 ====================

    CORS_ALLOW_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="CORS 允许的来源，逗号分隔"
    )

    # ==================== Pydantic Settings 配置 ====================

    model_config = SettingsConfigDict(
        # 计算.env文件的绝对路径：config目录的父目录(app目录)下的.env
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",          # .env文件编码
        case_sensitive=True,                 # 环境变量名大小写敏感
        extra="ignore",                      # 忽略额外的环境变量
        validate_default=True,               # 验证默认值
    )

    # ====================  ====================
    @model_validator(mode='after')
    def check_ai_service_configuration(self) -> Self:
        """
        验证器：在配置加载完成后自动执行。
        如果需要强制至少配置一个 AI 服务，可以在这里抛出 ValueError
        """
        # 注意：这里 self 已经是实例化后的模型对象
        has_service = any([
            self.MAIN_API_KEY and self.MAIN_BASE_URL,
            self.SUB_API_KEY and self.SUB_BASE_URL
        ])

        if not has_service:
            raise ValueError("必须配置至少一个 AI 服务 (主模型或子模型)")

        # JWT 密钥安全检查
        import logging
        _logger = logging.getLogger("config")
        INSECURE_DEFAULTS = {"change-me-in-production", "secret", "test", ""}
        if self.JWT_SECRET_KEY in INSECURE_DEFAULTS:
            _logger.warning(
                "⚠️  JWT_SECRET_KEY 使用了不安全的默认值，"
                "请在 .env 中配置一个至少 32 字符的随机密钥。"
                "生产环境中此配置将导致安全漏洞。"
            )

        return self



# 创建全局配置实例
settings = Settings()

