"""胜负判定"""

from __future__ import annotations

from ..models.game import GameState
from ..models.player import Player
from ..models.role import Faction, Role, is_god, is_civilian, ROLE_CONFIG


class WinChecker:
    """胜负判定器"""

    @staticmethod
    def check(state: GameState) -> str | None:
        """
        检查是否有阵营达成胜利条件
        返回: "good" | "wolf" | "third" | "cursed_fox" | None
        """
        alive = state.get_alive_players()
        if not alive:
            return None

        alive_wolves = [p for p in alive if p.faction == Faction.WOLF]
        alive_gods = [p for p in alive if p.role and is_god(p.role)]
        alive_civilians = [p for p in alive if p.role and is_civilian(p.role)]
        alive_third = [p for p in alive if p.faction in (Faction.THIRD_PARTY, Faction.INDEPENDENT)]

        # 检查咒狐独立胜利
        cursed_fox = state.get_player("cursed_fox")  # 特殊ID处理
        for p in alive:
            if p.role == Role.CURSED_FOX and p.is_alive:
                # 咒狐存活时，如果某方达成胜利条件，咒狐取代获胜
                good_wins = len(alive_wolves) == 0
                wolf_wins = len(alive_gods) == 0 or len(alive_civilians) == 0
                if good_wins or wolf_wins:
                    return "cursed_fox"

        # 好人胜利：所有狼人出局
        if len(alive_wolves) == 0:
            return "good"

        # 狼人胜利：屠神(所有神职出局) 或 屠民(所有平民出局)
        if len(alive_gods) == 0:
            return "wolf"
        if len(alive_civilians) == 0:
            return "wolf"

        # 第三方胜利(人狼恋丘比特)：所有非第三方出局
        if alive_third:
            non_third_alive = [p for p in alive if p.faction not in (Faction.THIRD_PARTY, Faction.INDEPENDENT)]
            if len(non_third_alive) == 0:
                return "third"

        return None

    @staticmethod
    def check_after_death(state: GameState, dead_player_id: str) -> str | None:
        """玩家死亡后的额外检查(殉情链式传播等)"""
        return WinChecker.check(state)
