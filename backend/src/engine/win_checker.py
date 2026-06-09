"""胜负判定 — 涵盖第三方/独立阵营"""

from __future__ import annotations

from ..models.game import GameState
from ..models.role import Faction, Role, is_god, is_civilian


class WinChecker:
    """胜负判定器"""

    @staticmethod
    def check(state: GameState) -> str | None:
        alive = state.get_alive_players()
        if not alive:
            return None

        alive_wolves = [p for p in alive if p.faction == Faction.WOLF]
        alive_gods = [p for p in alive if p.role and is_god(p.role)]
        alive_civilians = [p for p in alive if p.role and is_civilian(p.role)]
        alive_third = [p for p in alive if p.faction in (Faction.THIRD_PARTY, Faction.INDEPENDENT)]

        # ---- 咒狐独立胜利 ----
        for p in alive_third:
            if p.role == Role.CURSED_FOX:
                if WinChecker._cursed_fox_wins(state):
                    return "cursed_fox"

        # ---- 好人胜利：所有狼人出局 ----
        if len(alive_wolves) == 0:
            # 检查是否有第三方阻止好人胜利（人狼恋等）
            return "good"

        # ---- 狼人胜利：屠边（屠神 或 屠民） ----
        if len(alive_gods) == 0 or len(alive_civilians) == 0:
            return "wolf"

        # ---- 第三方胜利（人狼恋）：非第三方全灭 ----
        if alive_third:
            non_third = [p for p in alive if p.faction not in (Faction.THIRD_PARTY, Faction.INDEPENDENT)]
            if len(non_third) == 0:
                return "third"

        return None

    @staticmethod
    def _cursed_fox_wins(state: GameState) -> bool:
        """咒狐存活时，若任一阵营达成胜利条件，咒狐取代获胜"""
        alive = state.get_alive_players()
        alive_wolves = [p for p in alive if p.faction == Faction.WOLF]
        alive_gods = [p for p in alive if p.role and is_god(p.role)]
        alive_civilians = [p for p in alive if p.role and is_civilian(p.role)]
        if len(alive_wolves) == 0:
            return True
        if len(alive_gods) == 0 or len(alive_civilians) == 0:
            return True
        return False

    @staticmethod
    def get_death_chain(
        state: GameState, dead_player_ids: set[str], cause: str
    ) -> list[str]:
        """计算死亡链式传播

        Args:
            state: 游戏状态
            dead_player_ids: 已确定死亡的玩家集合
            cause: 死亡原因

        Returns:
            额外死亡的玩家ID列表（殉情、猎人带人等）
        """
        extra_deaths: list[str] = []
        processed = set(dead_player_ids)

        for pid in list(dead_player_ids):
            player = state.get_player(pid)
            if not player:
                continue

            # 情侣殉情
            if player.lover_id and player.lover_id not in processed:
                lover = state.get_player(player.lover_id)
                if lover and lover.is_alive:
                    extra_deaths.append(player.lover_id)
                    processed.add(player.lover_id)

            # 被狼美人魅惑者殉情
            for p in state.get_alive_players():
                if p.charmed_by_beauty and p.id not in processed:
                    extra_deaths.append(p.id)
                    processed.add(p.id)

            # 摄梦人夜晚死亡连带
            if player.role == Role.DREAM_WEAVER and cause == "wolf_kill":
                if state.dream_weaver_target and state.dream_weaver_target not in processed:
                    extra_deaths.append(state.dream_weaver_target)
                    processed.add(state.dream_weaver_target)

        return extra_deaths
