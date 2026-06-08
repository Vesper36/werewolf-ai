"""狼人杀板子预设。

板子保持纯配置，复杂角色的裁判细节在 engine 层逐步补齐。
"""

from __future__ import annotations

from ..models.board import BoardConfig, BoardSlot
from ..models.role import Faction, ROLE_CONFIG, Role, RoleCategory


def _pool_for(role: Role) -> str:
    config = ROLE_CONFIG[role]
    if config["faction"] == Faction.WOLF:
        return "wolf"
    if config["category"] == RoleCategory.GOD:
        return "good_god"
    if config["category"] == RoleCategory.CIVILIAN:
        return "good_civilian"
    return "special"


def _slot(role: Role) -> BoardSlot:
    return BoardSlot(pool=_pool_for(role), candidates=[role.value])


def _slots(roles: list[Role]) -> list[BoardSlot]:
    return [_slot(role) for role in roles]


BOARDS: list[BoardConfig] = [
    BoardConfig(
        id="novice_9_no_police",
        name="入门九人局",
        description="预女猎、三民、三狼。无上警，适合熟悉发言、投票和基础夜晚技能。",
        player_count=9,
        has_police=False,
        difficulty=["novice"],
        slots=_slots(
            [
                Role.SEER,
                Role.WITCH,
                Role.HUNTER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
            ]
        ),
        night_order=["werewolf", "witch", "seer"],
        special_rules={"speech_cap_seconds": 90, "sheriff": False},
    ),
    BoardConfig(
        id="basic_12_standard",
        name="基础十二人标准局",
        description="预女猎守、四民、四狼。默认带上警，练习警徽流和标准站边。",
        player_count=12,
        has_police=True,
        difficulty=["basic", "advanced"],
        slots=_slots(
            [
                Role.SEER,
                Role.WITCH,
                Role.HUNTER,
                Role.GUARD,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WOLF_KING,
            ]
        ),
        night_order=["werewolf", "witch", "guard", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True},
    ),
    BoardConfig(
        id="advanced_knight",
        name="狼王骑士",
        description="预女猎骑、四民、三狼一狼王。白天骑士决斗会强行改变站边节奏。",
        player_count=12,
        has_police=True,
        difficulty=["advanced", "expert"],
        slots=_slots(
            [
                Role.SEER,
                Role.WITCH,
                Role.HUNTER,
                Role.KNIGHT,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WOLF_KING,
            ]
        ),
        night_order=["werewolf", "witch", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "knight_duel": True},
    ),
    BoardConfig(
        id="expert_mech_psychic",
        name="机械狼通灵师",
        description="通灵师、女巫、猎人、守卫、四民、三狼、机械狼。机械狼与狼队隔离，大神模式默认推荐。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots(
            [
                Role.PSYCHIC,
                Role.WITCH,
                Role.HUNTER,
                Role.GUARD,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.MECHANICAL_WOLF,
            ]
        ),
        night_order=["mechanical_wolf", "werewolf", "witch", "guard", "psychic"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "separate_mechanical_wolf": True},
    ),
    BoardConfig(
        id="expert_wolf_beauty_knight",
        name="狼美人骑士",
        description="预女猎骑、四民、三狼、狼美人。强调魅惑链、骑士压迫和警上对跳。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots(
            [
                Role.SEER,
                Role.WITCH,
                Role.HUNTER,
                Role.KNIGHT,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WOLF_BEAUTY,
            ]
        ),
        night_order=["werewolf", "wolf_beauty", "witch", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "charm_death_chain": True},
    ),
    BoardConfig(
        id="expert_cupid_lovers",
        name="情侣丘比特",
        description="丘比特加入十二人局，支持人狼恋、第三方恋人胜利路线。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots(
            [
                Role.SEER,
                Role.WITCH,
                Role.HUNTER,
                Role.GUARD,
                Role.CUPID,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WOLF_KING,
            ]
        ),
        night_order=["cupid", "lovers", "werewolf", "witch", "guard", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "lovers": True},
    ),
    BoardConfig(
        id="expert_treasure_thief",
        name="盗宝大师",
        description="盗宝大师、通灵师、摄梦人、女巫、猎人、三民、三狼一狼王。用于复刻高复杂度花板子推理。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots(
            [
                Role.TREASURE_THIEF,
                Role.PSYCHIC,
                Role.DREAM_WEAVER,
                Role.WITCH,
                Role.HUNTER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WOLF_KING,
            ]
        ),
        night_order=["treasure_thief", "dream_weaver", "werewolf", "witch", "psychic"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "treasure_masks": 3},
    ),
    BoardConfig(
        id="expert_cursed_fox",
        name="咒狐争胜",
        description="咒狐加入十二人局，要求 AI 同时处理独立阵营、验狐出局和第三方胜利窗口。",
        player_count=12,
        has_police=True,
        difficulty=["advanced", "expert"],
        slots=_slots(
            [
                Role.CURSED_FOX,
                Role.SEER,
                Role.WITCH,
                Role.HUNTER,
                Role.GUARD,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.VILLAGER,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WEREWOLF,
                Role.WOLF_KING,
            ]
        ),
        night_order=["werewolf", "witch", "guard", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "cursed_fox": True},
    ),
]

BOARDS_BY_ID = {board.id: board for board in BOARDS}


def get_board(board_id: str) -> BoardConfig:
    try:
        return BOARDS_BY_ID[board_id]
    except KeyError as exc:
        raise ValueError(f"未知板子: {board_id}") from exc
