"""角色技能执行器 — 注册表模式，覆盖全角色"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.game import GameState, Action, ActionType
from ..models.player import Player
from ..models.role import Role, Faction, ROLE_CONFIG


class RoleExecutor(ABC):
    """角色技能执行器基类"""

    @abstractmethod
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        """执行夜晚技能"""
        pass

    def can_execute(self, state: GameState, player: Player) -> bool:
        return player.is_alive


class RoleExecutorRegistry:
    _executors: dict[Role, RoleExecutor] = {}

    @classmethod
    def register(cls, role: Role):
        def decorator(executor_cls):
            cls._executors[role] = executor_cls()
            return executor_cls
        return decorator

    @classmethod
    def get(cls, role: Role) -> RoleExecutor | None:
        return cls._executors.get(role)

    @classmethod
    async def execute(cls, role: Role, state: GameState, player: Player, action: Action) -> None:
        executor = cls._executors.get(role)
        if executor:
            await executor.execute_night(state, player, action)


# ============================================================
# 好人神职
# ============================================================

@RoleExecutorRegistry.register(Role.SEER)
class SeerExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.SEER_CHECK or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        state.seer_check_target = action.target_id
        if target.role in {Role.HIDDEN_WOLF, Role.SNOW_WOLF, Role.CURSED_FOX}:
            state.seer_check_result = True
        else:
            state.seer_check_result = target.faction != Faction.WOLF


@RoleExecutorRegistry.register(Role.PSYCHIC)
class PsychicExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type not in {ActionType.PSYCHIC_CHECK, ActionType.SEER_CHECK}:
            return
        if not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
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
        if action.target_id == player.last_guarded:
            return
        target = state.get_player(action.target_id)
        if target and target.is_alive:
            state.guard_target = action.target_id
            player.last_guarded = action.target_id


@RoleExecutorRegistry.register(Role.HUNTER)
class HunterExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 猎人技能在死亡时触发


@RoleExecutorRegistry.register(Role.KNIGHT)
class KnightExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 骑士在白天决斗


@RoleExecutorRegistry.register(Role.IDIOT)
class IdiotExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 白痴被投票出局时翻牌


@RoleExecutorRegistry.register(Role.MAGICIAN)
class MagicianExecutor(RoleExecutor):
    """魔术师：每晚交换两名玩家的号码牌"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.MAGICIAN_SWAP:
            return
        if not action.target_id or not action.second_target_id:
            return
        a = state.get_player(action.target_id)
        b = state.get_player(action.second_target_id)
        if not a or not b or not a.is_alive or not b.is_alive:
            return
        if action.target_id == action.second_target_id:
            return
        # 记录交换（延迟解析：在夜晚结算时统一应用）
        state.magician_swap_a = action.target_id
        state.magician_swap_b = action.second_target_id
        a.swapped_by_magician = True
        b.swapped_by_magician = True


@RoleExecutorRegistry.register(Role.UNDERTAKER)
class UndertakerExecutor(RoleExecutor):
    """守墓人：每晚查验前一天被放逐者的身份"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.UNDERTAKER_CHECK:
            return
        # 目标由 GameService 自动设置（前一天被放逐者）


@RoleExecutorRegistry.register(Role.DREAM_WEAVER)
class DreamWeaverExecutor(RoleExecutor):
    """摄梦人：每晚摄梦一名玩家，该玩家当晚技能失效且免死"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.DREAM_WEAVER_TARGET or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        state.dream_weaver_target = action.target_id
        target.dream_blocked = True


@RoleExecutorRegistry.register(Role.CROW)
class CrowExecutor(RoleExecutor):
    """乌鸦：每晚诅咒一名玩家，第二天该玩家投票自动多1票"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.CROW_CURSE or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        state.crow_curse_target = action.target_id
        target.cursed_by_crow = True


@RoleExecutorRegistry.register(Role.PURE_WHITE)
class PureWhiteExecutor(RoleExecutor):
    """纯白之女：每晚查验一名玩家的具体身份"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type not in {ActionType.PURE_WHITE_CHECK, ActionType.SEER_CHECK}:
            return
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        state.seer_check_target = action.target_id
        state.seer_check_result = target.faction != Faction.WOLF


@RoleExecutorRegistry.register(Role.ALCHEMIST)
class AlchemistExecutor(RoleExecutor):
    """炼金魔女：拥有特殊炼金能力"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 具体能力待补充


@RoleExecutorRegistry.register(Role.DAY_SCHOLAR)
class DayScholarExecutor(RoleExecutor):
    """白昼学者：白天阶段特殊能力"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.FLOW_DUKE)
class FlowDukeExecutor(RoleExecutor):
    """流光伯爵：守护相关能力"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.GUARD_PROTECT or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if target and target.is_alive:
            state.guard_target = action.target_id


@RoleExecutorRegistry.register(Role.HUNTER_DEMON)
class HunterDemonExecutor(RoleExecutor):
    """猎魔人：可猎杀狼人"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.HUNTER_DEMON_HUNT or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.is_alive:
            return
        if target.faction == Faction.WOLF:
            target.is_alive = False
        else:
            # 猎错好人，猎魔人自己出局
            player.is_alive = False


# ============================================================
# 好人平民
# ============================================================

@RoleExecutorRegistry.register(Role.VILLAGER)
class VillagerExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.OLD_ROGUE)
class OldRogueExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


# ============================================================
# 狼人阵营
# ============================================================

@RoleExecutorRegistry.register(Role.WEREWOLF)
class WerewolfExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.WOLF_KILL and action.target_id:
            state.wolf_kill_target = action.target_id


@RoleExecutorRegistry.register(Role.WOLF_KING)
class WolfKingExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 死亡时触发带人


@RoleExecutorRegistry.register(Role.WHITE_WOLF_KING)
class WhiteWolfKingExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 白天自爆触发带人


@RoleExecutorRegistry.register(Role.BLACK_WOLF_KING)
class BlackWolfKingExecutor(RoleExecutor):
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 死亡时触发带人（自爆不能发动）


@RoleExecutorRegistry.register(Role.WOLF_BEAUTY)
class WolfBeautyExecutor(RoleExecutor):
    """狼美人：每夜魅惑一人，出局时被魅惑者殉情"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.WOLF_BEAUTY_CHARM and action.target_id:
            target = state.get_player(action.target_id)
            if target:
                target.charmed_by_beauty = True


@RoleExecutorRegistry.register(Role.GARGOYLE)
class GargoyleExecutor(RoleExecutor):
    """石像鬼：与狼队互不相认，每晚查验一人具体身份，狼全死后继承刀权"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.GARGOYLE_CHECK and action.target_id:
            target = state.get_player(action.target_id)
            if target and target.is_alive:
                pass  # 查验结果通过 visible_state 传递


@RoleExecutorRegistry.register(Role.SNOW_WOLF)
class SnowWolfExecutor(RoleExecutor):
    """雪狼：预言家/守墓人查验为好人"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 被动能力，已由 SeerExecutor 处理


@RoleExecutorRegistry.register(Role.HIDDEN_WOLF)
class HiddenWolfExecutor(RoleExecutor):
    """隐狼：不与狼队一起睁眼，预言家查验为好人"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 被动能力


@RoleExecutorRegistry.register(Role.NIGHTMARE)
class NightmareExecutor(RoleExecutor):
    """梦魇：每晚在狼人行动前可选择一名玩家使其当晚技能失效"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.NIGHTMARE_BLOCK and action.target_id:
            target = state.get_player(action.target_id)
            if target:
                target.nightmare_blocked = True
                state.nightmare_block_target = action.target_id


@RoleExecutorRegistry.register(Role.MECHANICAL_WOLF)
class MechanicalWolfExecutor(RoleExecutor):
    """机械狼：与狼队互不相认，可学习一名玩家获得其技能"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.MECH_WOLF_LEARN and action.target_id:
            target = state.get_player(action.target_id)
            if target and target.role:
                player.learned_role = target.role
                player.has_learned = True


@RoleExecutorRegistry.register(Role.EVIL_KNIGHT)
class EvilKnightExecutor(RoleExecutor):
    """恶灵骑士：夜晚不死，被神职指定时反伤"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 被动能力，在死亡结算时处理


@RoleExecutorRegistry.register(Role.BLOOD_MOON)
class BloodMoonExecutor(RoleExecutor):
    """血月使徒：自爆后下个夜晚所有神职技能失效"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 自爆效果由 GameService 处理


@RoleExecutorRegistry.register(Role.WOLF_WITCH)
class WolfWitchExecutor(RoleExecutor):
    """狼巫：狼阵营特殊角色，可查验具体身份"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.WOLF_WITCH_CHECK and action.target_id:
            pass  # 查验通过 visible_state 传递


@RoleExecutorRegistry.register(Role.WOLF_CLAW)
class WolfClawExecutor(RoleExecutor):
    """狼鸦之爪：特殊狼人"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.SILENT_TUTOR)
class SilentTutorExecutor(RoleExecutor):
    """寂夜导师：封锁技能"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.SILENT_TUTOR_BLOCK and action.target_id:
            target = state.get_player(action.target_id)
            if target:
                target.nightmare_blocked = True


@RoleExecutorRegistry.register(Role.ECLIPSE_MAID)
class EclipseMaidExecutor(RoleExecutor):
    """蚀日侍女：狼阵营特殊角色"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.NIGHT_NOBLE)
class NightNobleExecutor(RoleExecutor):
    """夜之贵族：狼阵营特殊角色"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.WOLF_BROTHER_ELDER)
class WolfBrotherElderExecutor(RoleExecutor):
    """狼兄：与狼弟互认"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.WOLF_BROTHER_YOUNGER)
class WolfBrotherYoungerExecutor(RoleExecutor):
    """狼弟：与狼兄互认"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.DREAM_DEVIL)
class DreamDevilExecutor(RoleExecutor):
    """梦魇(狼阵营版本)"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.NIGHTMARE_BLOCK and action.target_id:
            target = state.get_player(action.target_id)
            if target:
                target.nightmare_blocked = True


@RoleExecutorRegistry.register(Role.FAKE_FACE)
class FakeFaceExecutor(RoleExecutor):
    """假面：查验或更换面具"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 具体逻辑待板子规则完善


# ============================================================
# 第三方 / 独立阵营
# ============================================================

@RoleExecutorRegistry.register(Role.CUPID)
class CupidExecutor(RoleExecutor):
    """丘比特：第一晚选择两名玩家成为情侣"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.CUPID_LINK:
            return
        if not action.target_id or not action.second_target_id:
            return
        if action.target_id == action.second_target_id:
            return  # 不能连自己
        a = state.get_player(action.target_id)
        b = state.get_player(action.second_target_id)
        if not a or not b:
            return
        a.lover_id = action.second_target_id
        b.lover_id = action.target_id
        state.lover_pairs.append((action.target_id, action.second_target_id))
        # 丘比特本身是好人阵营，但情侣可能是第三方


@RoleExecutorRegistry.register(Role.CURSED_FOX)
class CursedFoxExecutor(RoleExecutor):
    """咒狐：被狼刀不死，被预言家查验则出局，存活到最后即获胜"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass  # 被动能力，在死亡结算时处理


@RoleExecutorRegistry.register(Role.HALFBLOOD)
class HalfbloodExecutor(RoleExecutor):
    """混血儿：第一晚选择一名血亲，阵营与血亲绑定"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.HALFBLOOD_CHOOSE or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target or not target.faction:
            return
        player.role_model = action.target_id
        # 混血儿阵营与血亲一致
        if target.faction == Faction.WOLF:
            player.faction = Faction.WOLF
        else:
            player.faction = Faction.GOOD


@RoleExecutorRegistry.register(Role.THIEF)
class ThiefExecutor(RoleExecutor):
    """盗贼：第一晚从剩余两张牌中选择一张作为身份"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.THIEF_CHOOSE:
            return
        # 盗贼选择身份由 GameService 根据卡池配置处理


@RoleExecutorRegistry.register(Role.WILD_CHILD)
class WildChildExecutor(RoleExecutor):
    """野孩子：第一晚选榜样，榜样出局则转变为狼人"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.WILD_CHILD_CHOOSE or not action.target_id:
            return
        target = state.get_player(action.target_id)
        if not target:
            return
        player.role_model = action.target_id


@RoleExecutorRegistry.register(Role.TREASURE_THIEF)
class TreasureThiefExecutor(RoleExecutor):
    """盗宝大师：持有三张身份牌，每夜切换身份"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type != ActionType.TREASURE_THIEF_SWITCH:
            return
        # 身份切换由 GameService 根据牌库处理


@RoleExecutorRegistry.register(Role.DANCER)
class DancerExecutor(RoleExecutor):
    """舞者：每夜选三名未进舞池的存活玩家，若恰好一人面具不同则其出局"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        if action.action_type == ActionType.DANCER_INVITE and action.payload:
            guests = action.payload.get("guest_ids", [])
            if len(guests) == 3:
                state.dancer_guests = guests


@RoleExecutorRegistry.register(Role.MUTE_ELDER)
class MuteElderExecutor(RoleExecutor):
    """禁言长老：白天能力"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


@RoleExecutorRegistry.register(Role.BEAR)
class BearExecutor(RoleExecutor):
    """熊：被动咆哮判定，不在夜晚行动"""
    async def execute_night(self, state: GameState, player: Player, action: Action) -> None:
        pass


async def execute_night_action(
    state: GameState, player: Player, action: Action
) -> None:
    """便捷方法：执行一个夜晚行动"""
    if player.role:
        await RoleExecutorRegistry.execute(player.role, state, player, action)


def get_executor(role: Role) -> RoleExecutor | None:
    return RoleExecutorRegistry.get(role)
