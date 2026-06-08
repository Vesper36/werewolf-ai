"""角色技能执行器 — 注册表模式"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type

from ..models.game import GameState, Action, ActionType, NightResult
from ..models.player import Player
from ..models.role import Role, Faction


class RoleExecutor(ABC):
    """角色技能执行器基类"""

    @abstractmethod
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        """执行夜晚技能"""
        pass

    def can_execute(self, state: GameState, player: Player) -> bool:
        """是否可以执行技能"""
        return player.is_alive


class RoleExecutorRegistry:
    """角色执行器注册表"""
    _executors: dict[Role, RoleExecutor] = {}

    @classmethod
    def register(cls, role: Role):
        def decorator(executor_cls):
            instance = executor_cls()
            cls._executors[role] = instance
            return executor_cls
        return decorator

    @classmethod
    def get(cls, role: Role) -> RoleExecutor | None:
        return cls._executors.get(role)

    @classmethod
    def execute(cls, role: Role, state: GameState, player: Player, action: Action) -> None:
        executor = cls._executors.get(role)
        if executor:
            return executor.execute_night(state, player, action)


# === 具体角色执行器 ===

@RoleExecutorRegistry.register(Role.SEER)
class SeerExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.SEER_CHECK or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        state.seer_check_target = action.target_id
        # 预言家查验阵营
        if target.role == Role.HIDDEN_WOLF:
            state.seer_check_result = True  # 隐狼查验为好人
        elif target.role == Role.SNOW_WOLF:
            state.seer_check_result = True  # 雪狼查验为好人
        elif target.role == Role.CURSED_FOX:
            # 咒狐被查验为好人但会出局(特殊处理在game_manager中)
            state.seer_check_result = True
        else:
            state.seer_check_result = target.faction != Faction.WOLF


@RoleExecutorRegistry.register(Role.PSYCHIC)
class PsychicExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.PSYCHIC_CHECK or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        # 通灵师查验具体身份(结果通过event传递给AI)
        state.seer_check_target = action.target_id
        state.seer_check_result = target.faction != Faction.WOLF


@RoleExecutorRegistry.register(Role.WITCH)
class WitchExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if not player.has_antidote and not player.has_poison:
            return

        if action.action_type == ActionType.WITCH_SAVE:
            if player.has_antidote and state.wolf_kill_target:
                state.witch_save_target = state.wolf_kill_target
                player.has_antidote = False
        elif action.action_type == ActionType.WITCH_POISON:
            if player.has_poison and action.target_id:
                state.witch_poison_target = action.target_id
                player.has_poison = False


@RoleExecutorRegistry.register(Role.GUARD)
class GuardExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.GUARD_PROTECT or not action.target_id:
            return
        # 不可连续两晚守同一人
        if action.target_id == player.last_guarded:
            return
        target = state.get_player(action.target_id)
        if target and target.is_alive:
            state.guard_target = action.target_id
            player.last_guarded = action.target_id


@RoleExecutorRegistry.register(Role.HUNTER)
class HunterExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 猎人技能在死亡时触发，不在夜晚执行


@RoleExecutorRegistry.register(Role.KNIGHT)
class KnightExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 骑士技能在白天决斗时触发


@RoleExecutorRegistry.register(Role.WEREWOLF)
class WerewolfExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.WOLF_KILL and action.target_id:
            state.wolf_kill_target = action.target_id


@RoleExecutorRegistry.register(Role.MECHANICAL_WOLF)
class MechanicalWolfExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.MECH_WOLF_LEARN and action.target_id:
            target = state.get_player(action.target_id)
            if target and target.role:
                player.learned_role = target.role
                player.has_learned = True


@RoleExecutorRegistry.register(Role.WOLF_BEAUTY)
class WolfBeautyExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.WOLF_BEAUTY_CHARM and action.target_id:
            target = state.get_player(action.target_id)
            if target:
                target.charmed_by_beauty = True


@RoleExecutorRegistry.register(Role.WOLF_KING)
class WolfKingExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 狼王技能在死亡时触发


@RoleExecutorRegistry.register(Role.WHITE_WOLF_KING)
class WhiteWolfKingExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 白狼王技能在白天自爆时触发


def get_executor(role: Role) -> RoleExecutor | None:
    return RoleExecutorRegistry.get(role)
