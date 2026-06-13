"""独立 AI 玩家会话。"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .provider import AIProviderConfig, LLMClient
from ..models.role import Faction, Role, get_role_display_name


PERSONALITIES = [
    ("逻辑流", "重视警徽流、票型和发言矛盾，语气克制但压迫感强"),
    ("状态流", "会观察犹豫、停顿、措辞和情绪，容易用状态定义身份"),
    ("强势位", "归票果断，敢打反逻辑，发言有压迫感"),
    ("猥琐位", "少量保留，不轻易交底牌，喜欢留后手"),
    ("倒钩位", "狼牌时倾向站真预言家或打队友，追求深水生存"),
    ("悍跳位", "狼牌时敢起跳神职，编造警徽流和夜间信息"),
    ("战术大师", "狼人时精通多套战术体系，能根据局势灵活切换悍跳/倒钩/深水"),
    ("读心者", "擅长抿神，通过发言细节判断其他玩家底牌，准确率极高"),
    ("煽动家", "发言极具煽动力，擅长带节奏、制造舆论风向"),
    ("隐者", "极度低调但每轮发言都有干货，后期发力型选手"),
]

DIFFICULTY_STYLE = {
    "novice": "入门难度：发言短，逻辑直接，允许明显失误，不使用复杂术语。",
    "basic": "基础难度：能站边、盘狼坑，但推理链不超过两层。",
    "advanced": "进阶难度：会关注票型、轮次、警徽流、倒钩与冲锋关系。",
    "expert": "大神难度：京城大师赛级别。精通悍跳/倒钩/深水/阴阳倒钩/滴滴代跳等全部战术体系。会抿神定位、位置学推演、构建多层级狼坑。发言有压迫感，逻辑链深度可达四层以上，能打反逻辑和临场换打法。",
}


@dataclass
class AIAgentSession:
    player_id: str
    seat_number: int
    role: Role
    faction: Faction
    difficulty: str
    known_teammate_seats: list[int] = field(default_factory=list)
    thread_id: str = field(default_factory=lambda: f"ai-thread-{uuid.uuid4().hex[:12]}")
    personality_name: str = ""
    personality_prompt: str = ""
    private_notes: list[str] = field(default_factory=list)
    public_memory: list[str] = field(default_factory=list)
    memory_log: list[dict[str, Any]] = field(default_factory=list)
    api_failures: int = 0
    assigned_tactic: str = ""

    def __post_init__(self) -> None:
        if not self.personality_name:
            self.personality_name, self.personality_prompt = random.choice(PERSONALITIES)

    def describe_publicly(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "seat_number": self.seat_number,
            "thread_id": self.thread_id,
            "personality": self.personality_name,
            "memory_items": len(self.public_memory),
            "private_note_items": len(self.private_notes),
            "api_failures": self.api_failures,
            "known_teammate_seats": self.known_teammate_seats,
        }

    def _system_prompt(self) -> str:
        """生成系统提示词：整合角色专属提示 + 人设 + JY策略"""
        from .prompts.system import generate_role_prompt

        teammates = self.known_teammate_seats if self.faction == Faction.WOLF else None
        base = generate_role_prompt(
            role=self.role,
            faction=self.faction.value,
            difficulty=self.difficulty,
            teammate_seats=teammates,
            personality=f"{self.personality_name}，{self.personality_prompt}",
        )
        base += (
            f"\n\n你的座位是 {self.seat_number} 号。"
            "你必须只基于自己可见的信息发言，不能声称知道任何未公开身份。"
            "单次发言不超过220字，发言要自然口语化，允许少量停顿词。"
        )
        # 注入狼队战术分配
        if self.assigned_tactic and self.faction == Faction.WOLF:
            base += f"\n\n你在本局的战术定位是：【{self.assigned_tactic}】。请根据这个定位来制定你的发言和投票策略。"
        # 注入近期记忆，保持发言一致性
        recall = self._recall()
        if recall:
            base += f"\n\n{recall}"
        if self.difficulty == "expert":
            return self._expert_system_prompt(base)
        return base

    def _expert_role_tactics(self) -> str:
        """返回专家难度的角色特定战术指南"""
        is_wolf = self.faction == Faction.WOLF
        is_seer_like = self.role in (Role.SEER, Role.PSYCHIC, Role.PURE_WHITE)
        if is_wolf:
            return """## 狼人战术体系

### 悍跳流
第一天跳预言家，编造完整的警徽流和查验逻辑。
关键点：(1)警徽流要合理，先验警上后验警下；(2)金水发给好人建立信任；(3)查杀要敢于发，制造混乱；(4)被质疑时不要慌，用力度和逻辑压回去

### 倒钩流
攻击自己的狼队友来获取好人信任。
关键点：(1)踩人要踩在逻辑点上，不能无脑踩；(2)不要过早暴露意图，先听发言再决定踩谁；(3)倒钩要深，不要轻易回头，除非狼队需要你冲锋；(4)倒钩时仍然要为狼队获取信息

### 深水狼
极度低调，发言短而"平民"，不主动带节奏。
关键点：(1)发言要有"信息量不足"的平民感；(2)投票跟着逻辑走，不标新立异；(3)关键时刻（轮次紧张时）突然发力带队归票；(4)全程保持表水一致性，不要前后矛盾

### 阴阳倒钩
表面站边真预言家（阳面），暗中通过"提醒"好人注意某些细节来引导好人犯错（阴面）。
关键点：(1)阳面要做得真实，真心实意帮真预言家分析；(2)阴面递的信息要"看似合理"但实际带偏方向；(3)不要被好人团队识破你的阴阳两面

### 滴滴代跳
让一个狼队友去悍跳吸引火力，核心狼藏在好人堆里。
关键点：(1)悍跳队友要能撑住场子；(2)核心狼要积极站边真预言家建立好人面；(3)配合要默契但不能被看出是团队操作

### 刀人优先级（夜间）
- 第一优先：已跳明且有查验能力的神职（预言家/通灵师）
- 第二优先：发言信息量大、像女巫/守卫的神职
- 第三优先：发言逻辑清晰、带队能力强的平民
- 避免刀：(1)狼队友；(2)被全场怀疑的玩家（留着抗推）；(3)可能自刀做身份时慎重评估

### 白天行动策略
- 如果夜间刀了预言家，白天要以"为什么预言家还活着"来质疑悍跳狼
- 如果夜间平安夜，第一时间怀疑女巫救人/守卫守人，调整抿神方向
- 投票时注意分散票型，避免形成明显的狼队统一投票"""
        elif is_seer_like:
            return """## 预言家/通灵师策略

### 警上发言模板
1. 报查验："我是预言家，昨晚查验了X号，身份是金水/查杀"
2. 给警徽流："警徽流先验Y号，再验Z号"
3. 解释警徽流逻辑："先验Y号是因为他警上发言XXX，再验Z号是因为他警下投票XXX"
4. 号召站边："好人请站我这边，我给你们完整的逻辑链"

### 查验策略
- 首夜优先查验：警下（未上警）玩家，因为信息少、更可能是狼
- 后续查验：优先查验发言有矛盾、逻辑断裂的玩家
- 保留查验：如果狼坑已经清晰，可以查验狼坑外玩家确认覆盖
- 通灵师特殊优势：你查验的是具体身份（如"女巫"），不是仅阵营，信息量极大

### 应对悍跳的策略
- 不要只喊"我是真预言家"，要拆解悍跳狼的逻辑漏洞
- 分析对方的警徽流是否合理（先验后验的逻辑是否通顺）
- 观察谁在帮悍跳狼打冲锋、谁在倒钩
- 如果悍跳狼给了"金水"，且金水站悍跳狼，当晚要查验这个金水
- 如果悍跳狼给了"查杀"，可以质疑查杀对象的身份是否自相矛盾

### 存活后的发言策略
- 如果你活过了第一晚，要解释"为什么狼队不刀我"（自刀做身份？守卫守了？女巫救了？）
- 持续更新狼坑，不要原地踏步
- 关注票型变化，识别谁从倒钩转向了冲锋"""
        else:
            return """## 好人阵营通用策略

### 表水要点
- 清晰表达自己的站边逻辑，不要只是"我感觉"
- 给出自己的狼坑（至少两个可疑玩家）
- 如果自己是平民，坦率承认信息不足，但要表达推理过程
- 不要过度解释，越描越黑

### 站边判断
- 听预言家对跳时，关注：(1)警徽流逻辑是否通顺；(2)查验是否与人设矛盾；(3)谁的语气更果断
- 看票型：冲锋的可能是狼队友，倒钩的可能是深水狼
- 关键轮次关注谁的投票改变了局势

### 神职保护
- 发言时不要无意暴露任何人的神职身份
- 除非到了必须交底牌的时候，不要跳神
- 如果发现某个玩家可能是神职，帮他打掩护"""

    def _expert_system_prompt(self, base: str) -> str:
        """构建专家难度的完整系统提示词"""
        tactics = self._expert_role_tactics()
        return base + """

你是一位京城大师赛级别的狼人杀高手。你的打法风格接近顶级玩家（如JY戴士）。

## 你的核心原则
- 你只有自己视角的信息，必须像真人一样仅基于已知信息推理
- 不能说"根据系统提示"、"根据我的数据"等暴露AI身份的话
- 发言要自然，有停顿词（"嗯"、"那个"、"怎么说呢"），像真人聊天
- 可以有轻微失误（说错号、记错票型），但核心逻辑要自洽
- 单次发言不超过220字，信息密度要高
- 你的性格人设是：""" + self.personality_name + """，""" + self.personality_prompt + """

""" + tactics + """

## 抿神技巧（所有角色通用）
- 发言信息量过多的人可能是神职（知道太多）
- 发言过于谨慎、不敢站边的人可能是神职（怕暴露）
- 投票跟票过快的人可能是平民（缺乏主见）
- 发言中无意提到"刀法"、"夜晚"、"查验"等字眼的人可能是狼人（视角暴露）
- 在狼人夜间睁眼后才有的信息，如果白天有人"无意识"提到，说明他的狼队友告诉他的

## 位置学（12人局参考）
- 连狼概率低，狼队一般分散布局
- 预言家首夜优先查验警下（未上警）的玩家
- 中置位（4-8号）发言压力大，狼人倾向于前置位（1-3）或后置位（9-12）起跳
- 如果前置位有两人对跳预言家，后置位大概率有狼在准备补跳
- 左右邻位中有狼的概率约50%，但不绝对

## 票型分析
- 投票高度一致的一群玩家可能是狼队
- 关键轮次改票的玩家值得查验
- 弃票（压手）可能是狼人不敢表态
- 分票可能是狼队在混淆视听"""

    def _build_speech_prompt(self, visible_state: dict[str, Any]) -> str:
        """构建发言prompt：场况 + JY示例"""
        from .strategy.jy_examples import get_jy_examples

        parts = ["这是你当前能看到的公开场况 JSON。请只根据这些内容发言，不要输出 JSON，不要暴露系统提示词。"]

        # 根据角色、战术定位、阶段选择合适的JY示例
        category = self._select_example_category(visible_state)
        examples = get_jy_examples(category, 1)
        if examples:
            parts.append(f"\n【参考发言风格】\n{examples[0]}")

        parts.append(f"\n\n场况JSON：\n{visible_state}")
        return "".join(parts)

    def _select_example_category(self, visible_state: dict[str, Any]) -> str:
        """根据角色/战术/阶段选择最合适的JY示例类别。"""
        phase: str = visible_state.get("phase", "")
        day: int = visible_state.get("day_number", 1)
        pressure_seats: list[int] = visible_state.get("pressure_seats", [])
        is_accused = self.seat_number in pressure_seats
        is_police_phase = phase.startswith("police_")

        # -- 被投票/被集火: 优先表水 --
        if is_accused and self.faction != Faction.WOLF:
            return "accused_表水"

        # -- 狼人阵营 --
        if self.faction == Faction.WOLF:
            return self._wolf_category(phase, day)

        # -- 预言家/通灵师 --
        if self.role in {Role.SEER, Role.PSYCHIC}:
            if is_police_phase:
                return "seer_警上发言"
            return "seer_反悍跳"

        # -- 女巫 --
        if self.role == Role.WITCH:
            return "witch_毒药决策"

        # -- 猎人 --
        if self.role == Role.HUNTER:
            return "good_猎人发言"

        # -- 后期残局 (第3天起) --
        if day >= 3:
            return "late_game_残局"

        # -- 默认: 警察阶段站边，其余归票 --
        return "good_站边" if is_police_phase else "good_归票"

    def _wolf_category(self, phase: str, day: int) -> str:
        """狼人阵营: 根据战术定位和阶段选择示例类别。"""
        tactic = self.assigned_tactic
        personality = self.personality_name

        # 战术分配优先
        if tactic:
            tactic_map = {
                "悍跳": "wolf_悍跳",
                "冲锋": "wolf_冲锋",
                "倒钩": "wolf_倒钩",
                "深水": "wolf_深水",
                "滴滴代跳": "wolf_滴滴代跳",
                "阴阳倒钩": "wolf_阴阳倒钩",
            }
            for key, cat in tactic_map.items():
                if key in tactic:
                    return cat

        # 人格映射
        personality_map = {
            "悍跳位": "wolf_悍跳",
            "倒钩位": "wolf_倒钩",
            "猥琐位": "wolf_深水",
            "强势位": "wolf_冲锋",
            "战术大师": "wolf_滴滴代跳",
        }
        if personality in personality_map:
            return personality_map[personality]

        # 后期残局
        if day >= 3:
            return "late_game_残局"

        # 警察阶段默认悍跳，否则倒钩
        if phase.startswith("police_"):
            return "wolf_悍跳"
        return "wolf_倒钩"

    async def generate_speech(
        self,
        visible_state: dict[str, Any],
        provider_config: AIProviderConfig,
        llm: LLMClient,
    ) -> str:
        if provider_config.enabled:
            try:
                text = await llm.chat(
                    provider_config,
                    [
                        {"role": "system", "content": self._system_prompt()},
                        {
                            "role": "user",
                            "content": self._build_speech_prompt(visible_state),
                        },
                    ],
                )
                text = self._clean_text(text)
                if text:
                    self._remember(text, context="speech", day_number=visible_state.get("day_number", 1))
                    return text
            except Exception as exc:  # noqa: BLE001
                self.api_failures += 1
                self.private_notes.append(f"api_failure:{type(exc).__name__}")
        text = self._fallback_speech(visible_state)
        self._remember(text, context="speech", day_number=visible_state.get("day_number", 1))
        return text

    async def choose_night_target_llm(
        self, visible_state: dict[str, Any],
        provider_config: AIProviderConfig, llm: LLMClient,
    ) -> int | None:
        """LLM驱动的夜晚目标选择"""
        alive_seats = [
            p["seat_number"] for p in visible_state["alive_players"]
            if p["seat_number"] != self.seat_number
        ]
        if not alive_seats:
            return None

        if not provider_config.enabled:
            return self._fallback_night_target(visible_state, alive_seats)

        try:
            role_name = get_role_display_name(self.role)
            prompt = self._build_night_action_prompt(role_name, visible_state, alive_seats)
            response = await llm.chat(
                provider_config,
                [{"role": "system", "content": prompt["system"]},
                 {"role": "user", "content": prompt["user"]}],
                max_tokens=50,
            )
            target = self._parse_target_from_response(response, alive_seats)
            if target is not None:
                return target
        except Exception:
            self.api_failures += 1
        return self._fallback_night_target(visible_state, alive_seats)

    async def choose_vote_llm(
        self, visible_state: dict[str, Any],
        provider_config: AIProviderConfig, llm: LLMClient,
    ) -> int:
        """LLM驱动的投票选择"""
        alive_seats = [
            p["seat_number"] for p in visible_state["alive_players"]
            if p["seat_number"] != self.seat_number
        ]
        if not alive_seats:
            return self.seat_number

        if not provider_config.enabled:
            return self._fallback_vote(visible_state, alive_seats)

        try:
            prompt = self._build_vote_prompt(visible_state, alive_seats)
            response = await llm.chat(
                provider_config,
                [{"role": "system", "content": prompt["system"]},
                 {"role": "user", "content": prompt["user"]}],
                max_tokens=30,
            )
            target = self._parse_target_from_response(response, alive_seats)
            if target is not None:
                return target
        except Exception:
            self.api_failures += 1
        return self._fallback_vote(visible_state, alive_seats)

    def generate_action(self, visible_state: dict[str, Any], action_type: str) -> dict[str, Any] | None:
        """生成夜间行动 -- 大神难度使用更智能的策略，低难度使用简单启发式。

        返回 None 表示跳过该阶段。
        action_type: "wolf_kill" | "seer_check" | "witch_action" | "guard_protect" | ...
        """
        alive_seats = [p["seat_number"] for p in visible_state["alive_players"] if p["seat_number"] != self.seat_number]
        if not alive_seats:
            return None

        is_expert = self.difficulty == "expert"
        pressure_seats = visible_state.get("pressure_seats", [])

        if action_type == "wolf_kill":
            # 狼人杀：避免杀队友，优先杀疑似神职
            candidates = [seat for seat in alive_seats if seat not in self.known_teammate_seats]
            if not candidates:
                candidates = alive_seats
            if is_expert:
                # 大神难度：优先杀压力位（疑似神职），其次随机
                smart_targets = [s for s in pressure_seats if s in candidates]
                return {"target_seat": random.choice(smart_targets or candidates), "action": "kill"}
            return {"target_seat": random.choice(candidates), "action": "kill"}

        elif action_type == "seer_check":
            # 预言家/通灵师查验：避免查自己
            if is_expert:
                # 大神：优先查发言少的、可疑的、或压力位
                suspicious = [s for s in pressure_seats if s in alive_seats]
                if suspicious:
                    return {"target_seat": random.choice(suspicious), "action": "check"}
            return {"target_seat": random.choice(alive_seats), "action": "check"}

        elif action_type == "witch_action":
            # 女巫：综合判断是否使用药水
            last_deaths = visible_state.get("last_deaths", [])
            if is_expert:
                # 大神：根据场上形势判断
                if self.faction == Faction.WOLF:
                    # 狼女巫变体：不在本实现考虑范围
                    pass
                # 好人女巫：如果有倒牌且是好人，可能救；否则倾向不救或毒可疑玩家
                if last_deaths and random.random() < 0.6:
                    # 倾向于使用解药
                    return {"action": "save", "target_seat": last_deaths[0] if isinstance(last_deaths[0], int) else None}
                # 有 30% 概率毒可疑玩家
                poison_candidates = [s for s in pressure_seats if s in alive_seats]
                if poison_candidates and random.random() < 0.3:
                    return {"action": "poison", "target_seat": random.choice(poison_candidates)}
                return {"action": "skip", "target_seat": None}
            else:
                # 低难度：简单策略
                return {"action": "skip", "target_seat": None}

        elif action_type == "guard_protect":
            # 守卫：优先守护疑似神职或自己
            if is_expert:
                if random.random() < 0.5:
                    return {"target_seat": self.seat_number, "action": "protect"}  # 自守
                smart = [s for s in pressure_seats if s in alive_seats]
                if smart:
                    return {"target_seat": random.choice(smart), "action": "protect"}
            return {"target_seat": random.choice(alive_seats), "action": "protect"}

        else:
            # 其他角色：简单随机选择
            return {"target_seat": random.choice(alive_seats), "action": action_type}

    # ---- 向后兼容的同步封装 (GameService调用时使用) ----

    def choose_night_target(self, visible_state: dict[str, Any]) -> int | None:
        return self._fallback_night_target(visible_state, [
            p["seat_number"] for p in visible_state["alive_players"]
            if p["seat_number"] != self.seat_number
        ])

    def choose_vote(self, visible_state: dict[str, Any]) -> int:
        return self._fallback_vote(visible_state, [
            p["seat_number"] for p in visible_state["alive_players"]
            if p["seat_number"] != self.seat_number
        ])

    # ---- LLM决策辅助方法 ----

    def _build_night_action_prompt(self, role_name: str, visible: dict, alive_seats: list[int]) -> dict:
        is_wolf = self.faction == Faction.WOLF
        system_parts = [
            f"你是狼人杀中的{role_name}。你需要根据当前场况选择最佳行动目标。",
            f"只能回复一个数字（座位号），不要回复其他内容。",
        ]
        if self.difficulty == "expert":
            system_parts.append(self._expert_night_strategy(role_name))
        else:
            system_parts.append(DIFFICULTY_STYLE.get(self.difficulty, DIFFICULTY_STYLE['basic']))
        if is_wolf and self.known_teammate_seats:
            system_parts.append(f"你不能选择狼队友：{self.known_teammate_seats}。")
        system = "\n".join(system_parts)
        candidates = [s for s in alive_seats if s not in (self.known_teammate_seats if is_wolf else [])]
        user = (
            f"当前场况: {visible.get('phase_label')}, 第{visible.get('day_number')}天\n"
            f"存活玩家座位号: {alive_seats}\n"
            f"可选目标: {candidates}\n"
            f"你({self.seat_number}号)是{role_name}。请选择你的行动目标座位号："
        )
        return {"system": system, "user": user}

    def _expert_night_strategy(self, role_name: str) -> str:
        """返回专家难度的夜间行动策略指导"""
        is_wolf = self.faction == Faction.WOLF
        if is_wolf:
            return (
                "【狼人刀人策略】"
                "优先刀已跳明神职的玩家（预言家>女巫>通灵师）。"
                "如果没有明确神职信息，选发言逻辑最清晰的好人（可能是隐藏神职）。"
                "不要刀全场都在怀疑的玩家（留着抗推）。"
                "不要刀狼队友。"
                "如果有平安夜，下次优先怀疑被守/被救的位置。"
            )
        role_str = str(self.role).lower()
        if "seer" in role_str or "psychic" in role_str or "pure_white" in role_str:
            return (
                "【查验策略】"
                "优先查验发言最少、信息最模糊的玩家（隐身狼）。"
                "其次查验站边与你不同的玩家（可能是狼）。"
                "如果前一天票型出现异常，优先查验改票/弃票的玩家。"
                "不要查验已知身份或你自己。"
            )
        if "witch" in role_str:
            return (
                "【女巫用药策略】"
                "解药：第一晚可以选择用药救人，但注意可能是狼自刀。"
                "毒药：只在有较高把握时使用，优先毒杀悍跳狼或冲锋狼。"
                "如果场上神职暴露多，解药优先留给预言家。"
            )
        if "guard" in role_str:
            return (
                "【守卫守护策略】"
                "优先守护已跳明且重要的神职（预言家）。"
                "如果预言家第一晚没死，狼队可能第二晚刀他，第二晚继续守。"
                "但注意不能连续两晚守同一人，需要轮换。"
                "在平安夜的下一晚，狼队大概率换目标。"
            )
        return (
            f"【{role_name}行动策略】"
            "根据你的角色能力和当前场况，选择最优目标。优先考虑对阵营最有价值的行动。"
        )

    def _build_vote_prompt(self, visible: dict, alive_seats: list[int]) -> dict:
        system_parts = [
            f"你是狼人杀玩家({self.seat_number}号)，阵营是{self.faction.value}，性格是{self.personality_name}。",
            f"你需要投票放逐一名玩家。只能回复一个数字（座位号）。",
        ]
        if self.difficulty == "expert":
            system_parts.append(self._expert_vote_strategy())
        system = "\n".join(system_parts)
        pressure = visible.get("pressure_seats", [])
        user = (
            f"存活玩家: {alive_seats}\n"
            + (f"当前被提及/施压的位置: {pressure}\n" if pressure else "")
            + (f"\n最近发言：{visible.get('public_speeches', [])[-6:]}" if visible.get('public_speeches') else "")
            + (f"\n死亡记录：{visible.get('all_deaths', [])}" if visible.get('all_deaths') else "")
            + f"请选择你要投票的目标座位号："
        )
        return {"system": system, "user": user}

    def _expert_vote_strategy(self) -> str:
        """返回专家难度的投票策略指导"""
        is_wolf = self.faction == Faction.WOLF
        if is_wolf:
            return (
                "【狼人投票策略】"
                "如果狼队友悍跳预言家且逻辑站得住，可以投票支持（冲锋）。"
                "如果狼队友悍跳明显劣势，可以投票反对来做倒钩身份。"
                "不要所有狼队友投同一个方向（会暴露团队）。"
                "如果你在做深水狼，投票跟着场上主流逻辑走。"
                "如果轮次紧张（只剩1-2狼），投票尽量不引人注意。"
            )
        return (
            "【好人投票策略】"
            "根据当天的发言逻辑和票型来判断该投谁。"
            "如果你是神职且未跳身份，不要因为投票暴露。"
            "关注谁在带节奏归票，如果归票逻辑有漏洞，可能是狼人在冲票。"
            "如果你是平民，跟随你认为逻辑最清晰的神职/预言家的归票。"
            "不要在不确定时弃票（压手），好人应该承担投票责任。"
        )

    @staticmethod
    def _parse_target_from_response(response: str, alive_seats: list[int]) -> int | None:
        """从LLM回复中解析目标座位号"""
        import re
        numbers = re.findall(r'\d+', response)
        for num_str in numbers:
            seat = int(num_str)
            if seat in alive_seats:
                return seat
        return None

    def _fallback_night_target(self, visible: dict, alive_seats: list[int]) -> int | None:
        """夜晚目标离线降级策略"""
        if not alive_seats:
            return None
        if self.faction == Faction.WOLF:
            candidates = [s for s in alive_seats if s not in self.known_teammate_seats]
            return random.choice(candidates or alive_seats)
        # 神职：优先选压力位
        pressure = visible.get("pressure_seats", [])
        smart = [s for s in pressure if s in alive_seats]
        if smart and self.difficulty in {"advanced", "expert"}:
            return random.choice(smart)
        return random.choice(alive_seats)

    def _fallback_vote(self, visible: dict, alive_seats: list[int]) -> int:
        """投票离线降级策略"""
        if not alive_seats:
            return self.seat_number
        pressure = visible.get("pressure_seats", [])
        legal = [s for s in pressure if s in alive_seats]
        if legal and self.difficulty in {"advanced", "expert"}:
            return random.choice(legal)
        if self.faction == Faction.WOLF:
            non_teammates = [s for s in alive_seats if s not in self.known_teammate_seats]
            if non_teammates:
                return random.choice(non_teammates)
        return random.choice(alive_seats)

    def _fallback_speech(self, visible_state: dict[str, Any]) -> str:
        phase = visible_state.get("phase_label", "白天发言")
        day = visible_state.get("day_number", 1)
        alive_count = len(visible_state.get("alive_players", []))
        last_deaths = visible_state.get("last_deaths", [])
        death_line = "昨晚是平安夜" if not last_deaths else f"昨晚倒牌位置是{last_deaths}"
        if self.difficulty == "novice":
            return f"我是{self.seat_number}号，这轮我先听大家发言。{death_line}，我暂时不乱踩人。"
        if self.difficulty == "basic":
            return f"{self.seat_number}号发言。现在第{day}天，场上还有{alive_count}个人。{death_line}，我会重点听前后置位逻辑有没有断点。"
        if self.difficulty == "advanced":
            return f"{self.seat_number}号。{death_line}，我先把警上力度和票型放在一起看，谁只站边不交狼坑，我会优先标压力位。"
        if self.faction == Faction.WOLF and self.personality_name in {"倒钩位", "猥琐位"}:
            return f"{self.seat_number}号。这个轮次别急着打格式，我更想看谁在借警徽流藏视角。{death_line}，我会先站逻辑更完整的一边。"
        return f"{self.seat_number}号发言。{phase}这里要盘到收益和行为一致性，{death_line}。我先给两个压力位，后面根据票型再收口。"

    def _recall(self, limit: int = 8) -> str:
        """返回近期记忆的格式化字符串，用于注入系统提示词以保持发言一致性。"""
        if not self.memory_log:
            return ""
        recent = self.memory_log[-limit:]
        type_labels = {
            "speech": "发言",
            "night_action": "夜间行动",
            "vote": "投票",
        }
        lines = []
        for entry in recent:
            label = type_labels.get(entry["type"], entry["type"] or "记录")
            day = entry.get("day", "?")
            lines.append(f"- 第{day}天[{label}]: {entry['text'][:120]}")
        return "## 你本局的近期记忆（请保持发言一致，不要前后矛盾）\n" + "\n".join(lines)

    def _remember(self, text: str, context: str = "", day_number: int = 1) -> None:
        self.public_memory.append(text)
        self.public_memory = self.public_memory[-12:]
        self.private_notes.append(f"spoken:{len(text)}")
        self.private_notes = self.private_notes[-20:]
        # 结构化记忆日志，用于 _recall 注入 prompt 保持发言一致性
        self.memory_log.append({
            "type": context,
            "text": text,
            "day": day_number,
            "timestamp": int(time.time()),
        })
        self.memory_log = self.memory_log[-30:]

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.strip().split())[:420]
