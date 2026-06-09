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
    # ================================================================
    # 京城大师赛经典板子
    # ================================================================
    BoardConfig(
        id="expert_pre_witch_hunter_idiot_half",
        name="预女猎白混",
        description="预言家、女巫、猎人、白痴、混血儿、3平民、4狼。JY最爱的纯粹竞技板。",
        player_count=12,
        has_police=True,
        difficulty=["advanced", "expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.HUNTER, Role.IDIOT,
            Role.HALFBLOOD,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
        ]),
        night_order=["halfblood", "werewolf", "witch", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "halfblood": True},
    ),
    BoardConfig(
        id="expert_white_wolf_knight",
        name="白狼王骑士",
        description="预言家、女巫、守卫、骑士、4平民、3狼、白狼王。白狼王自爆带人+骑士决斗双核压制。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.GUARD, Role.KNIGHT,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.WHITE_WOLF_KING,
        ]),
        night_order=["werewolf", "witch", "guard", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "white_wolf_explode": True, "knight_duel": True},
    ),
    BoardConfig(
        id="expert_nightmare_dream_weaver",
        name="梦魇摄梦人",
        description="预言家、女巫、猎人、摄梦人、4平民、3狼、梦魇。技能封锁+摄梦保护双体系对抗。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.HUNTER, Role.DREAM_WEAVER,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.NIGHTMARE,
        ]),
        night_order=["nightmare", "werewolf", "witch", "dream_weaver", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "nightmare_block": True, "dream_lock": True},
    ),
    BoardConfig(
        id="expert_gargoyle_undertaker",
        name="石像鬼守墓人",
        description="预言家、女巫、猎人、守墓人、4平民、3狼、石像鬼。石像鬼独立查验+守墓人验尸。",
        player_count=12,
        has_police=True,
        difficulty=["advanced", "expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.HUNTER, Role.UNDERTAKER,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.GARGOYLE,
        ]),
        night_order=["gargoyle", "werewolf", "witch", "undertaker", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "gargoyle_separate": True, "undertaker": True},
    ),
    BoardConfig(
        id="expert_blood_moon_hunter_demon",
        name="血月猎魔人",
        description="预言家、女巫、猎魔人、守卫、4平民、3狼、血月使徒。猎魔人主动猎杀+血月自爆锁技能。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.HUNTER_DEMON, Role.GUARD,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.BLOOD_MOON,
        ]),
        night_order=["werewolf", "witch", "guard", "hunter_demon", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "hunter_demon": True, "blood_moon_lock": True},
    ),
    BoardConfig(
        id="expert_dancer_fake_face",
        name="假面舞会",
        description="预言家、女巫、舞者、白痴、4平民、3狼、假面。京城大师赛原创板，舞池面具机制。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.DANCER, Role.IDIOT,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.FAKE_FACE,
        ]),
        night_order=["dancer", "fake_face", "werewolf", "witch", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "dancer": True, "fake_face": True},
    ),
    BoardConfig(
        id="expert_thief_cupid",
        name="盗贼丘比特",
        description="预言家、女巫、猎人、白痴、盗贼+丘比特、4平民、2狼、狼王。第三方情侣链。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.HUNTER, Role.IDIOT,
            Role.THIEF, Role.CUPID,
            Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF,
            Role.WOLF_KING,
        ]),
        night_order=["thief", "cupid", "lovers", "werewolf", "witch", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "thief_pool": 4, "lovers": True},
    ),
    BoardConfig(
        id="expert_bear_hidden_wolf",
        name="熊隐狼",
        description="熊、女巫、猎人、守卫、4平民、3狼、隐狼。熊咆哮提供额外信息，隐狼潜伏破坏。",
        player_count=12,
        has_police=True,
        difficulty=["advanced", "expert"],
        slots=_slots([
            Role.BEAR, Role.WITCH, Role.HUNTER, Role.GUARD,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.HIDDEN_WOLF,
        ]),
        night_order=["werewolf", "witch", "guard"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "bear_roar": True, "hidden_wolf": True},
    ),
    BoardConfig(
        id="expert_evil_knight",
        name="恶灵骑士",
        description="预言家、女巫、守卫、白痴、4平民、3狼、恶灵骑士。恶灵骑士夜间免疫+反伤神职。",
        player_count=12,
        has_police=True,
        difficulty=["expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.GUARD, Role.IDIOT,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
            Role.EVIL_KNIGHT,
        ]),
        night_order=["werewolf", "witch", "guard", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "evil_knight_reflect": True},
    ),
    BoardConfig(
        id="expert_mute_mix",
        name="预女猎禁混",
        description="预言家、女巫、猎人、禁言长老、混血儿、3平民、4狼。标准板变体，禁言机制增加变数。",
        player_count=12,
        has_police=True,
        difficulty=["advanced", "expert"],
        slots=_slots([
            Role.SEER, Role.WITCH, Role.HUNTER, Role.MUTE_ELDER,
            Role.HALFBLOOD,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
        ]),
        night_order=["halfblood", "werewolf", "witch", "seer"],
        special_rules={"speech_cap_seconds": 120, "sheriff": True, "mute_elder": True, "halfblood": True},
    ),
]

BOARDS_BY_ID = {board.id: board for board in BOARDS}


def get_board(board_id: str) -> BoardConfig:
    try:
        return BOARDS_BY_ID[board_id]
    except KeyError as exc:
        raise ValueError(f"未知板子: {board_id}") from exc
