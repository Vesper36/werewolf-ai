"""板子配置模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .role import Role


@dataclass
class BoardSlot:
    """座位配置"""
    pool: str  # "good_god" | "good_civilian" | "wolf" | "special"
    candidates: list[str] = field(default_factory=list)  # 可选角色(固定角色时只有一个)


@dataclass
class BoardConfig:
    """板子配置"""
    id: str
    name: str
    description: str
    player_count: int
    has_police: bool
    difficulty: list[str]  # ["novice"] | ["basic", "advanced"] | ["expert"]
    slots: list[BoardSlot]
    night_order: list[str]  # 夜晚行动顺序
    special_rules: dict[str, Any] = field(default_factory=dict)

    def get_roles(self) -> list[Role]:
        """获取本板子所有固定角色"""
        roles = []
        for slot in self.slots:
            if slot.candidates and len(slot.candidates) == 1:
                roles.append(Role(slot.candidates[0]))
        return roles

    def get_wolf_roles(self) -> list[Role]:
        """获取狼人角色"""
        return [Role(s.candidates[0]) for s in self.slots
                if s.pool == "wolf" and s.candidates]

    def get_god_roles(self) -> list[Role]:
        """获取神职角色"""
        return [Role(s.candidates[0]) for s in self.slots
                if s.pool == "good_god" and s.candidates]
