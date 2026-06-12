"""游戏状态模型"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Any
import time

from .player import Player
from .role import Faction, Role


class GamePhase(str, Enum):
    """游戏阶段"""
    LOBBY = "lobby"
    ROLE_DEALT = "role_dealt"

    # 夜晚阶段
    NIGHT_START = "night_start"
    NIGHT_MAGICIAN = "night_magician"
    NIGHT_THIEF = "night_thief"
    NIGHT_CUPID = "night_cupid"
    NIGHT_LOVERS = "night_lovers"
    NIGHT_WILD_CHILD = "night_wild_child"
    NIGHT_MECH_WOLF = "night_mech_wolf"
    NIGHT_NIGHTMARE = "night_nightmare"
    NIGHT_WOLF_KILL = "night_wolf_kill"
    NIGHT_WOLF_BEAUTY = "night_wolf_beauty"
    NIGHT_GARGOYLE = "night_gargoyle"
    NIGHT_WITCH = "night_witch"
    NIGHT_GUARD = "night_guard"
    NIGHT_SEER = "night_seer"
    NIGHT_CROW = "night_crow"
    NIGHT_END = "night_end"

    # 白天阶段
    DAY_DEATH_ANNOUNCE = "day_death_announce"
    POLICE_REGISTER = "police_register"
    POLICE_SPEECH = "police_speech"
    POLICE_WITHDRAW = "police_withdraw"
    POLICE_VOTE = "police_vote"
    POLICE_PK = "police_pk"
    POLICE_RESULT = "police_result"
    DAY_DISCUSS = "day_discuss"
    DAY_VOTE = "day_vote"
    DAY_PK = "day_pk"
    DAY_VOTE_RESULT = "day_vote_result"

    GAME_OVER = "game_over"


class ActionType(str, Enum):
    """行动类型"""
    # 夜晚行动
    WOLF_KILL = "wolf_kill"
    WITCH_SAVE = "witch_save"
    WITCH_POISON = "witch_poison"
    GUARD_PROTECT = "guard_protect"
    SEER_CHECK = "seer_check"
    PSYCHIC_CHECK = "psychic_check"
    MAGICIAN_SWAP = "magician_swap"
    CUPID_LINK = "cupid_link"
    THIEF_CHOOSE = "thief_choose"
    WILD_CHILD_CHOOSE = "wild_child_choose"
    MECH_WOLF_LEARN = "mech_wolf_learn"
    NIGHTMARE_BLOCK = "nightmare_block"
    WOLF_BEAUTY_CHARM = "wolf_beauty_charm"
    GARGOYLE_CHECK = "gargoyle_check"
    DREAM_WEAVER_TARGET = "dream_weaver_target"
    CROW_CURSE = "crow_curse"
    HUNTER_DEMON_HUNT = "hunter_demon_hunt"
    UNDERTAKER_CHECK = "undertaker_check"
    TREASURE_THIEF_SWITCH = "treasure_thief_switch"
    HALFBLOOD_CHOOSE = "halfblood_choose"
    PURE_WHITE_CHECK = "pure_white_check"
    ALCHEMIST_ACTION = "alchemist_action"
    WOLF_WITCH_CHECK = "wolf_witch_check"
    SILENT_TUTOR_BLOCK = "silent_tutor_block"
    DANCER_INVITE = "dancer_invite"
    FAKE_FACE_SWAP = "fake_face_swap"

    # 白天行动
    SPEECH = "speech"
    VOTE = "vote"
    POLICE_REGISTER = "police_register"
    POLICE_VOTE = "police_vote"
    POLICE_WITHDRAW = "police_withdraw"
    KNIGHT_DUEL = "knight_duel"
    HUNTER_SHOOT = "hunter_shoot"
    WOLF_SELF_EXPLODE = "wolf_self_explode"
    IDIOT_REVEAL = "idiot_reveal"

    # 系统
    SKIP = "skip"
    PASS = "pass"


@dataclass
class Action:
    """玩家行动"""
    player_id: str
    action_type: ActionType
    target_id: str | None = None
    second_target_id: str | None = None  # 魔术师交换需要两个目标
    payload: dict[str, Any] | None = None  # 额外数据(如发言内容)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "action_type": self.action_type.value,
            "target_id": self.target_id,
            "second_target_id": self.second_target_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class VoteRecord:
    """投票记录"""
    voter_id: str
    target_id: str
    is_sheriff_vote: bool = False  # 是否为警长投票(1.5票)
    is_cursed_vote: bool = False   # 是否被乌鸦诅咒(+1票)


@dataclass
class SpeechRecord:
    """发言记录"""
    player_id: str
    text: str
    phase: GamePhase
    day_number: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class NightResult:
    """夜晚结算结果"""
    deaths: list[dict[str, Any]] = field(default_factory=list)
    # {"player_id": "player_3", "cause": "wolf_kill"|"witch_poison"|"..."}


@dataclass
class GameState:
    """完整游戏状态"""
    game_id: str
    board_id: str
    difficulty: str
    players: list[Player] = field(default_factory=list)
    phase: GamePhase = GamePhase.LOBBY
    day_number: int = 0
    is_first_night: bool = True

    # 警长
    sheriff_id: str | None = None
    police_candidates: list[str] = field(default_factory=list)
    police_vote_records: list[VoteRecord] = field(default_factory=list)

    # 夜晚行动记录
    wolf_kill_target: str | None = None
    witch_save_target: str | None = None
    witch_poison_target: str | None = None
    guard_target: str | None = None
    seer_check_target: str | None = None
    seer_check_result: bool | None = None  # True=好人, False=狼人
    nightmare_block_target: str | None = None
    crow_curse_target: str | None = None
    dream_weaver_target: str | None = None
    magician_swap_a: str | None = None
    magician_swap_b: str | None = None
    dancer_guests: list[str] = field(default_factory=list)  # 舞者邀请的玩家

    # 情侣
    lover_pairs: list[tuple[str, str]] = field(default_factory=list)  # [(a_id, b_id), ...]

    # 预言家/通灵师查验结果（持久保留到下一次夜晚才清除）
    last_check_result: dict | None = None  # {"target_seat": int, "result": "good"|"wolf", "role": str|None}

    # 投票
    vote_records: list[VoteRecord] = field(default_factory=list)

    # 历史
    speech_history: list[SpeechRecord] = field(default_factory=list)
    night_results: list[NightResult] = field(default_factory=list)
    day_deaths: list[dict[str, Any]] = field(default_factory=list)

    # 警徽流
    sheriff_badge_flow: list[str] = field(default_factory=list)

    # 自爆
    self_explode_count: int = 0

    # 遗言池（本局还能使用的遗言次数）
    remaining_last_words: int = 0

    # 胜利方
    winner: str | None = None  # "good" | "wolf" | "third" | "cursed_fox"

    def get_player(self, player_id: str) -> Player | None:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def get_player_by_seat(self, seat: int) -> Player | None:
        for p in self.players:
            if p.seat_number == seat:
                return p
        return None

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.is_alive]

    def get_alive_wolves(self) -> list[Player]:
        return [p for p in self.players if p.is_alive and p.faction == Faction.WOLF]

    def get_alive_gods(self) -> list[Player]:
        from .role import is_god
        return [p for p in self.players if p.is_alive and p.role and is_god(p.role)]

    def get_alive_civilians(self) -> list[Player]:
        from .role import is_civilian
        return [p for p in self.players if p.is_alive and p.role and is_civilian(p.role)]

    def get_human_player(self) -> Player | None:
        for p in self.players:
            if p.is_human:
                return p
        return None

    def get_alive_non_wolves(self) -> list[Player]:
        return [p for p in self.players if p.is_alive and p.faction != Faction.WOLF]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "board_id": self.board_id,
            "difficulty": self.difficulty,
            "phase": self.phase.value,
            "day_number": self.day_number,
            "is_first_night": self.is_first_night,
            "sheriff_id": self.sheriff_id,
            "winner": self.winner,
            "players": [p.to_public_dict() for p in self.players],
        }
