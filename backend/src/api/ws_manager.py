"""WebSocket 实时通信管理"""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """管理每个游戏房间的 WebSocket 连接"""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, game_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(game_id, []).append(ws)

    def disconnect(self, game_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(game_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(game_id, None)

    async def broadcast(self, game_id: str, data: dict[str, Any]) -> None:
        """广播消息到指定游戏房间的所有连接"""
        conns = self._connections.get(game_id, [])
        if not conns:
            return
        payload = json.dumps(data, ensure_ascii=False, default=str)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(game_id, ws)

    async def send_personal(self, ws: WebSocket, data: dict[str, Any]) -> None:
        """发送私有消息给特定连接"""
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
        except Exception:
            pass

    @property
    def active_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())


ws_manager = ConnectionManager()
