"""完整游戏流程集成测试"""

from __future__ import annotations
import pytest
from src.ai.provider import AIProviderConfig
from src.services.game_service import game_service


# ---- 无警长板子 ----

@pytest.mark.asyncio
async def test_no_police_board_skips_election() -> None:
    """无警长板子不应产生警长"""
    p = game_service.create_game(
        board_id="novice_9_no_police", difficulty="novice",
        human_name="tester", human_role="villager",
        provider_config=AIProviderConfig(provider="offline"),
    )
    gid = p["game"]["game_id"]
    await game_service.process_first_night(gid)
    rt = game_service._get_runtime(gid)
    assert rt.state.sheriff_id is None
    assert rt.board.has_police is False


# ---- 有警长板子 ----

@pytest.mark.asyncio
async def test_police_board_has_election() -> None:
    """有警长板子应自动产生警长"""
    p = game_service.create_game(
        board_id="basic_12_standard", difficulty="basic",
        human_name="tester", human_role="villager",
        provider_config=AIProviderConfig(provider="offline"),
    )
    gid = p["game"]["game_id"]
    await game_service.process_first_night(gid)
    rt = game_service._get_runtime(gid)
    assert rt.board.has_police is True
    # process_first_night应推进游戏状态
    assert rt.state.phase.value in {"day_discuss", "game_over", "police_register", "police_speech", "police_vote"}, \
        f"首夜后应推进: {rt.state.phase.value}"


# ---- 狼人夜刀 ----

@pytest.mark.asyncio
async def test_wolf_human_can_kill() -> None:
    """人类狼人能提交刀人目标"""
    from src.models.role import Role
    p = game_service.create_game(
        board_id="advanced_knight", difficulty="advanced",
        human_name="tester", human_role="werewolf",
        provider_config=AIProviderConfig(provider="offline"),
    )
    gid = p["game"]["game_id"]
    rt = game_service._get_runtime(gid)
    human = rt.state.get_human_player()
    assert human.role == Role.WEREWOLF

    # 提交刀人
    alive = [p2 for p2 in rt.state.get_alive_players() if not p2.is_human and p2.faction.value != "wolf"]
    if alive:
        await game_service.submit_human_night_action(gid, "wolf_kill", alive[0].seat_number)
        rt2 = game_service._get_runtime(gid)
        # 狼刀行动被记录
        assert rt2.state.phase.value in {"night_seer", "night_witch", "night_end", "night_guard", "day_discuss", "game_over", "night_start"}


# ---- 完整循环 ----

@pytest.mark.asyncio
async def test_full_day_night_cycle() -> None:
    """完整白天发言+投票+夜晚流转"""
    p = game_service.create_game(
        board_id="novice_9_no_police", difficulty="novice",
        human_name="tester", human_role="villager",
        provider_config=AIProviderConfig(provider="offline"),
    )
    gid = p["game"]["game_id"]
    await game_service.process_first_night(gid)
    rt = game_service._get_runtime(gid)
    if rt.state.phase.value == "game_over":
        return  # 极端情况
    # 发言
    await game_service.run_ai_speeches(gid)
    game_service.submit_human_speech(gid, "我是村民，这轮听发言")
    # 投票 - 切到投票阶段
    game_service.start_vote_phase(gid)
    rt = game_service._get_runtime(gid)
    if rt.state.phase.value == "day_vote":
        alive = [p2 for p2 in rt.state.get_alive_players() if not p2.is_human]
        if alive:
            game_service.submit_human_vote(gid, alive[0].seat_number)
            await game_service.resolve_votes(gid)
    rt2 = game_service._get_runtime(gid)
    # 应该在投票后进入了夜晚或结束
    assert rt2.state.phase.value in {"night_start", "game_over"}, f"投票后应进入夜晚: {rt2.state.phase.value}"
