"""应用配置"""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用设置 -- 支持环境变量和.env文件"""

    # 服务
    app_name: str = "AI狼人杀 -- 大师竞技场"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # 数据库
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/werewolf"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # 默认LLM配置
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o"
    default_llm_api_key: str = ""
    default_llm_base_url: str = ""

    # 默认TTS配置
    default_tts_provider: str = "openai"
    default_tts_model: str = "tts-1"
    default_tts_api_key: str = ""
    default_tts_voice: str = "alloy"

    # 游戏设置
    speech_timeout: int = 120          # 发言超时（秒）
    typing_speed_min: float = 3.0      # 最低打字速度（字/秒）
    typing_speed_max: float = 5.0      # 最高打字速度（字/秒）

    # AI降级行为
    ai_fallback_enabled: bool = True   # API失败时启用降级
    ai_request_timeout: int = 30       # LLM请求超时（秒）

    model_config = {"env_file": ".env", "env_prefix": "WEREWOLF_"}


settings = Settings()
