"""游戏业务编排。

GameService 是裁判和房间管理器；AIAgentSession 是玩家视角。
任何 AI 调用只能拿 visible_state，不能拿完整 GameState。
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
from ..models.board import BoardConfig
from ..models.game import GamePhase, GameState, NightResult, SpeechRecord, VoteRecord
from ..models.player import Player
from ..models.role import Faction, ROLE_CONFIG, Role, get_role_display_name


PHASE_LABELS = {
    GamePhase.LOBBY: "大厅",
    GamePhase.ROLE_DEALT: "身份确认",
    GamePhase.NIGHT_START: "天黑请闭眼",
    GamePhase.POLICE_REGISTER: "警长竞选",
    GamePhase.POLICE_SPEECH: "警上发言",
    GamePhase.POLICE_VOTE: "警长投票",
    GamePhase.DAY_DEATH_ANNOUNCE: "宣布昨夜死讯",
    GamePhase.DAY_DISCUSS: "白天发言",
    GamePhase.DAY_VOTE: "放逐投票",
    GamePhase.DAY_PK: "平票 PK",
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


class GameService:
    def __init__(self) -> None:
        self._games: dict[str, GameRuntime] = {}

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
        )
        runtime = GameRuntime(state=state, board=board, provider_config=provider_config)
        runtime.agents = self._create_agents(state, difficulty)
        runtime.timeline.append(
            {
                "type": "system",
                "text": f"本局为{board.name}，{board.player_count}人，{'带上警' if board.has_police else '不上警'}。",
            }
        )
        runtime.timeline.append({"type": "system", "text": f"你的身份是{get_role_display_name(chosen_human_role)}。"})
        self._games[game_id] = runtime
        return self.get_game(game_id)

    def get_game(self, game_id: str) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        return self._runtime_to_dict(runtime)

    async def resolve_night(self, game_id: str, target_seat: int | None = None) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        if not human:
            raise ValueError("缺少人类玩家")
        if state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)

        state.phase = GamePhase.NIGHT_START
        alive = state.get_alive_players()
        wolf_targets: list[int] = []
        for player in alive:
            if player.is_human:
                continue
            agent = runtime.agents.get(player.id)
            if not agent:
                continue
            visible = self._visible_state(runtime, player.id)
            ai_target = agent.choose_night_target(visible)
            if ai_target and player.faction == Faction.WOLF:
                wolf_targets.append(ai_target)

        if human.faction == Faction.WOLF and target_seat:
            wolf_targets.append(target_seat)

        wolf_target = self._most_common(wolf_targets)
        if wolf_target:
            target = state.get_player_by_seat(wolf_target)
            if target:
                state.wolf_kill_target = target.id

        if human.role in {Role.SEER, Role.PSYCHIC} and target_seat:
            target = state.get_player_by_seat(target_seat)
            if target:
                state.seer_check_target = target.id
                state.seer_check_result = target.faction != Faction.WOLF
                role_info = get_role_display_name(target.role) if human.role == Role.PSYCHIC and target.role else ""
                result = "好人" if state.seer_check_result else "狼人"
                suffix = f"，具体身份：{role_info}" if role_info else ""
                runtime.timeline.append({"type": "private", "text": f"你查验了{target.seat_number}号：{result}{suffix}。"})

        deaths: list[dict[str, Any]] = []
        if state.wolf_kill_target:
            killed = state.get_player(state.wolf_kill_target)
            if killed and killed.is_alive:
                killed.is_alive = False
                deaths.append({"player_id": killed.id, "seat_number": killed.seat_number, "cause": "wolf_kill"})

        state.night_results.append(NightResult(deaths=deaths))
        if deaths:
            seats = "、".join(f"{death['seat_number']}号" for death in deaths)
            runtime.timeline.append({"type": "death", "text": f"昨夜{seats}出局。"})
        else:
            runtime.timeline.append({"type": "death", "text": "昨夜平安夜。"})

        winner = WinChecker.check(state)
        if winner:
            state.winner = winner
            state.phase = GamePhase.GAME_OVER
            runtime.timeline.append({"type": "game_over", "text": f"{self._winner_label(winner)}获胜。"})
            return self.get_game(game_id)

        if runtime.board.has_police and state.is_first_night:
            self._auto_police(runtime)
        state.phase = GamePhase.DAY_DISCUSS
        state.is_first_night = False
        return self.get_game(game_id)

    async def run_ai_speeches(self, game_id: str) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        state = runtime.state
        if state.phase == GamePhase.ROLE_DEALT:
            await self.resolve_night(game_id)
        if state.phase == GamePhase.NIGHT_START:
            await self.resolve_night(game_id)
        if state.phase == GamePhase.GAME_OVER:
            return self.get_game(game_id)

        ai_players = [p for p in state.get_alive_players() if not p.is_human]
        records: list[SpeechRecord] = []

        async def speak(player: Player) -> SpeechRecord | None:
            agent = runtime.agents.get(player.id)
            if not agent:
                return None
            visible = self._visible_state(runtime, player.id)
            text = await agent.generate_speech(visible, runtime.provider_config, runtime.llm)
            return SpeechRecord(player_id=player.id, text=text, phase=state.phase, day_number=state.day_number)

        generated = await asyncio.gather(*(speak(player) for player in ai_players))
        for record in generated:
            if record is None:
                continue
            state.speech_history.append(record)
            records.append(record)
            player = state.get_player(record.player_id)
            seat = player.seat_number if player else "?"
            runtime.timeline.append({"type": "speech", "text": f"{seat}号：{record.text}", "player_id": record.player_id})
        return {**self.get_game(game_id), "new_speeches": [self._speech_to_dict(runtime, record) for record in records]}

    def submit_human_speech(self, game_id: str, text: str) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        if not human:
            raise ValueError("缺少人类玩家")
        clean = " ".join(text.strip().split())[:600]
        if not clean:
            raise ValueError("发言不能为空")
        record = SpeechRecord(player_id=human.id, text=clean, phase=state.phase, day_number=state.day_number)
        state.speech_history.append(record)
        runtime.timeline.append({"type": "speech", "text": f"{human.seat_number}号：{clean}", "player_id": human.id})
        return self.get_game(game_id)

    def resolve_vote(self, game_id: str, target_seat: int) -> dict[str, Any]:
        runtime = self._get_runtime(game_id)
        state = runtime.state
        human = state.get_human_player()
        target = state.get_player_by_seat(target_seat)
        if not human or not target or not target.is_alive:
            raise ValueError("投票目标无效")

        records = [VoteRecord(voter_id=human.id, target_id=target.id, is_sheriff_vote=human.is_sheriff)]
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
                records.append(VoteRecord(voter_id=player.id, target_id=ai_target.id, is_sheriff_vote=player.is_sheriff))

        state.vote_records = records
        totals = self._vote_totals(records)
        top_score = max(totals.values())
        top_targets = [pid for pid, score in totals.items() if score == top_score]
        vote_line = "，".join(
            f"{state.get_player(pid).seat_number}号{score:g}票" for pid, score in sorted(totals.items(), key=lambda item: -item[1])
        )
        runtime.timeline.append({"type": "vote", "text": f"投票结果：{vote_line}。"})

        if len(top_targets) > 1:
            state.phase = GamePhase.DAY_PK
            runtime.pk_pending_seats = [state.get_player(pid).seat_number for pid in top_targets if state.get_player(pid)]
            runtime.timeline.append({"type": "vote", "text": f"平票 PK：{runtime.pk_pending_seats}，本轮无人出局，直接进入黑夜。"})
            state.day_number += 1
            state.phase = GamePhase.NIGHT_START
            return self.get_game(game_id)

        exiled = state.get_player(top_targets[0])
        if exiled:
            exiled.is_alive = False
            state.day_deaths.append({"player_id": exiled.id, "seat_number": exiled.seat_number, "cause": "vote"})
            runtime.timeline.append({"type": "death", "text": f"{exiled.seat_number}号被放逐，身份为{exiled.display_role}。"})

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
            runtime.timeline.append({"type": "phase", "text": f"进入第{state.day_number}夜。"})
        return self.get_game(game_id)

    async def test_provider(self, provider_config: AIProviderConfig) -> dict[str, Any]:
        if not provider_config.enabled:
            return {"ok": True, "mode": "offline", "message": "离线策略可用，不会调用外部模型。"}
        llm = LLMClient()
        text = await llm.chat(
            provider_config,
            [
                {"role": "system", "content": "你只需要回复“连接正常”。"},
                {"role": "user", "content": "测试连接。"},
            ],
            max_tokens=20,
        )
        return {"ok": True, "mode": provider_config.provider, "message": text[:80]}

    def _get_runtime(self, game_id: str) -> GameRuntime:
        try:
            return self._games[game_id]
        except KeyError as exc:
            raise ValueError("游戏不存在") from exc

    def _create_agents(self, state: GameState, difficulty: str) -> dict[str, AIAgentSession]:
        wolves = [p for p in state.players if p.faction == Faction.WOLF]
        regular_wolf_ids = {p.id for p in wolves if p.role not in {Role.MECHANICAL_WOLF, Role.GARGOYLE, Role.HIDDEN_WOLF}}
        agents: dict[str, AIAgentSession] = {}
        for player in state.players:
            if player.is_human or not player.role or not player.faction:
                continue
            teammate_seats: list[int] = []
            if player.id in regular_wolf_ids:
                teammate_seats = [p.seat_number for p in wolves if p.id != player.id and p.id in regular_wolf_ids]
            agents[player.id] = AIAgentSession(
                player_id=player.id,
                seat_number=player.seat_number,
                role=player.role,
                faction=player.faction,
                difficulty=difficulty,
                known_teammate_seats=teammate_seats,
            )
        return agents

    def _visible_state(self, runtime: GameRuntime, player_id: str) -> dict[str, Any]:
        state = runtime.state
        player = state.get_player(player_id)
        if not player:
            raise ValueError("玩家不存在")
        last_deaths = []
        if state.night_results:
            last_deaths = [death["seat_number"] for death in state.night_results[-1].deaths]
        public_speeches = [self._speech_to_dict(runtime, record) for record in state.speech_history[-24:]]
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
            "vote_records": [self._vote_to_dict(state, record) for record in state.vote_records[-24:]],
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
                    "role": get_role_display_name(target.role) if human.role == Role.PSYCHIC and target.role else None,
                }
        return {
            "game": state.to_dict(),
            "board": self._board_to_dict(runtime.board),
            "phase_label": PHASE_LABELS.get(state.phase, state.phase.value),
            "human": human.to_role_dict() if human else None,
            "players": [self._player_to_dict_for_human(player, human) for player in state.players],
            "timeline": runtime.timeline[-80:],
            "speeches": [self._speech_to_dict(runtime, record) for record in state.speech_history[-80:]],
            "votes": [self._vote_to_dict(state, record) for record in state.vote_records],
            "last_check": role_result,
            "agents": [agent.describe_publicly() for agent in runtime.agents.values()],
            "provider": runtime.provider_config.masked(),
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

    def _auto_police(self, runtime: GameRuntime) -> None:
        state = runtime.state
        alive = state.get_alive_players()
        candidates = random.sample(alive, k=min(4, len(alive)))
        state.police_candidates = [p.id for p in candidates]
        sheriff = random.choice(candidates)
        sheriff.is_sheriff = True
        state.sheriff_id = sheriff.id
        runtime.timeline.append(
            {
                "type": "police",
                "text": f"警长竞选完成：{sheriff.seat_number}号获得警徽。警上候选为{[p.seat_number for p in candidates]}。",
            }
        )

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
    def _most_common(values: list[int]) -> int | None:
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
    def _vote_totals(records: list[VoteRecord]) -> dict[str, float]:
        totals: dict[str, float] = {}
        for record in records:
            totals[record.target_id] = totals.get(record.target_id, 0) + (1.5 if record.is_sheriff_vote else 1)
        return totals

    @staticmethod
    def _winner_label(winner: str) -> str:
        return {
            "good": "好人阵营",
            "wolf": "狼人阵营",
            "third": "第三方阵营",
            "cursed_fox": "咒狐",
        }.get(winner, winner)


game_service = GameService()
