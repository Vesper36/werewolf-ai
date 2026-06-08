"""API请求/响应的Pydantic模型"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


# ============================================================
# 游戏创建
# ============================================================

class CreateGameRequest(BaseModel):
    """创建游戏请求"""
    difficulty: str = Field(..., description="难度: beginner/intermediate/advanced/master")
    board_id: str = Field(..., description="板型ID, 如 'classic_guard'")
    human_seat: int = Field(default=1, ge=1, le=12, description="玩家座位号")


# ============================================================
# 玩家动作
# ============================================================

class PlayerActionRequest(BaseModel):
    """玩家动作请求"""
    action_type: str  # vote, seer_check, witch_save, witch_poison, guard_protect, etc.
    target_id: str | None = None
    second_target_id: str | None = None
    payload: dict[str, Any] | None = None


class SpeechRequest(BaseModel):
    """发言请求"""
    text: str = Field(..., min_length=1, max_length=2000)


class PoliceRegisterRequest(BaseModel):
    """警长竞选报名"""
    register: bool = True  # True=上警, False=退水


# ============================================================
# 游戏状态响应
# ============================================================

class PlayerPublic(BaseModel):
    """玩家公开信息"""
    id: str
    seat_number: int
    name: str
    is_human: bool
    is_alive: bool
    is_sheriff: bool
    is_revealed_idiot: bool


class PlayerPrivate(PlayerPublic):
    """玩家私有信息（仅自己可见）"""
    role: str | None = None
    faction: str | None = None
    has_antidote: bool | None = None
    has_poison: bool | None = None


class GameStateResponse(BaseModel):
    """游戏状态响应"""
    game_id: str
    board_id: str
    difficulty: str
    phase: str
    day_number: int
    is_first_night: bool
    sheriff_id: str | None
    winner: str | None
    players: list[PlayerPublic]
    human_player: PlayerPrivate | None = None


# ============================================================
# WebSocket消息
# ============================================================

class WSMessage(BaseModel):
    """WebSocket消息基类"""
    type: str
    data: dict[str, Any] = {}
    timestamp: float = 0.0


# ============================================================
# 设置
# ============================================================

class LLMSettings(BaseModel):
    """LLM配置"""
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""


class TTSSettings(BaseModel):
    """TTS配置"""
    provider: str = "openai"
    model: str = "tts-1"
    api_key: str = ""
    voice: str = "alloy"
    speed: float = Field(default=1.0, ge=0.8, le=1.5)


class STTSettings(BaseModel):
    """STT配置"""
    enabled: bool = False
    language: str = "zh-CN"


class AllSettings(BaseModel):
    """全部设置"""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    stt: STTSettings = Field(default_factory=STTSettings)


class ConnectionTestRequest(BaseModel):
    """连接测试请求"""
    provider: str
    model: str
    api_key: str
    base_url: str = ""


class ConnectionTestResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str
    latency_ms: float = 0.0


# ============================================================
# 板型信息
# ============================================================

class BoardInfo(BaseModel):
    """板型简要信息"""
    id: str
    name: str
    player_count: int
    has_police: bool
    description: str


class BoardDetail(BoardInfo):
    """板型详细信息"""
    god_roles: list[str]
    civilian_roles: list[str]
    wolf_roles: list[str]
    third_party_roles: list[str] = []
