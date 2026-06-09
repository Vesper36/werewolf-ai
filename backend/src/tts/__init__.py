"""TTS 文字转语音 — 多提供方支持"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx


@dataclass
class TTSConfig:
    provider: str = "edge"  # "openai" | "edge" | "offline"
    model: str = "tts-1"
    voice: str = "alloy"
    speed: float = 1.0
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"

    @property
    def enabled(self) -> bool:
        return self.provider != "offline"


_CACHE: dict[str, bytes] = {}


class TTSEngine:

    def __init__(self, config: TTSConfig | None = None) -> None:
        self.config = config or TTSConfig()

    async def synthesize(self, text: str) -> bytes | None:
        if not text.strip():
            return None
        key = self._cache_key(text)
        if key in _CACHE:
            return _CACHE[key]
        try:
            audio = None
            if self.config.provider == "openai":
                audio = await self._openai_tts(text)
            elif self.config.provider == "edge":
                audio = await self._edge_tts(text)
            if audio:
                _CACHE[key] = audio
                if len(_CACHE) > 200:
                    _CACHE.pop(next(iter(_CACHE)))
            return audio
        except Exception:
            return None

    async def _openai_tts(self, text: str) -> bytes | None:
        url = f"{self.config.base_url.rstrip('/')}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model, "input": text,
            "voice": self.config.voice, "speed": self.config.speed,
            "response_format": "mp3",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content

    async def _edge_tts(self, text: str) -> bytes | None:
        voice = "zh-CN-XiaoxiaoNeural" if self.config.voice == "alloy" else "zh-CN-YunxiNeural"
        ssml = (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
            f'<voice name="{voice}"><prosody rate="{self.config.speed}">{text}</prosody>'
            '</voice></speak>'
        )
        url = (
            "https://speech.platform.bing.com/consumer/speech/synthesize/"
            "readaloud/edge/v1?TrustedClientToken=6A5AA1D4EAFF4E9FB37E23D68491D6F4"
        )
        headers = {
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            "User-Agent": "Mozilla/5.0",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, content=ssml, headers=headers)
            resp.raise_for_status()
            return resp.content

    def _cache_key(self, text: str) -> str:
        raw = f"{self.config.provider}:{self.config.voice}:{self.config.speed}:{text}"
        return hashlib.md5(raw.encode()).hexdigest()
