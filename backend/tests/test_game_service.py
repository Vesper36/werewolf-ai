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
    mech = next(agent for agent in agents if agent["seat_number"] == 12)
    assert mech["known_teammate_seats"] == []


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
    after_night = await game_service.resolve_night(game_id, 2)
    assert after_night["game"]["phase"] in {"day_discuss", "game_over"}
    if after_night["game"]["phase"] == "game_over":
        return
    after_speech = await game_service.run_ai_speeches(game_id)
    assert len(after_speech["speeches"]) > 0
    alive_targets = [p["seat_number"] for p in after_speech["players"] if p["is_alive"] and not p["is_human"]]
    after_vote = game_service.resolve_vote(game_id, alive_targets[0])
    assert after_vote["game"]["phase"] in {"night_start", "game_over"}
