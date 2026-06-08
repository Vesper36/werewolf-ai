"""角色枚举与能力定义"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class Faction(str, Enum):
    """阵营"""
    GOOD = "good"           # 好人阵营
    WOLF = "wolf"           # 狼人阵营
    THIRD_PARTY = "third"   # 第三方阵营
    INDEPENDENT = "independent"  # 独立阵营(咒狐)


class RoleCategory(str, Enum):
    """角色大类"""
    GOD = "god"           # 神职
    CIVILIAN = "civilian"  # 平民
    WOLF = "wolf"         # 狼人
    SPECIAL = "special"   # 特殊(第三方/独立)


class Role(str, Enum):
    """所有角色"""
    # 好人神职
    SEER = "seer"                 # 预言家
    WITCH = "witch"               # 女巫
    HUNTER = "hunter"             # 猎人
    GUARD = "guard"               # 守卫
    IDIOT = "idiot"               # 白痴
    KNIGHT = "knight"             # 骑士
    PSYCHIC = "psychic"           # 通灵师
    MAGICIAN = "magician"         # 魔术师
    UNDERTAKER = "undertaker"     # 守墓人
    DREAM_WEAVER = "dream_weaver" # 摄梦人
    CROW = "crow"                 # 乌鸦
    PURE_WHITE = "pure_white"     # 纯白之女
    ALCHEMIST = "alchemist"       # 炼金魔女
    DAY_SCHOLAR = "day_scholar"   # 白昼学者
    FLOW_DUKE = "flow_duke"       # 流光伯爵
    HUNTER_DEMON = "hunter_demon" # 猎魔人/猎日

    # 好人平民
    VILLAGER = "villager"         # 村民
    OLD_ROGUE = "old_rogue"       # 老流氓

    # 狼人
    WEREWOLF = "werewolf"         # 普通狼人
    WOLF_KING = "wolf_king"       # 狼王
    WHITE_WOLF_KING = "white_wolf_king"  # 白狼王
    BLACK_WOLF_KING = "black_wolf_king"  # 黑狼王
    WOLF_BEAUTY = "wolf_beauty"   # 狼美人
    GARGOYLE = "gargoyle"         # 石像鬼
    SNOW_WOLF = "snow_wolf"       # 雪狼
    HIDDEN_WOLF = "hidden_wolf"   # 隐狼
    NIGHTMARE = "nightmare"       # 梦魇
    MECHANICAL_WOLF = "mechanical_wolf"  # 机械狼
    EVIL_KNIGHT = "evil_knight"   # 恶灵骑士
    BLOOD_MOON = "blood_moon"     # 血月使徒
    WOLF_WITCH = "wolf_witch"     # 狼巫
    WOLF_CLAW = "wolf_claw"       # 狼鸦之爪
    SILENT_TUTOR = "silent_tutor" # 寂夜导师
    ECLIPSE_MAID = "eclipse_maid" # 蚀日侍女
    NIGHT_NOBLE = "night_noble"   # 夜之贵族
    WOLF_BROTHER_ELDER = "wolf_brother_elder"  # 狼兄
    WOLF_BROTHER_YOUNGER = "wolf_brother_younger"  # 狼弟
    DREAM_DEVIL = "dream_devil"   # 梦魇(狼阵营版本)
    FAKE_FACE = "fake_face"       # 假面

    # 第三方/独立
    CUPID = "cupid"               # 丘比特
    CURSED_FOX = "cursed_fox"     # 咒狐
    HALFBLOOD = "halfblood"       # 混血儿
    THIEF = "thief"               # 盗贼
    WILD_CHILD = "wild_child"     # 野孩子
    TREASURE_THIEF = "treasure_thief"  # 盗宝大师


# 角色属性配置
ROLE_CONFIG: dict[Role, dict] = {
    # === 好人神职 ===
    Role.SEER: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "预言家",
        "description": "每晚查验一名玩家的阵营(好人/狼人)",
        "night_active": True,
        "can_self_check": False,
    },
    Role.WITCH: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "女巫",
        "description": "拥有解药和毒药各一瓶",
        "night_active": True,
        "has_antidote": True,
        "has_poison": True,
        "can_self_save": False,  # 全程不可自救
    },
    Role.HUNTER: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "猎人",
        "description": "出局时(殉情/被毒除外)可开枪带走一人",
        "night_active": False,
        "can_shoot_when_poisoned": False,
    },
    Role.GUARD: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "守卫",
        "description": "每晚守护一名玩家免受狼刀，不可连续两晚守同一人",
        "night_active": True,
        "cannot_guard_same_twice": True,
    },
    Role.IDIOT: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "白痴",
        "description": "被投票放逐时翻牌免疫，但失去投票权",
        "night_active": False,
    },
    Role.KNIGHT: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "骑士",
        "description": "白天可决斗一名玩家，对方是狼则出局，是好人则骑士死",
        "night_active": False,
        "once_per_game": True,
    },
    Role.PSYCHIC: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "通灵师",
        "description": "每晚查验一名玩家的具体身份(而非仅阵营)",
        "night_active": True,
    },
    Role.MAGICIAN: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "魔术师",
        "description": "每晚交换两名玩家的号码牌，当晚所有技能目标互换",
        "night_active": True,
        "each_player_once": True,
    },
    Role.UNDERTAKER: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "守墓人",
        "description": "每晚可查验前一天白天被放逐出局玩家的身份",
        "night_active": True,
    },
    Role.DREAM_WEAVER: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "摄梦人",
        "description": "每晚选择一名玩家摄梦，使其当晚所有技能失效",
        "night_active": True,
    },
    Role.CROW: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "乌鸦",
        "description": "每晚诅咒一名玩家，第二天该玩家投票自动多1票",
        "night_active": True,
    },
    Role.PURE_WHITE: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "纯白之女",
        "description": "每晚查验一名玩家的具体身份",
        "night_active": True,
    },
    Role.ALCHEMIST: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "炼金魔女",
        "description": "拥有特殊炼金能力",
        "night_active": True,
    },
    Role.DAY_SCHOLAR: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "白昼学者",
        "description": "白天阶段拥有特殊能力",
        "night_active": False,
    },
    Role.FLOW_DUKE: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "流光伯爵",
        "description": "拥有守护相关能力",
        "night_active": True,
    },
    Role.HUNTER_DEMON: {
        "faction": Faction.GOOD,
        "category": RoleCategory.GOD,
        "display_name": "猎魔人",
        "description": "可猎杀狼人",
        "night_active": True,
    },

    # === 好人平民 ===
    Role.VILLAGER: {
        "faction": Faction.GOOD,
        "category": RoleCategory.CIVILIAN,
        "display_name": "村民",
        "description": "无特殊技能，通过发言和投票贡献",
        "night_active": False,
    },
    Role.OLD_ROGUE: {
        "faction": Faction.GOOD,
        "category": RoleCategory.CIVILIAN,
        "display_name": "老流氓",
        "description": "特殊平民",
        "night_active": False,
    },

    # === 狼人阵营 ===
    Role.WEREWOLF: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼人",
        "description": "夜间与队友讨论并选择击杀目标",
        "night_active": True,
    },
    Role.WOLF_KING: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼王",
        "description": "出局时(被毒除外)可带走一人",
        "night_active": True,
        "can_kill_on_death": True,
        "poison_disables": True,
    },
    Role.WHITE_WOLF_KING: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "白狼王",
        "description": "白天自爆可带走一名玩家",
        "night_active": True,
        "can_self_explode_kill": True,
    },
    Role.BLACK_WOLF_KING: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "黑狼王",
        "description": "出局时可带人，但自爆不能发动技能",
        "night_active": True,
        "can_kill_on_death": True,
        "self_explode_no_skill": True,
    },
    Role.WOLF_BEAUTY: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼美人",
        "description": "每夜魅惑一人，出局时被魅惑者殉情",
        "night_active": True,
        "has_charm": True,
    },
    Role.GARGOYLE: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "石像鬼",
        "description": "与狼人互不相认，每晚查验一人身份，狼全死后继承刀权",
        "night_active": True,
        "separate_from_wolves": True,
    },
    Role.SNOW_WOLF: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "雪狼",
        "description": "预言家/守墓人不能认定其为狼人",
        "night_active": True,
        "immune_to_seer": True,
    },
    Role.HIDDEN_WOLF: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "隐狼",
        "description": "不与狼人一起睁眼，预言家查验为好人",
        "night_active": False,
        "invisible_to_seer": True,
    },
    Role.NIGHTMARE: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "梦魇",
        "description": "每晚在狼人行动前可选择一名玩家使其当晚不能使用技能",
        "night_active": True,
    },
    Role.MECHANICAL_WOLF: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "机械狼",
        "description": "与狼人互不相认，可学习一名玩家获得其技能",
        "night_active": True,
        "separate_from_wolves": True,
        "can_learn": True,
    },
    Role.EVIL_KNIGHT: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "恶灵骑士",
        "description": "不能在晚上死亡，被神职指定时反伤",
        "night_active": True,
        "night_immortal": True,
        "one_time_reflect": True,
    },
    Role.BLOOD_MOON: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "血月使徒",
        "description": "出局时触发特殊效果",
        "night_active": True,
    },
    Role.WOLF_WITCH: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼巫",
        "description": "狼阵营特殊角色",
        "night_active": True,
    },
    Role.WOLF_CLAW: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼鸦之爪",
        "description": "狼阵营特殊角色",
        "night_active": True,
    },
    Role.SILENT_TUTOR: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "寂夜导师",
        "description": "狼阵营特殊角色",
        "night_active": True,
    },
    Role.ECLIPSE_MAID: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "蚀日侍女",
        "description": "狼阵营特殊角色",
        "night_active": True,
    },
    Role.NIGHT_NOBLE: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "夜之贵族",
        "description": "狼阵营特殊角色",
        "night_active": True,
    },
    Role.WOLF_BROTHER_ELDER: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼兄",
        "description": "与狼弟互认",
        "night_active": True,
    },
    Role.WOLF_BROTHER_YOUNGER: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "狼弟",
        "description": "与狼兄互认",
        "night_active": True,
    },
    Role.DREAM_DEVIL: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "梦魇(狼)",
        "description": "狼阵营梦魇",
        "night_active": True,
    },
    Role.FAKE_FACE: {
        "faction": Faction.WOLF,
        "category": RoleCategory.WOLF,
        "display_name": "假面",
        "description": "特殊狼人变体",
        "night_active": True,
    },

    # === 第三方/独立 ===
    Role.CUPID: {
        "faction": Faction.THIRD_PARTY,
        "category": RoleCategory.SPECIAL,
        "display_name": "丘比特",
        "description": "第一晚选择两名玩家成为情侣",
        "night_active": True,
        "first_night_only": True,
    },
    Role.CURSED_FOX: {
        "faction": Faction.INDEPENDENT,
        "category": RoleCategory.SPECIAL,
        "display_name": "咒狐",
        "description": "被狼刀不死，被预言家查验则出局，存活到最后即获胜",
        "night_active": False,
    },
    Role.HALFBLOOD: {
        "faction": Faction.THIRD_PARTY,
        "category": RoleCategory.SPECIAL,
        "display_name": "混血儿",
        "description": "第一晚选择一名玩家作为血亲，阵营与血亲绑定",
        "night_active": True,
        "first_night_only": True,
    },
    Role.THIEF: {
        "faction": Faction.THIRD_PARTY,
        "category": RoleCategory.SPECIAL,
        "display_name": "盗贼",
        "description": "第一晚从剩余两张牌中选择一张作为身份",
        "night_active": True,
        "first_night_only": True,
    },
    Role.WILD_CHILD: {
        "faction": Faction.GOOD,
        "category": RoleCategory.SPECIAL,
        "display_name": "野孩子",
        "description": "第一晚选榜样，榜样出局则转变为狼人",
        "night_active": True,
        "first_night_only": True,
    },
    Role.TREASURE_THIEF: {
        "faction": Faction.THIRD_PARTY,
        "category": RoleCategory.SPECIAL,
        "display_name": "盗宝大师",
        "description": "持有三张身份牌的能力",
        "night_active": True,
    },
}


def get_role_faction(role: Role) -> Faction:
    return ROLE_CONFIG[role]["faction"]


def get_role_category(role: Role) -> RoleCategory:
    return ROLE_CONFIG[role]["category"]


def get_role_display_name(role: Role) -> str:
    return ROLE_CONFIG[role]["display_name"]


def get_role_description(role: Role) -> str:
    return ROLE_CONFIG[role]["description"]


def is_night_active(role: Role) -> bool:
    return ROLE_CONFIG[role].get("night_active", False)


def is_wolf_team(role: Role) -> bool:
    return ROLE_CONFIG[role]["faction"] == Faction.WOLF


def is_good_team(role: Role) -> bool:
    return ROLE_CONFIG[role]["faction"] == Faction.GOOD


def is_god(role: Role) -> bool:
    return ROLE_CONFIG[role]["category"] == RoleCategory.GOD


def is_civilian(role: Role) -> bool:
    return ROLE_CONFIG[role]["category"] == RoleCategory.CIVILIAN
