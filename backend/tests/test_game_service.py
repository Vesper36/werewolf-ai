from __future__ import annotations

import pytest

from src.ai.provider import AIProviderConfig
from src.services.game_service import game_service


@pytest.mark.asyncio
async def test_expert_board_creates_isolated_agents() -> None:
    payload = game_service.create_game(
        board_id="expert_mech_psychic",
        difficulty="expert",
        human_name="tester",
        human_role="psychic",
        provider_config=AIProviderConfig(provider="offline"),
    )
    agents = payload["agents"]
    assert len(agents) == 11
    assert len({agent["thread_id"] for agent in agents}) == 11
    # 所有狼人(非机械狼)应有已知队友，机械狼队友应为空
    game_id = payload["game"]["game_id"]
    runtime = game_service._get_runtime(game_id)
    mech_agent = None
    for agent in agents:
        player = runtime.state.get_player(agent["player_id"])
        if player and player.role and player.role.value == "mechanical_wolf":
            mech_agent = agent
            break
    assert mech_agent is not None, "应存在机械狼玩家"
    assert mech_agent["known_teammate_seats"] == [], "机械狼不应知道狼队友"


@pytest.mark.asyncio
async def test_offline_game_loop_generates_speeches_and_vote() -> None:
    payload = game_service.create_game(
        board_id="novice_9_no_police",
        difficulty="novice",
        human_name="tester",
        human_role="seer",
        provider_config=AIProviderConfig(provider="offline"),
    )
    game_id = payload["game"]["game_id"]
    # 使用新的首夜流程
    after_night = await game_service.process_first_night(game_id)
    phase = after_night["game"]["phase"]
    assert phase in {"day_discuss", "game_over"}, f"unexpected phase: {phase}"
    if after_night["game"]["phase"] == "game_over":
        return
    after_speech = await game_service.run_ai_speeches(game_id)
    assert len(after_speech["speeches"]) > 0
    alive_targets = [
        p["seat_number"] for p in after_speech["players"]
        if p["is_alive"] and not p["is_human"]
    ]
    # 人类投票
    game_service.submit_human_vote(game_id, alive_targets[0])
    after_vote = await game_service.resolve_votes(game_id)
    assert after_vote["game"]["phase"] in {"night_start", "game_over"}
