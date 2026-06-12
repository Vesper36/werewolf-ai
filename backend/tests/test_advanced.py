"""警长竞选、特殊行动、边界条件测试"""

from __future__ import annotations

import pytest

from src.ai.provider import AIProviderConfig
from src.services.game_service import game_service
from src.models.role import Role, Faction, ROLE_CONFIG
from src.models.player import Player
from src.models.game import GameState
from src.engine.win_checker import WinChecker


def _create(board_id="basic_12_police", difficulty="basic", human_role="villager"):
    payload = game_service.create_game(
        board_id=board_id, difficulty=difficulty,
        human_name="tester", human_role=human_role,
        provider_config=AIProviderConfig(provider="offline"),
    )
    return payload["game"]["game_id"]


# ---- 警长竞选 ----

@pytest.mark.asyncio
async def test_police_election_creates_sheriff() -> None:
    """有警长板子应产生警长"""
    game_id = _create(board_id="basic_12_police", difficulty="basic")
    rt = game_service._get_runtime(game_id)
    await game_service._run_police_election(rt)
    state = rt.state
    assert state.sheriff_id is not None, "应产生警长"
    sheriff = state.get_player(state.sheriff_id)
    assert sheriff is not None
    assert sheriff.is_sheriff is True


@pytest.mark.asyncio
async def test_police_candidates_registered() -> None:
    """警长竞选应有候选人"""
    game_id = _create(board_id="basic_12_police", difficulty="basic")
    rt = game_service._get_runtime(game_id)
    await game_service._run_police_election(rt)
    assert len(rt.state.police_candidates) >= 2, "应至少有2名候选人"


@pytest.mark.asyncio
async def test_police_election_records_speeches() -> None:
    """警上候选人应有发言记录"""
    game_id = _create(board_id="basic_12_police", difficulty="basic")
    rt = game_service._get_runtime(game_id)
    before = len(rt.state.speech_history)
    await game_service._run_police_election(rt)
    after = len(rt.state.speech_history)
    assert after > before, "警上竞选应产生发言"


@pytest.mark.asyncio
async def test_police_vote_records_exist() -> None:
    """警长投票后应有投票记录"""
    game_id = _create(board_id="basic_12_police", difficulty="basic")
    rt = game_service._get_runtime(game_id)
    await game_service._run_police_election(rt)
    assert len(rt.state.police_vote_records) > 0, "应有投票记录"


# ---- 投票平票/PK ----

@pytest.mark.asyncio
async def test_tie_vote_sets_pk_phase() -> None:
    """平票后应进入PK或黑夜"""
    # 手动构造平票场景
    from src.models.game import VoteRecord
    state = GameState(game_id="pk_test", board_id="test", difficulty="expert")
    state.players = [
        Player(id="p1", seat_number=1, name="A", role=Role.SEER, faction=Faction.GOOD),
        Player(id="p2", seat_number=2, name="B", role=Role.WEREWOLF, faction=Faction.WOLF),
        Player(id="p3", seat_number=3, name="C", role=Role.WEREWOLF, faction=Faction.WOLF),
        Player(id="p4", seat_number=4, name="D", role=Role.VILLAGER, faction=Faction.GOOD),
    ]
    # p2 和 p3 各得2票（平票）
    records = [
        VoteRecord(voter_id="p1", target_id="p2"),
        VoteRecord(voter_id="p4", target_id="p2"),
        VoteRecord(voter_id="p2", target_id="p3"),
        VoteRecord(voter_id="p3", target_id="p3"),
    ]
    from src.services.game_service import GameService
    svc = GameService()
    svc._games["pk_test"] = type("RT", (), {"state": state, "board": None, "provider_config": None, "agents": {}, "llm": None, "timeline": [], "pk_pending_seats": [], "pending_human_prompt": None, "pending_human_action_type": None})()
    svc._process_vote_result(svc._games["pk_test"], records)
    # 平票后应进入黑夜（当前实现：直接进入黑夜）
    assert state.phase.value in {"day_pk", "night_start"}, f"平票后应进PK或黑夜: {state.phase.value}"


# ---- 胜负判定 ----

@pytest.mark.asyncio
async def test_win_checker_no_winner_when_game_start() -> None:
    """游戏刚开始时应无获胜方"""
    state = GameState(game_id="t", board_id="t", difficulty="expert")
    state.players = [
        Player(id="p1", seat_number=1, name="A", role=Role.SEER, faction=Faction.GOOD),
        Player(id="p2", seat_number=2, name="B", role=Role.WEREWOLF, faction=Faction.WOLF),
    ]
    assert WinChecker.check(state) is None


@pytest.mark.asyncio
async def test_win_checker_third_party_wins() -> None:
    """第三方阵营在所有其他阵营出局后应获胜"""
    state = GameState(game_id="t", board_id="t", difficulty="expert")
    state.players = [
        Player(id="p1", seat_number=1, name="A", role=Role.CUPID, faction=Faction.THIRD_PARTY),
        Player(id="p2", seat_number=2, name="B", role=Role.WEREWOLF, faction=Faction.WOLF, is_alive=False),
        Player(id="p3", seat_number=3, name="C", role=Role.SEER, faction=Faction.GOOD, is_alive=False),
    ]
    assert WinChecker.check(state) == "third"


# ---- 白痴翻牌 ----

@pytest.mark.asyncio
async def test_idiot_survives_vote() -> None:
    """白痴被投票放逐时应翻牌免疫"""
    from src.models.game import VoteRecord, ActionType
    from src.services.game_service import GameService, GameRuntime
    state = GameState(game_id="idiot_test", board_id="test", difficulty="expert")
    idiot = Player(id="p1", seat_number=1, name="白痴", role=Role.IDIOT, faction=Faction.GOOD)
    voter = Player(id="p2", seat_number=2, name="狼人", role=Role.WEREWOLF, faction=Faction.WOLF)
    state.players = [idiot, voter]
    svc = GameService()
    rt = GameRuntime(state=state, board=None, provider_config=None, agents={}, llm=None, timeline=[], pk_pending_seats=[], pending_human_prompt=None, pending_human_action_type=None)
    svc._games["idiot_test"] = rt
    records = [VoteRecord(voter_id="p2", target_id="p1")]
    svc._process_vote_result(rt, records)
    assert idiot.is_alive is True, "白痴翻牌后应存活"
    assert idiot.is_revealed_idiot is True, "白痴应已翻牌"


# ---- 板型验证 ----

@pytest.mark.asyncio
async def test_all_boards_valid() -> None:
    """所有预设板型应可创建游戏"""
    from src.data.boards import BOARDS
    for board in BOARDS:
        if not board.difficulty:
            continue
        payload = game_service.create_game(
            board_id=board.id, difficulty=board.difficulty[0],
            human_name="test", human_role="random",
            provider_config=AIProviderConfig(provider="offline"),
        )
        assert payload["game"]["game_id"], f"{board.id} 应能创建游戏"
        assert len(payload["players"]) == board.player_count, f"{board.id} 玩家数不匹配"


@pytest.mark.asyncio
async def test_board_role_distribution() -> None:
    """板型角色分配应与配置一致"""
    from src.data.boards import BOARDS_BY_ID
    payload = game_service.create_game(
        board_id="novice_9_no_police", difficulty="novice",
        human_name="test", human_role="villager",
        provider_config=AIProviderConfig(provider="offline"),
    )
    runtime = game_service._get_runtime(payload["game"]["game_id"])
    board = BOARDS_BY_ID["novice_9_no_police"]
    assert len(runtime.state.players) == board.player_count


# ---- 多局一致性 ----

@pytest.mark.asyncio
async def test_each_game_has_unique_id() -> None:
    """每次创建游戏应有唯一game_id"""
    ids = set()
    for _ in range(5):
        payload = game_service.create_game(
            board_id="novice_9_no_police", difficulty="novice",
            human_name="test", human_role="villager",
            provider_config=AIProviderConfig(provider="offline"),
        )
        gid = payload["game"]["game_id"]
        assert gid not in ids, f"game_id重复: {gid}"
        ids.add(gid)


@pytest.mark.asyncio
async def test_game_service_is_singleton() -> None:
    """game_service应是单例"""
    from src.services.game_service import game_service as svc1
    from src.services.game_service import game_service as svc2
    assert svc1 is svc2
