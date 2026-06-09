"""AI决策辅助 — 战术分类与策略选择"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ...models.role import Role, Faction


@dataclass
class TacticProfile:
    """战术画像"""
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)

    def to_prompt_snippet(self) -> str:
        return f"【{self.name}】{self.description}"


# 狼队战术库
WOLF_TACTICS = [
    TacticProfile(
        name="悍跳",
        description="冒充预言家/通灵师，编造夜间查验信息，争夺警徽。适合发言能力强、逻辑完整的AI执行。",
        keywords=["起跳", "查验", "金水", "查杀", "警徽流"],
    ),
    TacticProfile(
        name="冲锋",
        description="强势站边悍跳狼队友，用力度和逻辑压制真预言家，带动场风向。",
        keywords=["站边", "力度", "冲锋", "带队"],
    ),
    TacticProfile(
        name="倒钩",
        description="站边真预言家，合理质疑狼队友，追求深水生存到最后。适合前期需要隐藏的狼。",
        keywords=["倒钩", "站真预言家", "合理怀疑", "深水"],
    ),
    TacticProfile(
        name="深水倒钩",
        description="极深度倒钩，全程表现如好人，只在关键时刻投出对狼队有利的一票。",
        keywords=["深水", "低调", "关键票", "最后反转"],
    ),
    TacticProfile(
        name="阴阳倒钩",
        description="表面帮真预言家，实际散布错误逻辑和信息，误导好人推理方向。",
        keywords=["阳奉阴违", "递错误信息", "误导", "伪逻辑"],
    ),
    TacticProfile(
        name="垫飞",
        description="装作悍跳狼的'猪队友'，表现极差让真预言家看起来更可信，但投票时暗中帮狼队。",
        keywords=["假装猪队友", "演技", "反直觉"],
    ),
    TacticProfile(
        name="自刀",
        description="狼队夜间刀自己人制造银水身份，被刀者在白天获得女巫银水保护。高风险高收益。",
        keywords=["自刀", "银水", "高风险", "身份做高"],
    ),
    TacticProfile(
        name="淘汰/划水",
        description="跟随大部队，不主动发表立场意见，避免成为焦点。适合非关键位置的狼。",
        keywords=["划水", "不站边", "听发言", "低调"],
    ),
]


def assign_tactics(wolves: list[dict], difficulty: str) -> dict[str, TacticProfile]:
    """为狼队分配战术

    Args:
        wolves: 狼人玩家列表 [{"id": ..., "seat": ..., "role": ...}]
        difficulty: 难度等级

    Returns:
        {player_id: TacticProfile}
    """
    assignments: dict[str, TacticProfile] = {}

    if difficulty in {"novice", "basic"}:
        # 低难度：随机分配简单战术
        for w in wolves:
            assignments[w["id"]] = random.choice([WOLF_TACTICS[0], WOLF_TACTICS[1], WOLF_TACTICS[3]])
        return assignments

    # 高难度：协调分配
    available = list(WOLF_TACTICS)

    # 必有一人悍跳（除非配置不允许）
    jump_candidate = random.choice([t for t in available if t.name in {"悍跳", "冲锋"}])
    wolf_king = next((w for w in wolves if "king" in (w.get("role") or "").lower()), None)

    # 狼王/白狼王优先冲锋（因为它们出局能带人）
    if wolf_king:
        assignments[wolf_king["id"]] = next(t for t in available if t.name == "冲锋")
        available = [t for t in available if t.name != "冲锋"]

    for w in wolves:
        if w["id"] in assignments:
            continue
        tactic = random.choice(available)
        assignments[w["id"]] = tactic

    return assignments


# 好人神职夜间行动优先级
GOD_NIGHT_PRIORITIES = {
    Role.SEER: "优先查验警上/前置位未发言/行为可疑的玩家。若已知悍跳狼则优先验其金水以确认阵营。",
    Role.PSYCHIC: "优先查验场上被多人谈论但未发言的焦点位。通灵师看到具体身份，若场上有机械狼可能存在身份伪装。",
    Role.WITCH: "解药优先留给确定的好人，尤其是已跳身份的预言家。毒药在确定狼人身份后再使用，不确定的情况下空过。",
    Role.GUARD: "首夜空守或守自己。若预言家/通灵师已跳则优先守护。注意不要连续两天守同一人。",
    Role.DREAM_WEAVER: "优先摄梦被多人攻击/可疑的玩家以检验身份，或保护确定的好人。",
    Role.CROW: "优先诅咒被多人质疑但尚未确定身份的可疑玩家。",
    Role.MAGICIAN: "优先交换确定的好人与可能被刀的神职，分散狼刀风险。",
    Role.UNDERTAKER: "查验前一天被放逐者的身份以验证放逐是否正确。",
    Role.HUNTER_DEMON: "优先猎杀被多人指认且有逻辑漏洞的疑似狼人。若不确定则空过。",
}


def get_god_night_strategy(role: Role, difficulty: str) -> str:
    """获取神职夜晚行动策略"""
    base = GOD_NIGHT_PRIORITIES.get(role, "根据场况自行判断最佳目标。")
    if difficulty == "expert":
        return base + (
            "\n【大师补充】注意观察目标的行为模式和发言状态——真神职和悍跳狼在细节处有本质区别。"
            "抿神的本质是找视角差异——谁的信息量超出了Ta应该知道的范围。"
        )
    return base
