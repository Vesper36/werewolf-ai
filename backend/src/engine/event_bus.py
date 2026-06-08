"""事件总线 — 解耦引擎与通信层"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable
import time


@dataclass
class GameEvent:
    """游戏事件"""
    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


# 事件处理器类型
EventHandler = Callable[[GameEvent], Awaitable[None]]


class EventBus:
    """事件总线"""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[GameEvent] = []

    def on(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器"""
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """移除事件处理器"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """发布事件"""
        event = GameEvent(event_type=event_type, data=data or {})
        self._history.append(event)

        handlers = self._handlers.get(event_type, [])
        # 同时也触发通配符处理器
        wildcard_handlers = self._handlers.get("*", [])

        all_handlers = handlers + wildcard_handlers
        if all_handlers:
            await asyncio.gather(
                *[handler(event) for handler in all_handlers],
                return_exceptions=True,
            )

    def get_history(self, event_type: str | None = None) -> list[GameEvent]:
        """获取事件历史"""
        if event_type:
            return [e for e in self._history if e.event_type == event_type]
        return list(self._history)

    def clear(self) -> None:
        """清空所有处理器和历史"""
        self._handlers.clear()
        self._history.clear()
