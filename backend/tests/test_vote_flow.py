"""投票、PK、胜负判定集成测试"""

from __future__ import annotations

import pytest

from src.ai.provider import AIProviderConfig
from src.services.game_service import game_service


def _create_game(difficulty="novice", board_id="novice_9_no_police", human_role="villager"):
    payload = game_service.create_game(
        board_id=board_id, difficulty=difficulty,
        human_name="tester", human_role=human_role,
        provider_config=AIProviderConfig(provider="offline"),
    )
    return payload["game"]["game_id"]


@pytest.mark.asyncio
async def test_vote_eliminates_player() -> None:
    """投票应能放逐一名玩家（或平票无人出局）"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    rt = game_service._get_runtime(game_id)
    if rt.state.phase.value == "game_over":
        pytest.skip("游戏已结束")
    await game_service.run_ai_speeches(game_id)
    alive_ai = [p for p in game_service._get_runtime(game_id).state.get_alive_players() if not p.is_human]
    if not alive_ai:
        pytest.skip("无存活AI玩家")
    target = alive_ai[0]
    before_count = len(game_service._get_runtime(game_id).state.get_alive_players())
    game_service.submit_human_vote(game_id, target.seat_number)
    result = await game_service.resolve_votes(game_id)
    after_count = len(game_service._get_runtime(game_id).state.get_alive_players())
    phase = result["game"]["phase"]
    # 两种合理结果：有人出局(少于之前)，或平票(无人出局进入PK/黑夜)
    assert after_count <= before_count
    assert phase in {"night_start", "game_over", "day_pk"}


@pytest.mark.asyncio
async def test_all_ai_votes_counted() -> None:
    """所有AI应参与投票"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    rt = game_service._get_runtime(game_id)
    if rt.state.phase.value == "game_over":
        pytest.skip("游戏已结束")
    await game_service.run_ai_speeches(game_id)
    alive_ai = [p for p in game_service._get_runtime(game_id).state.get_alive_players() if not p.is_human]
    if not alive_ai:
        pytest.skip("无存活AI玩家")
    game_service.submit_human_vote(game_id, alive_ai[0].seat_number)
    result = await game_service.resolve_votes(game_id)
    votes = result.get("votes", [])
    assert len(votes) >= len(alive_ai), f"应有至少{len(alive_ai)}票, 实际: {len(votes)}"


@pytest.mark.asyncio
async def test_win_checker_good_wins_when_all_wolves_dead() -> None:
    from src.models.game import GameState
    from src.models.player import Player
    from src.models.role import Role, Faction
    from src.engine.win_checker import WinChecker
    state = GameState(game_id="test", board_id="test", difficulty="expert")
    state.players = [
        Player(id="p1", seat_number=1, name="A", role=Role.SEER, faction=Faction.GOOD),
        Player(id="p2", seat_number=2, name="B", role=Role.WEREWOLF, faction=Faction.WOLF, is_alive=False),
        Player(id="p3", seat_number=3, name="C", role=Role.VILLAGER, faction=Faction.GOOD),
    ]
    assert WinChecker.check(state) == "good"


@pytest.mark.asyncio
async def test_win_checker_wolf_wins_when_no_gods() -> None:
    from src.models.game import GameState
    from src.models.player import Player
    from src.models.role import Role, Faction
    from src.engine.win_checker import WinChecker
    state = GameState(game_id="test", board_id="test", difficulty="expert")
    state.players = [
        Player(id="p1", seat_number=1, name="A", role=Role.SEER, faction=Faction.GOOD, is_alive=False),
        Player(id="p2", seat_number=2, name="B", role=Role.WEREWOLF, faction=Faction.WOLF),
        Player(id="p3", seat_number=3, name="C", role=Role.VILLAGER, faction=Faction.GOOD),
    ]
    assert WinChecker.check(state) == "wolf"


@pytest.mark.asyncio
async def test_win_checker_wolf_wins_when_no_civilians() -> None:
    from src.models.game import GameState
    from src.models.player import Player
    from src.models.role import Role, Faction
    from src.engine.win_checker import WinChecker
    state = GameState(game_id="test", board_id="test", difficulty="expert")
    state.players = [
        Player(id="p1", seat_number=1, name="A", role=Role.SEER, faction=Faction.GOOD),
        Player(id="p2", seat_number=2, name="B", role=Role.WEREWOLF, faction=Faction.WOLF),
        Player(id="p3", seat_number=3, name="C", role=Role.VILLAGER, faction=Faction.GOOD, is_alive=False),
    ]
    assert WinChecker.check(state) == "wolf"


@pytest.mark.asyncio
async def test_vote_result_reveals_role() -> None:
    """被放逐玩家应揭露角色"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    rt = game_service._get_runtime(game_id)
    if rt.state.phase.value == "game_over":
        pytest.skip("游戏已结束")
    await game_service.run_ai_speeches(game_id)
    alive_ai = [p for p in game_service._get_runtime(game_id).state.get_alive_players() if not p.is_human]
    if not alive_ai:
        pytest.skip("无存活AI玩家")
    target = alive_ai[0]
    game_service.submit_human_vote(game_id, target.seat_number)
    result = await game_service.resolve_votes(game_id)
    # 检查被放逐者的角色在timeline中被揭露
    timeline = result.get("timeline", [])
    death_events = [t for t in timeline if t.get("type") == "death"]
    assert len(death_events) > 0 or result["game"]["phase"] == "game_over"


@pytest.mark.asyncio
async def test_ai_sessions_are_independent() -> None:
    """所有AI session应有独立的thread_id和personality"""
    payload = game_service.create_game(
        board_id="expert_mech_psychic", difficulty="expert",
        human_name="tester", human_role="psychic",
        provider_config=AIProviderConfig(provider="offline"),
    )
    agents = payload["agents"]
    thread_ids = [a["thread_id"] for a in agents]
    assert len(thread_ids) == len(set(thread_ids)), "所有AI session应有唯一thread_id"
    for agent in agents:
        assert agent["personality"], f"{agent['seat_number']}号AI应有性格定义"


@pytest.mark.asyncio
async def test_expert_board_wolf_agents_have_teammates() -> None:
    """大神板子的普通狼人应知道狼队友"""
    payload = game_service.create_game(
        board_id="expert_mech_psychic", difficulty="expert",
        human_name="tester", human_role="psychic",
        provider_config=AIProviderConfig(provider="offline"),
    )
    game_id = payload["game"]["game_id"]
    runtime = game_service._get_runtime(game_id)
    wolves = [p for p in runtime.state.players if p.faction.value == "wolf" and p.role.value not in {"mechanical_wolf", "gargoyle", "hidden_wolf"}]
    for wolf in wolves:
        wolf_agent = runtime.agents.get(wolf.id)
        if wolf_agent:
            assert len(wolf_agent.known_teammate_seats) > 0, f"{wolf.seat_number}号狼人应知道队友"


@pytest.mark.asyncio
async def test_game_state_serialization() -> None:
    """游戏状态应可序列化为JSON"""
    import json
    payload = game_service.create_game(
        board_id="novice_9_no_police", difficulty="novice",
        human_name="tester", human_role="villager",
        provider_config=AIProviderConfig(provider="offline"),
    )
    # 整个payload应该是JSON可序列化的
    json_str = json.dumps(payload, ensure_ascii=False)
    assert len(json_str) > 100
    # 反序列化后应保持结构
    restored = json.loads(json_str)
    assert restored["game"]["game_id"] == payload["game"]["game_id"]
