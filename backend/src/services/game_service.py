"""游戏业务编排 — 完整流程编排器（暂停式夜晚流程）

GameService 是裁判和房间管理器。
- 任何 AI 调用只能拿 visible_state，不能拿完整 GameState
- 夜晚/白天流程按顺序自动推进
- 人类玩家在需要操作时等待 API 输入
"""

from __future__ import annotations

import asyncio
import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..ai.provider import AIProviderConfig, LLMClient
from ..ai.session import AIAgentSession
from ..data.boards import BOARDS, BOARDS_BY_ID
from ..engine.win_checker import WinChecker
from ..engine.role_executor import execute_night_action
from ..models.board import BoardConfig
from ..models.game import (
    Action, ActionType, GamePhase, GameState,
    NightResult, SpeechRecord, VoteRecord,
)
from ..models.player import Player
from ..models.role import Faction, ROLE_CONFIG, Role, get_role_display_name, is_wolf_team
from ..api.ws_manager import ws_manager


PHASE_LABELS = {
    GamePhase.LOBBY: "大厅",
    GamePhase.ROLE_DEALT: "身份确认",
    GamePhase.NIGHT_START: "天黑请闭眼",
    GamePhase.NIGHT_MAGICIAN: "魔术师行动",
    GamePhase.NIGHT_THIEF: "盗贼行动",
    GamePhase.NIGHT_CUPID: "丘比特行动",
    GamePhase.NIGHT_LOVERS: "情侣相认",
    GamePhase.NIGHT_WILD_CHILD: "野孩子行动",
    GamePhase.NIGHT_MECH_WOLF: "机械狼行动",
    GamePhase.NIGHT_NIGHTMARE: "梦魇行动",
    GamePhase.NIGHT_WOLF_KILL: "狼人刀人",
    GamePhase.NIGHT_WOLF_BEAUTY: "狼美人魅惑",
    GamePhase.NIGHT_GARGOYLE: "石像鬼查验",
    GamePhase.NIGHT_WITCH: "女巫行动",
    GamePhase.NIGHT_GUARD: "守卫行动",
    GamePhase.NIGHT_SEER: "预言家查验",
    GamePhase.NIGHT_CROW: "乌鸦行动",
    GamePhase.NIGHT_END: "夜晚结算",
    GamePhase.DAY_DEATH_ANNOUNCE: "宣布死讯",
    GamePhase.POLICE_REGISTER: "警长竞选报名",
    GamePhase.POLICE_SPEECH: "警上发言",
    GamePhase.POLICE_WITHDRAW: "警上退水",
    GamePhase.POLICE_VOTE: "警长投票",
    GamePhase.POLICE_PK: "警长PK",
    GamePhase.POLICE_RESULT: "警长结果",
    GamePhase.DAY_DISCUSS: "白天发言",
    GamePhase.DAY_VOTE: "放逐投票",
    GamePhase.DAY_PK: "平票PK发言",
    GamePhase.DAY_VOTE_RESULT: "投票结果",
    GamePhase.GAME_OVER: "游戏结束",
}

AI_NAMES = ["星河", "南烛", "青岚", "月白", "阿澈", "闻舟", "林野", "迟夏", "砚秋", "北辰", "小满", "砚声"]


@dataclass
class GameRuntime:
    state: GameState
    board: BoardConfig
    provider_config: AIProviderConfig
    agents: dict[str, AIAgentSession] = field(default_factory=dict)
    llm: LLMClient = field(default_factory=LLMClient)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    pk_pending_seats: list[int] = field(default_factory=list)
    pending_human_prompt: str | None = None  # 等待人类玩家操作时的提示
    pending_human_action_type: str | None = None  # ActionType values: wolf_kill, seer_check, witch_save, etc.
    night_phase_index: int = 0  # 夜晚阶段进度：0=未开始, 1-99=阶段编号
    night_phases_queue: list[tuple[GamePhase, Role | None, ActionType | None]] = field(default_factory=list)
    police_elected: bool = False  # 警长是否已竞选


class GameService:
    def __init__(self) -> None:
        self._games: dict[str, GameRuntime] = {}

    # ================================================================
    # 公开 API
    # ================================================================

    def list_boards(self) -> list[dict[str, Any]]:
        return [self._board_to_dict(board) for board in BOARDS]

    def create_game(
        self,
        board_id: str,
        difficulty: str,
        human_name: str,
        human_role: str | None,
        provider_config: AIProviderConfig,
    ) -> dict[str, Any]:
        if board_id not in BOARDS_BY_ID:
            raise ValueError(f"未知板子: {board_id}")
        board = BOARDS_BY_ID[board_id]
        if difficulty not in board.difficulty and difficulty != "expert":
            raise ValueError(f"{board.name} 不支持难度 {difficulty}")

        game_id = uuid.uuid4().hex
        roles = self._roles_for_board(board)
        chosen_human_role = self._choose_human_role(roles, human_role)
        roles.remove(chosen_human_role)
        random.shuffle(roles)

        human = self._new_player(1, human_name or "你", chosen_human_role, is_human=True)
        ai_players = [
            self._new_player(seat, AI_NAMES[(seat - 2) % len(AI_NAMES)], role, is_human=False)
            for seat, role in zip(range(2, board.player_count + 1), roles, strict=False)
        ]

        state = GameState(
            game_id=game_id,
            board_id=board.id,
            difficulty=difficulty,
            players=[human, *ai_players],
            phase=GamePhase.ROLE_DEALT,
            day_number=1,
            is_first_night=True,
            remaining_last_words=board.player_count // 2,  # 遗言数量
        )
        runtime = GameRuntime(state=state, board=board, provider_config=provider_config)
        runtime.agents = self._create_agents(state, difficulty)
        runtime.timeline.append({
            "type": "system",
            "text": f"本局为{board.name}，{board.player_count}人，{'带上警' if board.has_police else '不上警'}。",
        })
        runtime.timeline.append({"type": "system", "text": f"你的身份是{get_role_display_name(chosen_human_role)}。"})
        self._games[game_id] = runtime
        return self.get_game(game_id)

    def get_game(self, game_id: str) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        result = self._runtime_to_dict(runtime)
        # 通过WebSocket广播最新状态
        asyncio.create_task(self._broadcast_state(game_id, result, runtime))
        return result

    async def _broadcast_state(
        self, game_id: str, game_dict: dict[str, Any], runtime: GameRuntime,
    ) -> None:
        """广播游戏状态变更到WebSocket客户端"""
        try:
            await ws_manager.broadcast(game_id, {
                "type": "state_update",
                "data": game_dict,
            })
        except Exception:
            pass  # WebSocket广播失败不阻塞游戏流程

    # ---- 夜晚流程 ----

    async def process_first_night(self, game_id: str) -> dict[str, Any]:
        """处理首夜（自动执行所有首夜专属阶段，遇到人类玩家时暂停）"""
        runtime = self._get_runtime(game_id)
        if runtime.state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)
        await self._run_first_night(runtime)
        return self.get_game(game_id)

    async def process_night(self, game_id: str) -> dict[str, Any]:
        """处理夜晚流程（非首夜）"""
        runtime = self._get_runtime(game_id)
        if runtime.state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)
        await self._run_night(runtime)
        return self.get_game(game_id)

    async def submit_human_night_action(
        self, game_id: str, action_type: str, target_seat: int | None = None,
        second_target_seat: int | None = None,
    ) -> dict[str, Any]:
        """人类玩家提交夜晚行动，然后继续夜晚流程"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        if not human:
            raise ValueError("缺少人类玩家")

        target = state.get_player_by_seat(target_seat) if target_seat else None
        second_target = state.get_player_by_seat(second_target_seat) if second_target_seat else None

        action = Action(
            player_id=human.id,
            action_type=ActionType(action_type),
            target_id=target.id if target else None,
            second_target_id=second_target.id if second_target else None,
        )
        if human.role:
            await execute_night_action(state, human, action)

        runtime.pending_human_prompt = None
        runtime.pending_human_action_type = None

        # 推进阶段索引并继续处理队列
        runtime.night_phase_index += 1
        await self._process_night_queue(runtime, first_night=state.is_first_night)
        return self.get_game(game_id)

    # ---- 白天流程 ----

    async def process_day_phases(self, game_id: str) -> dict[str, Any]:
        """处理完整白天流程"""
        runtime = self._get_runtime(game_id)
        if runtime.state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)
        await self._run_day(runtime)
        return self.get_game(game_id)

    def submit_human_speech(self, game_id: str, text: str) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        if not human:
            raise ValueError("缺少人类玩家")
        clean = " ".join(text.strip().split())[:600]
        if not clean:
            raise ValueError("发言不能为空")
        record = SpeechRecord(
            player_id=human.id, text=clean,
            phase=state.phase, day_number=state.day_number,
        )
        state.speech_history.append(record)
        human.has_spoken = True
        runtime.timeline.append({
            "type": "speech", "text": f"{human.seat_number}号：{clean}", "player_id": human.id,
        })
        runtime.pending_human_prompt = None
        runtime.pending_human_action_type = None
        return self.get_game(game_id)

    async def run_ai_speeches(self, game_id: str) -> dict[str, Any]:
        """批量生成所有未发言AI的发言"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        if state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)

        unspoken = [p for p in state.get_alive_players() if not p.is_human and not p.has_spoken]

        async def speak(player: Player) -> SpeechRecord | None:
            agent = runtime.agents.get(player.id)
            if not agent:
                return None
            visible = self._visible_state(runtime, player.id)
            text = await agent.generate_speech(visible, runtime.provider_config, runtime.llm)
            return SpeechRecord(
                player_id=player.id, text=text,
                phase=state.phase, day_number=state.day_number,
            )

        records: list[SpeechRecord] = []
        # 按座位号顺序发言
        for player in sorted(unspoken, key=lambda p: p.seat_number):
            record = await speak(player)
            if record:
                state.speech_history.append(record)
                records.append(record)
                player.has_spoken = True
                runtime.timeline.append({
                    "type": "speech", "text": f"{player.seat_number}号：{record.text}",
                    "player_id": player.id,
                })

        # 所有人发完言后自动进入投票阶段
        if not unspoken and not any(
            p.is_human and not p.has_spoken for p in state.get_alive_players()
        ):
            state.phase = GamePhase.DAY_VOTE

        return {**self.get_game(game_id), "new_speeches": [
            self._speech_to_dict(runtime, r) for r in records
        ]}

    def submit_human_vote(self, game_id: str, target_seat: int) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        target = state.get_player_by_seat(target_seat)
        if not human or not target or not target.is_alive:
            raise ValueError("投票目标无效")

        self._record_human_vote(state, human, target)
        runtime.pending_human_prompt = None
        runtime.pending_human_action_type = None
        return self.get_game(game_id)

    def start_vote_phase(self, game_id: str) -> dict[str, Any]:
        """从发言阶段切换到投票阶段"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        if state.phase == GamePhase.DAY_DISCUSS:
            state.phase = GamePhase.DAY_VOTE
        return self.get_game(game_id)

    async def resolve_votes(self, game_id: str) -> dict[str, Any]:
        """结算所有AI投票并处理放逐结果"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        if state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)

        # 收集所有AI投票
        total_records = list(state.vote_records)
        pressure = self._pressure_seats(runtime)
        for player in state.get_alive_players():
            if player.is_human:
                continue
            agent = runtime.agents.get(player.id)
            if not agent:
                continue
            visible = self._visible_state(runtime, player.id)
            visible["pressure_seats"] = pressure
            ai_target_seat = agent.choose_vote(visible)
            ai_target = state.get_player_by_seat(ai_target_seat)
            if ai_target and ai_target.is_alive:
                total_records.append(VoteRecord(
                    voter_id=player.id, target_id=ai_target.id,
                    is_sheriff_vote=player.is_sheriff,
                    is_cursed_vote=player.cursed_by_crow,
                ))

        state.vote_records = total_records
        self._process_vote_result(runtime, total_records)
        return self.get_game(game_id)

    # ---- 特殊行动 ----

    def self_explode(self, game_id: str, target_seat: int) -> dict[str, Any]:
        """狼人自爆（白狼王/黑狼王）"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        if not human or human.role not in {Role.WHITE_WOLF_KING, Role.BLACK_WOLF_KING}:
            raise ValueError("只有白狼王或黑狼王可以自爆")

        self._kill_player(state, human, "self_explode")
        state.self_explode_count += 1

        target = state.get_player_by_seat(target_seat)
        if target and target.is_alive:
            self._kill_player(state, target, "wolf_explode_kill")
            runtime.timeline.append({
                "type": "death",
                "text": f"{human.seat_number}号自爆，带走了{target_seat}号。",
            })

        winner = WinChecker.check(state)
        if winner:
            state.winner = winner
            state.phase = GamePhase.GAME_OVER
        else:
            state.phase = GamePhase.NIGHT_START
            state.day_number += 1

        return self.get_game(game_id)

    def hunter_shoot(self, game_id: str, target_seat: int) -> dict[str, Any]:
        """猎人开枪"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        target = state.get_player_by_seat(target_seat)
        if not target or not target.is_alive:
            raise ValueError("目标无效")
        self._kill_player(state, target, "hunter_shoot")
        runtime.timeline.append({
            "type": "death",
            "text": f"猎人开枪带走了{target_seat}号。",
        })
        runtime.pending_human_prompt = None
        return self._check_game_over(runtime)

    def knight_duel(self, game_id: str, target_seat: int) -> dict[str, Any]:
        """骑士决斗"""
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        target = state.get_player_by_seat(target_seat)
        if not human or not target or not target.is_alive:
            raise ValueError("目标无效")
        human.has_dueled = True

        if target.faction == Faction.WOLF:
            self._kill_player(state, target, "knight_duel")
            runtime.timeline.append({
                "type": "death", "text": f"骑士决斗{target_seat}号，{target_seat}号是狼人，出局！",
            })
        else:
            self._kill_player(state, human, "knight_duel_fail")
            runtime.timeline.append({
                "type": "death", "text": f"骑士决斗{target_seat}号，{target_seat}号是好人，骑士出局！",
            })
        return self._check_game_over(runtime)

    # ---- 工具方法 ----

    async def test_provider(self, provider_config: AIProviderConfig) -> dict[str, Any]:
        if not provider_config.enabled:
            return {"ok": True, "mode": "offline", "message": "离线策略可用"}
        llm = LLMClient()
        text = await llm.chat(
            provider_config,
            [{"role": "system", "content": "你只需要回复'连接正常'。"},
             {"role": "user", "content": "测试连接。"}],
            max_tokens=20,
        )
        return {"ok": True, "mode": provider_config.provider, "message": text[:80]}

    # ================================================================
    # 夜晚流程实现
    # ================================================================

    async def _run_first_night(self, runtime: GameRuntime) -> None:
        """执行首夜：构建阶段队列，逐步处理，遇到人类玩家时暂停"""
        state = runtime.state
        state.phase = GamePhase.NIGHT_START
        state.day_number = 1

        # 构建首夜阶段队列
        queue: list[tuple[GamePhase, Role | None, ActionType | None, str]] = []
        queue.append((GamePhase.NIGHT_WOLF_KILL, None, ActionType.WOLF_KILL, "选择袭击目标"))
        queue.append((GamePhase.NIGHT_GARGOYLE, Role.GARGOYLE, ActionType.GARGOYLE_CHECK, "查验一名玩家"))
        queue.append((GamePhase.NIGHT_WITCH, Role.WITCH, ActionType.WITCH_SAVE, "是否使用解药"))
        queue.append((GamePhase.NIGHT_GUARD, Role.GUARD, ActionType.GUARD_PROTECT, "选择守护目标"))
        queue.append((GamePhase.NIGHT_SEER, None, ActionType.SEER_CHECK, "选择查验目标"))
        # 一次性角色（仅首夜）
        if self._has_role_alive(state, Role.THIEF):
            queue.append((GamePhase.NIGHT_THIEF, Role.THIEF, ActionType.THIEF_CHOOSE, "选择身份牌"))
        if self._has_role_alive(state, Role.CUPID):
            queue.append((GamePhase.NIGHT_CUPID, Role.CUPID, ActionType.CUPID_LINK, "选择情侣"))
        if self._has_role_alive(state, Role.WILD_CHILD):
            queue.append((GamePhase.NIGHT_WILD_CHILD, Role.WILD_CHILD, ActionType.WILD_CHILD_CHOOSE, "选择榜样"))

        runtime.night_phases_queue = queue
        runtime.night_phase_index = 0
        await self._process_night_queue(runtime, first_night=True)

    async def _run_night(self, runtime: GameRuntime) -> None:
        """执行非首夜"""
        state = runtime.state
        state.phase = GamePhase.NIGHT_START

        # 重置发言标记
        for p in state.players:
            p.has_spoken = False

        queue: list[tuple[GamePhase, Role | None, ActionType | None, str]] = []
        if self._has_role_alive(state, Role.MECHANICAL_WOLF):
            queue.append((GamePhase.NIGHT_MECH_WOLF, Role.MECHANICAL_WOLF, ActionType.MECH_WOLF_LEARN, "选择学习目标"))
        if self._has_role_alive(state, Role.NIGHTMARE):
            queue.append((GamePhase.NIGHT_NIGHTMARE, Role.NIGHTMARE, ActionType.NIGHTMARE_BLOCK, "选择封锁目标"))
        queue.append((GamePhase.NIGHT_WOLF_KILL, None, ActionType.WOLF_KILL, "选择袭击目标"))
        if self._has_role_alive(state, Role.WOLF_BEAUTY):
            queue.append((GamePhase.NIGHT_WOLF_BEAUTY, Role.WOLF_BEAUTY, ActionType.WOLF_BEAUTY_CHARM, "选择魅惑目标"))
        if self._has_role_alive(state, Role.GARGOYLE):
            queue.append((GamePhase.NIGHT_GARGOYLE, Role.GARGOYLE, ActionType.GARGOYLE_CHECK, "查验一名玩家"))
        queue.append((GamePhase.NIGHT_WITCH, Role.WITCH, ActionType.WITCH_SAVE, "是否使用解药"))
        queue.append((GamePhase.NIGHT_GUARD, Role.GUARD, ActionType.GUARD_PROTECT, "选择守护目标"))
        queue.append((GamePhase.NIGHT_SEER, None, ActionType.SEER_CHECK, "选择查验目标"))
        if self._has_role_alive(state, Role.DREAM_WEAVER):
            queue.append((GamePhase.NIGHT_SEER, Role.DREAM_WEAVER, ActionType.DREAM_WEAVER_TARGET, "选择摄梦目标"))
        if self._has_role_alive(state, Role.CROW):
            queue.append((GamePhase.NIGHT_CROW, Role.CROW, ActionType.CROW_CURSE, "选择诅咒目标"))
        if self._has_role_alive(state, Role.MAGICIAN):
            queue.append((GamePhase.NIGHT_MAGICIAN, Role.MAGICIAN, ActionType.MAGICIAN_SWAP, "选择交换目标"))

        runtime.night_phases_queue = queue
        runtime.night_phase_index = 0
        await self._process_night_queue(runtime, first_night=False)

    async def _process_night_queue(self, runtime: GameRuntime, first_night: bool) -> None:
        """处理夜晚阶段队列：执行AI行动，遇到人类时暂停等待"""
        state = runtime.state
        queue = runtime.night_phases_queue

        while runtime.night_phase_index < len(queue):
            phase, role, action_type, prompt_hint = queue[runtime.night_phase_index]
            state.phase = phase

            if phase == GamePhase.NIGHT_WOLF_KILL:
                # 狼人刀人：特殊处理
                human = state.get_human_player()
                if human and human.faction == Faction.WOLF:
                    runtime.pending_human_prompt = "选择今晚的袭击目标"
                    runtime.pending_human_action_type = "wolf_kill"
                    return
                await self._execute_wolf_kill(runtime)

            elif role is None:
                # 复合阶段（如 Seer + Psychic + PureWhite）
                human_needs_act = False
                for p in state.get_alive_players():
                    if p.role in {Role.SEER, Role.PSYCHIC, Role.PURE_WHITE}:
                        if p.is_human:
                            runtime.pending_human_prompt = prompt_hint
                            runtime.pending_human_action_type = "seer_check"
                            human_needs_act = True
                            break
                        await self._ai_night_action(runtime, p, action_type)
                if human_needs_act:
                    return

            else:
                # 单角色阶段
                human_needs_act = False
                for p in state.get_alive_players():
                    if p.role != role:
                        continue
                    if p.is_human:
                        runtime.pending_human_prompt = prompt_hint
                        runtime.pending_human_action_type = action_type.value if action_type else "night_action"
                        human_needs_act = True
                        break
                    if action_type == ActionType.WITCH_SAVE:
                        await self._ai_witch_action(runtime, p)
                    elif action_type:
                        await self._ai_night_action(runtime, p, action_type)
                if human_needs_act:
                    return

            runtime.night_phase_index += 1

        # 所有阶段处理完毕，结算夜晚死亡
        await self._resolve_night_deaths(runtime)
        if first_night:
            state.is_first_night = False

        # 过渡到白天
        winner = WinChecker.check(state)
        if winner:
            state.winner = winner
            state.phase = GamePhase.GAME_OVER
            runtime.timeline.append({"type": "game_over", "text": f"{self._winner_label(winner)}获胜。"})
        else:
            state.phase = GamePhase.DAY_DISCUSS

    async def _execute_night_phase(
        self, runtime: GameRuntime, phase: GamePhase,
        role: Role | None, action_type: ActionType | None,
        is_lovers_meet: bool = False,
    ) -> None:
        """执行单个夜晚阶段"""
        state = runtime.state
        state.phase = phase

        if is_lovers_meet:
            # 情侣相认（仅通知）
            for a_id, b_id in state.lover_pairs:
                a = state.get_player(a_id)
                b = state.get_player(b_id)
                if a and b and not a.is_human and not b.is_human:
                    pass  # AI 情侣相认通过 visible_state 处理
            return

        if role is None:
            # 复合阶段（如 Seer + Psychic）
            for p in state.get_alive_players():
                if p.is_human:
                    continue
                if p.role in {Role.SEER, Role.PSYCHIC, Role.PURE_WHITE}:
                    await self._ai_night_action(runtime, p, ActionType.SEER_CHECK)
            return

        # 单角色阶段
        for p in state.get_alive_players():
            if p.role != role:
                continue
            if p.is_human:
                # 人类玩家需要手动操作
                runtime.pending_human_prompt = (
                    f"请选择{'查验' if 'check' in (action_type.value if action_type else '') else '行动'}目标"
                )
                runtime.pending_human_action_type = action_type.value if action_type else "night_action"
                return
            if action_type:
                await self._ai_night_action(runtime, p, action_type)

    async def _execute_wolf_kill(self, runtime: GameRuntime) -> None:
        """执行狼人刀人阶段"""
        state = runtime.state
        state.phase = GamePhase.NIGHT_WOLF_KILL

        state.wolf_kill_target = None
        wolf_targets: list[str] = []

        # 收集所有已知彼此存在的狼人投票
        regular_wolves = [
            p for p in state.get_alive_players()
            if p.faction == Faction.WOLF
            and p.role not in {Role.MECHANICAL_WOLF, Role.GARGOYLE, Role.HIDDEN_WOLF}
        ]

        human = state.get_human_player()
        for wolf in regular_wolves:
            if wolf.is_human:
                continue
            agent = runtime.agents.get(wolf.id)
            if not agent:
                continue
            visible = self._visible_state(runtime, wolf.id)
            target_seat = agent.choose_night_target(visible)
            if target_seat:
                target = state.get_player_by_seat(target_seat)
                if target and target.is_alive and target.faction != Faction.WOLF:
                    wolf_targets.append(target.id)

        # 多数决
        if wolf_targets:
            state.wolf_kill_target = max(set(wolf_targets), key=wolf_targets.count)

    async def _ai_night_action(
        self, runtime: GameRuntime, player: Player, action_type: ActionType,
    ) -> None:
        """AI自动执行夜晚行动"""
        state = runtime.state
        agent = runtime.agents.get(player.id)
        if not agent:
            return

        visible = self._visible_state(runtime, player.id)
        target_seat = agent.choose_night_target(visible)

        if target_seat is None:
            return

        target = state.get_player_by_seat(target_seat)
        if not target or not target.is_alive:
            return

        action = Action(
            player_id=player.id,
            action_type=action_type,
            target_id=target.id,
        )
        await execute_night_action(state, player, action)

    async def _ai_witch_action(self, runtime: GameRuntime, player: Player) -> None:
        """AI女巫决策：是否救/毒"""
        state = runtime.state
        agent = runtime.agents.get(player.id)
        if not agent:
            return

        visible = self._visible_state(runtime, player.id)
        last_deaths = visible.get("last_deaths", [])

        # 解药决策：有人被刀且女巫有解药
        if player.has_antidote and state.wolf_kill_target:
            # 简单策略：50%概率救（避免全救或全不救）
            should_save = state.difficulty == "expert" or random.random() < 0.5
            if should_save:
                save_action = Action(
                    player_id=player.id,
                    action_type=ActionType.WITCH_SAVE,
                )
                await execute_night_action(state, player, save_action)
                return

        # 毒药决策：第二天以后，有压力位目标时
        if player.has_poison and state.day_number > 1:
            target_seat = agent.choose_night_target(visible)
            if target_seat and random.random() < 0.3:  # 30%概率毒人
                target = state.get_player_by_seat(target_seat)
                if target and target.is_alive and target.faction != Faction.WOLF:
                    poison_action = Action(
                        player_id=player.id,
                        action_type=ActionType.WITCH_POISON,
                        target_id=target.id,
                    )
                    await execute_night_action(state, player, poison_action)

    async def _resolve_night_deaths(self, runtime: GameRuntime) -> None:
        """夜晚死亡结算"""
        state = runtime.state
        state.phase = GamePhase.NIGHT_END

        deaths: list[dict[str, Any]] = []
        killed_ids: set[str] = set()

        wolf_target = state.wolf_kill_target
        guard_target = state.guard_target
        witch_save = state.witch_save_target

        # ---- 狼刀结算 ----
        if wolf_target:
            wolf_victim = state.get_player(wolf_target)
            if wolf_victim:
                # 咒狐免疫狼刀
                if wolf_victim.role == Role.CURSED_FOX:
                    pass  # 咒狐不死
                elif wolf_victim.role == Role.EVIL_KNIGHT:
                    pass  # 恶灵骑士夜晚不死
                elif guard_target == wolf_target:
                    pass  # 守卫保护
                elif witch_save == wolf_target:
                    pass  # 女巫救活
                elif wolf_victim.dream_blocked:
                    pass  # 摄梦人保护
                else:
                    killed_ids.add(wolf_target)

        # ---- 女巫毒药结算 ----
        if state.witch_poison_target:
            poison_victim = state.get_player(state.witch_poison_target)
            if poison_victim and poison_victim.is_alive:
                if poison_victim.role != Role.EVIL_KNIGHT:
                    killed_ids.add(state.witch_poison_target)
                    poison_victim.can_shoot = False  # 被毒的猎人不能开枪

        # ---- 处理守护/救活标记 ----
        for pid in {wolf_target or "", guard_target or "", witch_save or ""}:
            if pid:
                p = state.get_player(pid)
                if p:
                    p.protected_by_guard = (pid == guard_target)
                    p.protected_by_witch = (pid == witch_save)

        # ---- 死亡链式传播 ----
        chain = WinChecker.get_death_chain(state, killed_ids, "wolf_kill")
        for extra_pid in chain:
            killed_ids.add(extra_pid)

        # ---- 标记死亡 ----
        for pid in killed_ids:
            victim = state.get_player(pid)
            if victim and victim.is_alive:
                victim.is_alive = False
                cause = "wolf_kill"
                if pid == state.witch_poison_target:
                    cause = "witch_poison"
                elif pid in chain:
                    cause = "lovers_chain"
                deaths.append({
                    "player_id": pid,
                    "seat_number": victim.seat_number,
                    "cause": cause,
                })

        # ---- 记录结果 ----
        state.night_results.append(NightResult(deaths=deaths))

        if deaths:
            seats = "、".join(f"{d['seat_number']}号" for d in deaths)
            runtime.timeline.append({"type": "death", "text": f"昨夜{seats}出局。"})
        else:
            runtime.timeline.append({"type": "death", "text": "昨夜是平安夜。"})

        # 清理夜晚状态
        state.wolf_kill_target = None
        state.witch_poison_target = None
        state.witch_save_target = None
        state.guard_target = None
        state.seer_check_target = None
        state.seer_check_result = None
        state.nightmare_block_target = None
        state.dream_weaver_target = None
        state.magician_swap_a = None
        state.magician_swap_b = None

        # 魔术师交换延迟解析
        self._resolve_magician_swap(state)

    def _resolve_magician_swap(self, state: GameState) -> None:
        """结算魔术师交换效果（在所有夜晚行动结束后）"""
        if not state.magician_swap_a or not state.magician_swap_b:
            return
        a = state.get_player(state.magician_swap_a)
        b = state.get_player(state.magician_swap_b)
        if not a or not b:
            return
        # 交换座位号
        a.seat_number, b.seat_number = b.seat_number, a.seat_number
        a.swapped_by_magician = False
        b.swapped_by_magician = False

    # ================================================================
    # 白天流程实现
    # ================================================================

    async def _run_day(self, runtime: GameRuntime) -> None:
        """执行完整白天流程"""
        state = runtime.state

        # 检查游戏是否已经结束
        winner = WinChecker.check(state)
        if winner:
            state.winner = winner
            state.phase = GamePhase.GAME_OVER
            runtime.timeline.append({"type": "game_over", "text": f"{self._winner_label(winner)}获胜。"})
            return

        # 1. 宣布死讯
        state.phase = GamePhase.DAY_DEATH_ANNOUNCE
        if state.night_results:
            last = state.night_results[-1]
            if last.deaths:
                dead_seats = [d["seat_number"] for d in last.deaths]
                runtime.timeline.append({
                    "type": "system",
                    "text": f"天亮了。昨夜{'、'.join(f'{s}号' for s in dead_seats)}倒牌。",
                })
            else:
                runtime.timeline.append({"type": "system", "text": "天亮了。昨晚是平安夜。"})

        # 2. 警长竞选（首日且有警徽的局）
        if not runtime.police_elected and runtime.board.has_police:
            await self._run_police_election(runtime)
            runtime.police_elected = True

        # 3. 发言阶段（前端通过 run_ai_speeches / submit_human_speech 驱动）
        state.phase = GamePhase.DAY_DISCUSS
        # 不继续推进到投票阶段 — 前端在发言完毕后通过 resolve_votes 推进

    async def _run_police_election(self, runtime: GameRuntime) -> None:
        """警长竞选流程"""
        state = runtime.state
        state.phase = GamePhase.POLICE_REGISTER

        alive = state.get_alive_players()
        # 随机选择3-4名候选人（模拟自愿上警）
        k = min(random.randint(3, 4), len(alive))
        candidates = random.sample(alive, k=k)
        state.police_candidates = [p.id for p in candidates]

        candidate_seats = [p.seat_number for p in candidates]
        runtime.timeline.append({
            "type": "police",
            "text": f"警长竞选开始，上警玩家：{'、'.join(f'{s}号' for s in candidate_seats)}。",
        })

        # 候选人发言
        state.phase = GamePhase.POLICE_SPEECH
        for candidate in candidates:
            if candidate.is_human:
                continue
            agent = runtime.agents.get(candidate.id)
            if not agent:
                continue
            visible = self._visible_state(runtime, candidate.id)
            text = await agent.generate_speech(visible, runtime.provider_config, runtime.llm)
            speech_record = SpeechRecord(
                player_id=candidate.id, text=text,
                phase=state.phase, day_number=state.day_number,
            )
            state.speech_history.append(speech_record)
            runtime.timeline.append({
                "type": "speech",
                "text": f"警上{candidate.seat_number}号：{text}",
                "player_id": candidate.id,
            })

        # 投票
        state.phase = GamePhase.POLICE_VOTE
        records: list[VoteRecord] = []
        for player in alive:
            if player.id in [c.id for c in candidates]:
                continue  # 候选人不能投票给自己以外的人
            target = random.choice(candidates)
            records.append(VoteRecord(voter_id=player.id, target_id=target.id))

        # 计票
        totals: dict[str, int] = {}
        for r in records:
            totals[r.target_id] = totals.get(r.target_id, 0) + 1

        if totals:
            sheriff_id = max(totals, key=totals.get)
            sheriff = state.get_player(sheriff_id)
            if sheriff:
                sheriff.is_sheriff = True
                state.sheriff_id = sheriff_id
                runtime.timeline.append({
                    "type": "police",
                    "text": f"{sheriff.seat_number}号获得警徽，当选警长。",
                })

        state.phase = GamePhase.POLICE_RESULT
        state.police_vote_records = records

    def _process_vote_result(self, runtime: GameRuntime, records: list[VoteRecord]) -> None:
        """处理投票结果"""
        state = runtime.state

        # 计票（含警长1.5票和乌鸦诅咒+1票）
        totals: dict[str, float] = {}
        for r in records:
            weight = 1.0
            if r.is_sheriff_vote:
                weight = 1.5
            if r.is_cursed_vote:
                weight += 1.0
            totals[r.target_id] = totals.get(r.target_id, 0) + weight

        if not totals:
            return

        top_score = max(totals.values())
        top_targets = [pid for pid, score in totals.items() if score == top_score]

        vote_line = "，".join(
            f"{state.get_player(pid).seat_number}号{score:g}票"
            for pid, score in sorted(totals.items(), key=lambda x: -x[1])
        )
        runtime.timeline.append({"type": "vote", "text": f"投票结果：{vote_line}。"})

        # 平票处理
        if len(top_targets) > 1:
            state.phase = GamePhase.DAY_PK
            pk_seats = [
                state.get_player(pid).seat_number
                for pid in top_targets if state.get_player(pid)
            ]
            runtime.timeline.append({
                "type": "vote",
                "text": f"平票PK：{'、'.join(f'{s}号' for s in pk_seats)}，无人出局，进入黑夜。",
            })
            state.day_number += 1
            state.phase = GamePhase.NIGHT_START
            return

        # 放逐
        exiled = state.get_player(top_targets[0])
        if not exiled:
            return

        # 白痴检查
        if exiled.role == Role.IDIOT and not exiled.is_revealed_idiot:
            exiled.is_revealed_idiot = True
            runtime.timeline.append({
                "type": "system",
                "text": f"{exiled.seat_number}号是白痴，翻牌免于放逐，但失去投票权。",
            })
            state.phase = GamePhase.NIGHT_START
            state.day_number += 1
            return

        exiled.is_alive = False
        state.day_deaths.append({
            "player_id": exiled.id,
            "seat_number": exiled.seat_number,
            "cause": "vote",
        })
        runtime.timeline.append({
            "type": "death",
            "text": f"{exiled.seat_number}号被放逐出局。",
        })

        # 警徽流转
        if exiled.is_sheriff:
            self._pass_sheriff_badge(state, runtime)

        # 死亡链
        extra = WinChecker.get_death_chain(state, {exiled.id}, "vote")
        for pid in extra:
            p = state.get_player(pid)
            if p and p.is_alive:
                p.is_alive = False
                runtime.timeline.append({
                    "type": "death", "text": f"{p.seat_number}号殉情出局。",
                })

        # 检查游戏结束
        winner = WinChecker.check(state)
        if winner:
            state.winner = winner
            state.phase = GamePhase.GAME_OVER
            runtime.timeline.append({"type": "game_over", "text": f"{self._winner_label(winner)}获胜。"})
        else:
            state.day_number += 1
            state.phase = GamePhase.NIGHT_START
            state.wolf_kill_target = None
            state.seer_check_target = None
            state.seer_check_result = None
            for p in state.players:
                p.has_voted = False
                p.has_spoken = False
            runtime.timeline.append({"type": "phase", "text": f"进入第{state.day_number}夜。"})

    def _pass_sheriff_badge(self, state: GameState, runtime: GameRuntime) -> None:
        """警徽流转"""
        alive = state.get_alive_players()
        if not alive:
            return
        new_sheriff = random.choice(alive)
        new_sheriff.is_sheriff = True
        state.sheriff_id = new_sheriff.id
        state.sheriff_badge_flow.append(new_sheriff.id)
        runtime.timeline.append({
            "type": "police",
            "text": f"警徽流转：{new_sheriff.seat_number}号接任警长。",
        })

    # ================================================================
    # 内部辅助方法
    # ================================================================

    def _get_runtime(self, game_id: str) -> GameRuntime:
        try:
            return self._games[game_id]
        except KeyError as exc:
            raise ValueError("游戏不存在") from exc

    def _check_game_over(self, runtime: GameRuntime) -> dict[str, Any]:
        state = runtime.state
        winner = WinChecker.check(state)
        if winner:
            state.winner = winner
            state.phase = GamePhase.GAME_OVER
            runtime.timeline.append({"type": "game_over", "text": f"{self._winner_label(winner)}获胜。"})
        return self.get_game(state.game_id)

    def _record_human_vote(self, state: GameState, human: Player, target: Player) -> None:
        state.vote_records.append(VoteRecord(
            voter_id=human.id, target_id=target.id,
            is_sheriff_vote=human.is_sheriff,
        ))
        human.has_voted = True

    def _kill_player(self, state: GameState, player: Player, cause: str) -> None:
        player.is_alive = False
        state.day_deaths.append({
            "player_id": player.id,
            "seat_number": player.seat_number,
            "cause": cause,
        })

    def _create_agents(self, state: GameState, difficulty: str) -> dict[str, AIAgentSession]:
        wolves = [p for p in state.players if p.faction == Faction.WOLF]
        regular_wolf_ids = {
            p.id for p in wolves
            if p.role not in {Role.MECHANICAL_WOLF, Role.GARGOYLE, Role.HIDDEN_WOLF}
        }
        agents: dict[str, AIAgentSession] = {}
        for player in state.players:
            if player.is_human or not player.role or not player.faction:
                continue
            teammate_seats: list[int] = []
            if player.id in regular_wolf_ids:
                teammate_seats = [
                    p.seat_number for p in wolves
                    if p.id != player.id and p.id in regular_wolf_ids
                ]
            agents[player.id] = AIAgentSession(
                player_id=player.id,
                seat_number=player.seat_number,
                role=player.role,
                faction=player.faction,
                difficulty=difficulty,
                known_teammate_seats=teammate_seats,
            )
        return agents

    @staticmethod
    def _has_role_alive(state: GameState, role: Role) -> bool:
        return any(p.is_alive and p.role == role for p in state.players)

    def _visible_state(self, runtime: GameRuntime, player_id: str) -> dict[str, Any]:
        state = runtime.state
        player = state.get_player(player_id)
        if not player:
            raise ValueError("玩家不存在")
        last_deaths = []
        if state.night_results:
            last_deaths = [d["seat_number"] for d in state.night_results[-1].deaths]
        public_speeches = [
            self._speech_to_dict(runtime, r)
            for r in state.speech_history[-24:]
        ]
        own_role = get_role_display_name(player.role) if player.role else "未知"
        return {
            "game_id": state.game_id,
            "board": {"id": runtime.board.id, "name": runtime.board.name, "has_police": runtime.board.has_police},
            "difficulty": state.difficulty,
            "phase": state.phase.value,
            "phase_label": PHASE_LABELS.get(state.phase, state.phase.value),
            "day_number": state.day_number,
            "self": {
                "seat_number": player.seat_number,
                "role": own_role,
                "faction": player.faction.value if player.faction else None,
                "is_sheriff": player.is_sheriff,
            },
            "alive_players": [p.to_public_dict() for p in state.get_alive_players()],
            "sheriff_seat": self._seat_for_id(state, state.sheriff_id),
            "last_deaths": last_deaths,
            "public_speeches": public_speeches,
            "vote_records": [
                self._vote_to_dict(state, r) for r in state.vote_records[-24:]
            ],
        }

    def _runtime_to_dict(self, runtime: GameRuntime) -> dict[str, Any]:
        state = runtime.state
        human = state.get_human_player()
        role_result = None
        if human and state.seer_check_target:
            target = state.get_player(state.seer_check_target)
            if target:
                role_result = {
                    "target_seat": target.seat_number,
                    "result": "good" if state.seer_check_result else "wolf",
                    "role": get_role_display_name(target.role)
                    if human.role == Role.PSYCHIC and target.role else None,
                }
        return {
            "game": state.to_dict(),
            "board": self._board_to_dict(runtime.board),
            "phase_label": PHASE_LABELS.get(state.phase, state.phase.value),
            "human": human.to_role_dict() if human else None,
            "players": [self._player_to_dict_for_human(p, human) for p in state.players],
            "timeline": runtime.timeline[-80:],
            "speeches": [
                self._speech_to_dict(runtime, r) for r in state.speech_history[-80:]
            ],
            "votes": [
                self._vote_to_dict(state, r) for r in state.vote_records
            ],
            "last_check": role_result,
            "agents": [a.describe_publicly() for a in runtime.agents.values()],
            "provider": runtime.provider_config.masked(),
            "pending_human_prompt": runtime.pending_human_prompt,
            "pending_human_action_type": runtime.pending_human_action_type,
        }

    def _player_to_dict_for_human(self, player: Player, human: Player | None) -> dict[str, Any]:
        data = player.to_public_dict()
        if human and player.id == human.id:
            data["role"] = player.role.value if player.role else None
            data["role_name"] = player.display_role
            data["faction"] = player.faction.value if player.faction else None
        return data

    def _board_to_dict(self, board: BoardConfig) -> dict[str, Any]:
        role_counts: dict[str, int] = {}
        roles = []
        for slot in board.slots:
            role = Role(slot.candidates[0])
            display = get_role_display_name(role)
            role_counts[display] = role_counts.get(display, 0) + 1
            roles.append({"role": role.value, "name": display, "pool": slot.pool})
        return {
            "id": board.id,
            "name": board.name,
            "description": board.description,
            "player_count": board.player_count,
            "has_police": board.has_police,
            "difficulty": board.difficulty,
            "roles": roles,
            "role_counts": role_counts,
            "night_order": board.night_order,
            "special_rules": board.special_rules,
        }

    def _speech_to_dict(self, runtime: GameRuntime, record: SpeechRecord) -> dict[str, Any]:
        player = runtime.state.get_player(record.player_id)
        return {
            "player_id": record.player_id,
            "seat_number": player.seat_number if player else None,
            "name": player.name if player else "未知",
            "text": record.text,
            "phase": record.phase.value,
            "day_number": record.day_number,
            "timestamp": record.timestamp,
            "typing_cps": self._typing_cps(runtime.state.difficulty, record.text),
        }

    @staticmethod
    def _typing_cps(difficulty: str, text: str) -> float:
        base = {"novice": 3.2, "basic": 3.8, "advanced": 4.4, "expert": 4.8}.get(difficulty, 3.8)
        jitter = random.uniform(-0.35, 0.45)
        if len(text) > 160:
            jitter += 0.25
        return round(max(2.4, base + jitter), 2)

    @staticmethod
    def _vote_to_dict(state: GameState, record: VoteRecord) -> dict[str, Any]:
        voter = state.get_player(record.voter_id)
        target = state.get_player(record.target_id)
        return {
            "voter_seat": voter.seat_number if voter else None,
            "target_seat": target.seat_number if target else None,
            "weight": 1.5 if record.is_sheriff_vote else 1,
        }

    @staticmethod
    def _roles_for_board(board: BoardConfig) -> list[Role]:
        return [Role(slot.candidates[0]) for slot in board.slots]

    @staticmethod
    def _choose_human_role(roles: list[Role], human_role: str | None) -> Role:
        if human_role and human_role != "random":
            desired = Role(human_role)
            if desired in roles:
                return desired
        if Role.SEER in roles:
            return Role.SEER
        if Role.PSYCHIC in roles:
            return Role.PSYCHIC
        return random.choice(roles)

    @staticmethod
    def _new_player(seat: int, name: str, role: Role, is_human: bool) -> Player:
        config = ROLE_CONFIG[role]
        return Player(
            id=f"player_{seat}",
            seat_number=seat,
            name=name,
            is_human=is_human,
            role=role,
            faction=config["faction"],
        )

    @staticmethod
    def _most_common(values: list[str]) -> str | None:
        if not values:
            return None
        return max(set(values), key=values.count)

    @staticmethod
    def _seat_for_id(state: GameState, player_id: str | None) -> int | None:
        if not player_id:
            return None
        player = state.get_player(player_id)
        return player.seat_number if player else None

    def _pressure_seats(self, runtime: GameRuntime) -> list[int]:
        speeches = runtime.state.speech_history[-12:]
        seats: list[int] = []
        for record in speeches:
            for player in runtime.state.get_alive_players():
                marker = f"{player.seat_number}号"
                if marker in record.text:
                    seats.append(player.seat_number)
        return seats[-4:]

    @staticmethod
    def _winner_label(winner: str) -> str:
        return {
            "good": "好人阵营",
            "wolf": "狼人阵营",
            "third": "第三方阵营",
            "cursed_fox": "咒狐",
        }.get(winner, winner)


game_service = GameService()
