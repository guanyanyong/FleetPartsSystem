"""全局配置：通过 pydantic-settings 从环境变量 / .env 读取。"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（config.py -> core -> app -> backend）
BASE_DIR: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """应用配置项，字段名与环境变量名一致（不区分大小写）。"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------- 应用 ----------------
    APP_NAME: str = "FleetPartsSystem"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    API_V1_PREFIX: str = "/api/v1"

    # ---------------- 数据库 ----------------
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "fleet_parts"
    DB_POOL_SIZE: int = Field(default=10, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0)
    DB_ECHO: bool = False
    DB_POOL_RECYCLE: int = Field(default=3600, description="连接回收时间（秒）")

    # ---------------- JWT ----------------
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ---------------- 文件存储 ----------------
    UPLOAD_DIR: str = "./uploads"
    QRCODE_DIR: str = "./uploads/qrcode"
    BARCODE_DIR: str = "./uploads/barcode"

    # ---------------- 跨域 ----------------
    # 环境变量中用英文逗号分隔，通过 cors_origins 属性获取列表
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ---------------- 日志 ----------------
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"

    # ---------------- 派生属性 ----------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """异步 MySQL 连接串（asyncmy 驱动）。"""
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+asyncmy://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def cors_origins(self) -> list[str]:
        """把逗号分隔的字符串转成列表，供 CORSMiddleware 使用。"""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def log_dir(self) -> Path:
        """日志目录（相对路径以 backend/ 为基准）。"""
        path = Path(self.LOG_DIR)
        return path if path.is_absolute() else BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    """带缓存的配置实例，测试时可 get_settings.cache_clear() 后重新获取。"""
    return Settings()


settings: Settings = get_settings()

__all__ = ["BASE_DIR", "Settings", "get_settings", "settings"]
