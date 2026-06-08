"""游戏状态机 — 阶段转换控制"""

from __future__ import annotations

from ..models.game import GamePhase, GameState
from ..models.board import BoardConfig
from ..models.role import Role, ROLE_CONFIG


# 阶段转换顺序
NIGHT_PHASES_FULL = [
    GamePhase.NIGHT_START,
    GamePhase.NIGHT_MAGICIAN,
    GamePhase.NIGHT_THIEF,
    GamePhase.NIGHT_CUPID,
    GamePhase.NIGHT_LOVERS,
    GamePhase.NIGHT_WILD_CHILD,
    GamePhase.NIGHT_MECH_WOLF,
    GamePhase.NIGHT_NIGHTMARE,
    GamePhase.NIGHT_WOLF_KILL,
    GamePhase.NIGHT_WOLF_BEAUTY,
    GamePhase.NIGHT_GARGOYLE,
    GamePhase.NIGHT_WITCH,
    GamePhase.NIGHT_GUARD,
    GamePhase.NIGHT_SEER,
    GamePhase.NIGHT_CROW,
    GamePhase.NIGHT_END,
]


def get_night_phases_for_board(board: BoardConfig) -> list[GamePhase]:
    """根据板子配置获取需要执行的夜晚阶段"""
    roles_in_board = set()
    for slot in board.slots:
        if slot.candidates:
            for c in slot.candidates:
                try:
                    roles_in_board.add(Role(c))
                except ValueError:
                    pass

    # 基础夜晚流程
    phases = [GamePhase.NIGHT_START]

    # 根据角色动态添加夜晚阶段
    if Role.MAGICIAN in roles_in_board:
        phases.append(GamePhase.NIGHT_MAGICIAN)
    if Role.THIEF in roles_in_board:
        phases.append(GamePhase.NIGHT_THIEF)
    if Role.CUPID in roles_in_board:
        phases.append(GamePhase.NIGHT_CUPID)
        phases.append(GamePhase.NIGHT_LOVERS)
    if Role.WILD_CHILD in roles_in_board:
        phases.append(GamePhase.NIGHT_WILD_CHILD)
    if Role.MECHANICAL_WOLF in roles_in_board:
        phases.append(GamePhase.NIGHT_MECH_WOLF)
    if Role.NIGHTMARE in roles_in_board:
        phases.append(GamePhase.NIGHT_NIGHTMARE)

    phases.append(GamePhase.NIGHT_WOLF_KILL)

    if Role.WOLF_BEAUTY in roles_in_board:
        phases.append(GamePhase.NIGHT_WOLF_BEAUTY)
    if Role.GARGOYLE in roles_in_board:
        phases.append(GamePhase.NIGHT_GARGOYLE)

    if Role.WITCH in roles_in_board:
        phases.append(GamePhase.NIGHT_WITCH)
    if Role.GUARD in roles_in_board:
        phases.append(GamePhase.NIGHT_GUARD)

    # 预言家和通灵师
    if Role.SEER in roles_in_board or Role.PSYCHIC in roles_in_board:
        phases.append(GamePhase.NIGHT_SEER)
    if Role.CROW in roles_in_board:
        phases.append(GamePhase.NIGHT_CROW)

    phases.append(GamePhase.NIGHT_END)
    return phases


class PhaseMachine:
    """游戏阶段状态机"""

    def __init__(self, board: BoardConfig):
        self.board = board
        self._night_phases = get_night_phases_for_board(board)
        self._night_phase_index = 0

    def get_initial_phase(self) -> GamePhase:
        return GamePhase.LOBBY

    def get_next_night_phase(self, current: GamePhase) -> GamePhase | None:
        """获取下一个夜晚阶段"""
        try:
            idx = self._night_phases.index(current)
            if idx + 1 < len(self._night_phases):
                return self._night_phases[idx + 1]
        except ValueError:
            pass
        return None

    def get_night_phases(self) -> list[GamePhase]:
        return list(self._night_phases)

    def should_skip_phase(self, phase: GamePhase, state: GameState) -> bool:
        """判断是否应跳过某个阶段"""
        # 首夜相关的阶段
        if phase in (GamePhase.NIGHT_CUPID, GamePhase.NIGHT_LOVERS,
                     GamePhase.NIGHT_WILD_CHILD, GamePhase.NIGHT_THIEF):
            if not state.is_first_night:
                return True

        # 需要对应角色存活才执行
        phase_role_map = {
            GamePhase.NIGHT_MAGICIAN: Role.MAGICIAN,
            GamePhase.NIGHT_THIEF: Role.THIEF,
            GamePhase.NIGHT_CUPID: Role.CUPID,
            GamePhase.NIGHT_WILD_CHILD: Role.WILD_CHILD,
            GamePhase.NIGHT_MECH_WOLF: Role.MECHANICAL_WOLF,
            GamePhase.NIGHT_NIGHTMARE: Role.NIGHTMARE,
            GamePhase.NIGHT_WOLF_BEAUTY: Role.WOLF_BEAUTY,
            GamePhase.NIGHT_GARGOYLE: Role.GARGOYLE,
            GamePhase.NIGHT_WITCH: Role.WITCH,
            GamePhase.NIGHT_GUARD: Role.GUARD,
            GamePhase.NIGHT_SEER: Role.SEER,  # 也包含PSYCHIC
            GamePhase.NIGHT_CROW: Role.CROW,
        }

        role = phase_role_map.get(phase)
        if role:
            # 检查是否有该角色的存活玩家
            has_role_alive = any(
                p.is_alive and p.role == role
                for p in state.players
            )
            # 特殊：NIGHT_SEER 也检查通灵师
            if phase == GamePhase.NIGHT_SEER:
                has_role_alive = has_role_alive or any(
                    p.is_alive and p.role == Role.PSYCHIC
                    for p in state.players
                )
            if not has_role_alive:
                return True

        return False

    def get_day_phases(self, has_police: bool) -> list[GamePhase]:
        """获取白天阶段序列"""
        phases = [GamePhase.DAY_DEATH_ANNOUNCE]
        if has_police:
            phases.extend([
                GamePhase.POLICE_REGISTER,
                GamePhase.POLICE_SPEECH,
                GamePhase.POLICE_WITHDRAW,
                GamePhase.POLICE_VOTE,
            ])
        phases.extend([
            GamePhase.DAY_DISCUSS,
            GamePhase.DAY_VOTE,
        ])
        return phases
