"""FastAPI 入口。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..ai.provider import AIProviderConfig
from ..services.game_service import game_service


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
    target_seat: int | None = None


class SpeechRequest(BaseModel):
    text: str


class VoteRequest(BaseModel):
    target_seat: int


app = FastAPI(title="AI狼人杀·大师竞技场", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/games/{game_id}")
async def get_game(game_id: str) -> dict[str, Any]:
    try:
        return game_service.get_game(game_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/night")
async def resolve_night(game_id: str, payload: NightActionRequest) -> dict[str, Any]:
    try:
        return await game_service.resolve_night(game_id, payload.target_seat)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/ai-speeches")
async def ai_speeches(game_id: str) -> dict[str, Any]:
    try:
        return await game_service.run_ai_speeches(game_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/speech")
async def human_speech(game_id: str, payload: SpeechRequest) -> dict[str, Any]:
    try:
        return game_service.submit_human_speech(game_id, payload.text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/games/{game_id}/vote")
async def vote(game_id: str, payload: VoteRequest) -> dict[str, Any]:
    try:
        return game_service.resolve_vote(game_id, payload.target_seat)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
