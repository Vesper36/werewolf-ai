"""FastAPI 入口 — 完整游戏API"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..ai.provider import AIProviderConfig
from ..services.game_service import game_service
from ..tts import TTSConfig, TTSEngine
from .ws_manager import ws_manager


class AIConfigRequest(BaseModel):
    provider: str = Field(default="offline")
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.75, ge=0, le=2)
    timeout_seconds: float = Field(default=25, ge=3, le=120)


class StartGameRequest(BaseModel):
    board_id: str
    difficulty: str = "expert"
    human_name: str = "你"
    human_role: str | None = "seer"
    ai: AIConfigRequest = Field(default_factory=AIConfigRequest)


class NightActionRequest(BaseModel):
    action_type: str = "seer_check"  # wolf_kill, seer_check, witch_save, etc.
    target_seat: int | None = None
    second_target_seat: int | None = None


class SpeechRequest(BaseModel):
    text: str


class VoteRequest(BaseModel):
    target_seat: int


class TargetRequest(BaseModel):
    target_seat: int


app = FastAPI(title="AI狼人杀·大师竞技场", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_provider_config(payload: AIConfigRequest) -> AIProviderConfig:
    return AIProviderConfig(
        provider=payload.provider,
        base_url=payload.base_url,
        api_key=payload.api_key,
        model=payload.model,
        temperature=payload.temperature,
        timeout_seconds=payload.timeout_seconds,
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/boards")
async def boards() -> dict[str, Any]:
    return {"boards": game_service.list_boards()}


@app.post("/api/settings/test")
async def test_settings(payload: AIConfigRequest) -> dict[str, Any]:
    try:
        return await game_service.test_provider(_to_provider_config(payload))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败: {exc}") from exc


@app.post("/api/games")
async def create_game(payload: StartGameRequest) -> dict[str, Any]:
    try:
        return game_service.create_game(
            board_id=payload.board_id,
            difficulty=payload.difficulty,
            human_name=payload.human_name,
            human_role=payload.human_role,
            provider_config=_to_provider_config(payload.ai),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/games/{game_id}")
async def get_game(game_id: str) -> dict[str, Any]:
    try:
        return game_service.get_game(game_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---- 夜晚流程 ----

@app.post("/api/games/{game_id}/night/start")
async def start_night(game_id: str) -> dict[str, Any]:
    """开始夜晚流程（首夜自动执行全部首夜阶段，非首夜执行常规夜晚）"""
    try:
        runtime = game_service._get_runtime(game_id)
        if runtime.state.is_first_night:
            return await game_service.process_first_night(game_id)
        return await game_service.process_night(game_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/night/action")
async def submit_night_action(game_id: str, payload: NightActionRequest) -> dict[str, Any]:
    """人类玩家提交夜晚行动"""
    try:
        return await game_service.submit_human_night_action(
            game_id, payload.action_type,
            payload.target_seat, payload.second_target_seat,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---- 白天流程 ----

@app.post("/api/games/{game_id}/day/start")
async def start_day(game_id: str) -> dict[str, Any]:
    """开始白天流程"""
    try:
        return await game_service.process_day_phases(game_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/speech")
async def human_speech(game_id: str, payload: SpeechRequest) -> dict[str, Any]:
    """人类玩家提交发言"""
    try:
        return game_service.submit_human_speech(game_id, payload.text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/ai-speeches")
async def ai_speeches(game_id: str) -> dict[str, Any]:
    """生成AI发言"""
    try:
        return await game_service.run_ai_speeches(game_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/vote")
async def human_vote(game_id: str, payload: VoteRequest) -> dict[str, Any]:
    """人类玩家提交投票"""
    try:
        return game_service.submit_human_vote(game_id, payload.target_seat)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/votes/resolve")
async def resolve_votes(game_id: str) -> dict[str, Any]:
    """结算所有AI投票并处理放逐结果"""
    try:
        return await game_service.resolve_votes(game_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---- 特殊行动 ----

@app.post("/api/games/{game_id}/self-explode")
async def self_explode(game_id: str, payload: TargetRequest) -> dict[str, Any]:
    """狼人自爆"""
    try:
        return game_service.self_explode(game_id, payload.target_seat)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/hunter-shoot")
async def hunter_shoot(game_id: str, payload: TargetRequest) -> dict[str, Any]:
    """猎人开枪"""
    try:
        return game_service.hunter_shoot(game_id, payload.target_seat)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/knight-duel")
async def knight_duel(game_id: str, payload: TargetRequest) -> dict[str, Any]:
    """骑士决斗"""
    try:
        return game_service.knight_duel(game_id, payload.target_seat)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---- TTS 语音合成 ----

class TTSRequest(BaseModel):
    text: str
    provider: str = "edge"
    voice: str = "alloy"
    speed: float = 1.0

@app.post("/api/tts/synthesize")
async def synthesize_speech(payload: TTSRequest):
    """将文字转为语音音频"""
    try:
        config = TTSConfig(
            provider=payload.provider,
            voice=payload.voice,
            speed=payload.speed,
        )
        engine = TTSEngine(config)
        audio = await engine.synthesize(payload.text)
        if audio is None:
            raise HTTPException(status_code=500, detail="语音合成失败")
        from fastapi.responses import Response
        return Response(content=audio, media_type="audio/mpeg")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---- WebSocket ----

@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str):
    """游戏实时通信"""
    await ws_manager.connect(game_id, websocket)
    try:
        while True:
            # 接收客户端消息（心跳/确认等）
            data = await websocket.receive_text()
            # 当前只做心跳维持连接，消息交互通过REST
            if data == "ping":
                await ws_manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(game_id, websocket)
