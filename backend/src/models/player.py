"""玩家模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .role import Role, Faction, RoleCategory, ROLE_CONFIG


@dataclass
class Player:
    """游戏玩家"""
    id: str                    # 唯一ID (如 "player_0")
    seat_number: int           # 座位号 (1-12)
    name: str                  # 显示名称
    is_human: bool = False     # 是否为人类玩家
    is_alive: bool = True      # 是否存活
    is_sheriff: bool = False   # 是否为警长
    role: Role | None = None   # 角色
    faction: Faction | None = None  # 阵营

    # 状态标记
    has_voted: bool = False
    has_spoken: bool = False
    is_revealed_idiot: bool = False  # 白痴是否已翻牌

    # 特殊状态
    protected_by_guard: bool = False   # 被守卫守护
    protected_by_witch: bool = False   # 被女巫救
    poisoned_by_witch: bool = False    # 被女巫毒
    charmed_by_beauty: bool = False    # 被狼美人魅惑
    cursed_by_crow: bool = False       # 被乌鸦诅咒(+1票)
    dream_blocked: bool = False        # 被摄梦人封技能
    nightmare_blocked: bool = False    # 被梦魇封技能
    swapped_by_magician: bool = False  # 被魔术师交换号码
    swap_target: str | None = None     # 交换目标

    # 机械狼相关
    learned_role: Role | None = None   # 机械狼学习到的角色
    has_learned: bool = False          # 是否已学习

    # 野孩子相关
    role_model: str | None = None      # 榜样ID
    turned_wolf: bool = False          # 是否已转变为狼人

    # 情侣相关
    lover_id: str | None = None        # 情侣ID

    # 女巫药水
    has_antidote: bool = True          # 解药
    has_poison: bool = True            # 毒药

    # 守卫
    last_guarded: str | None = None    # 上一晚守护的目标

    # 猎人/狼王
    can_shoot: bool = True             # 是否可以开枪(被毒则不能)
    has_used_skill: bool = False       # 是否已使用一次性技能

    # 骑士
    has_dueled: bool = False           # 是否已决斗过

    @property
    def display_role(self) -> str:
        if self.role is None:
            return "未知"
        return ROLE_CONFIG[self.role]["display_name"]

    @property
    def role_category(self) -> RoleCategory | None:
        if self.role is None:
            return None
        return ROLE_CONFIG[self.role]["category"]

    def to_public_dict(self) -> dict[str, Any]:
        """公开信息(对所有人可见)"""
        return {
            "id": self.id,
            "seat_number": self.seat_number,
            "name": self.name,
            "is_human": self.is_human,
            "is_alive": self.is_alive,
            "is_sheriff": self.is_sheriff,
            "is_revealed_idiot": self.is_revealed_idiot,
        }

    def to_role_dict(self) -> dict[str, Any]:
        """角色信息(仅对自己和特殊情况下可见)"""
        return {
            **self.to_public_dict(),
            "role": self.role.value if self.role else None,
            "faction": self.faction.value if self.faction else None,
        }
