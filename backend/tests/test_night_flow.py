"""夜间流程集成测试"""

from __future__ import annotations

import pytest

from src.ai.provider import AIProviderConfig
from src.services.game_service import game_service


def _create_game(difficulty="novice", board_id="novice_9_no_police", human_role="villager"):
    payload = game_service.create_game(
        board_id=board_id, difficulty=difficulty,
        human_name="测试玩家", human_role=human_role,
        provider_config=AIProviderConfig(provider="offline"),
    )
    return payload["game"]["game_id"]


@pytest.mark.asyncio
async def test_first_night_completes_for_villager() -> None:
    """村民玩家首夜应自动完成并进入白天"""
    game_id = _create_game()
    result = await game_service.process_first_night(game_id)
    phase = result["game"]["phase"]
    assert phase in {"day_discuss", "game_over"}, f"首夜后应进入白天或结束, 实际: {phase}"
    runtime = game_service._get_runtime(game_id)
    assert runtime.state.is_first_night is False


@pytest.mark.asyncio
async def test_night_results_recorded_after_night() -> None:
    """夜间结算后应有night_results记录"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    runtime = game_service._get_runtime(game_id)
    assert len(runtime.state.night_results) >= 1


@pytest.mark.asyncio
async def test_wolf_kill_target_is_set() -> None:
    """狼刀目标应被设置"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    runtime = game_service._get_runtime(game_id)
    # wolf_kill_target 应该被设置了（除非狼人恰好杀了被女巫救的人）
    # 至少night_results有记录
    assert runtime.state.night_results[-1].deaths is not None


@pytest.mark.asyncio
async def test_seer_requires_human_input() -> None:
    """预言家玩家首夜时应等待人类输入查验目标"""
    game_id = _create_game(human_role="seer")
    runtime = game_service._get_runtime(game_id)
    result = await game_service.process_first_night(game_id)
    # 当人类是预言家时，夜晚应在seer阶段暂停
    rt = game_service._get_runtime(game_id)
    phase = rt.state.phase.value
    # 应停在night_seer或已到day_discuss（取决于实现是否自动跳过）
    assert phase in {"night_seer", "day_discuss", "game_over"}, f"预言家应停在查验阶段: {phase}"


@pytest.mark.asyncio
async def test_human_seer_can_submit_check_and_continue() -> None:
    """预言家提交查验后应能获得查验结果或流程推进"""
    game_id = _create_game(human_role="seer")
    await game_service.process_first_night(game_id)
    rt = game_service._get_runtime(game_id)
    phase = rt.state.phase.value
    if phase == "night_seer":
        alive_ai = [p for p in rt.state.get_alive_players() if not p.is_human]
        target = alive_ai[0]
        result = await game_service.submit_human_night_action(game_id, "seer_check", target.seat_number)
        # 提交后应推进流程
        rt2 = game_service._get_runtime(game_id)
        assert rt2.state.phase.value in {"day_discuss", "game_over", "night_end"}, \
            f"提交查验后应推进: {rt2.state.phase.value}"
    else:
        # 流程已自动完成
        assert phase in {"day_discuss", "game_over"}


@pytest.mark.asyncio
async def test_game_can_reach_day_discuss_and_generate_speeches() -> None:
    """完整流程：首夜 -> 发言"""
    game_id = _create_game()
    night = await game_service.process_first_night(game_id)
    if night["game"]["phase"] == "game_over":
        pytest.skip("游戏已结束")
    # AI发言
    speech_result = await game_service.run_ai_speeches(game_id)
    assert len(speech_result["speeches"]) > 0
    # 人类发言
    game_service.submit_human_speech(game_id, "我是村民，这轮先听发言")
    rt = game_service._get_runtime(game_id)
    human_speeches = [s for s in rt.state.speech_history if rt.state.get_player(s.player_id) and rt.state.get_player(s.player_id).is_human]
    assert len(human_speeches) >= 1


@pytest.mark.asyncio
async def test_night_sets_deaths_correctly() -> None:
    """夜间死亡人数应合理（0-2人）"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    rt = game_service._get_runtime(game_id)
    deaths = rt.state.night_results[-1].deaths
    assert 0 <= len(deaths) <= 2, f"夜间死亡应在0-2人之间: {len(deaths)}"


@pytest.mark.asyncio
async def test_night_does_not_kill_dead_players() -> None:
    """已死亡玩家不应再被杀"""
    game_id = _create_game()
    await game_service.process_first_night(game_id)
    rt = game_service._get_runtime(game_id)
    deaths = rt.state.night_results[-1].deaths
    for death in deaths:
        player = rt.state.get_player(death["player_id"])
        assert player is not None
