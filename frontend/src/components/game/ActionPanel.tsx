"use client";

import { useState } from "react";
import { Bot, Moon, Send, Vote, Skull, Shield, ArrowRight } from "lucide-react";
import type { GameResponse } from "@/types/game";

type Props = {
  game: GameResponse;
  loading: boolean;
  onStartNight: () => void;
  onSubmitNightAction: (actionType: string, targetSeat: number | null) => void;
  onStartDay: () => void;
  onStartVote: () => void;
  onContinueDay: () => void;
  onTriggerAI: () => void;
  onSubmitSpeech: (text: string) => void;
  onSubmitVote: (targetSeat: number) => void;
  onResolveVotes: () => void;
  onSelfExplode: (targetSeat: number | null) => void;
  onHunterShoot: (targetSeat: number) => void;
  onKnightDuel: (targetSeat: number) => void;
};

export default function ActionPanel({
  game,
  loading,
  onStartNight,
  onSubmitNightAction,
  onStartDay,
  onStartVote,
  onTriggerAI,
  onSubmitSpeech,
  onSubmitVote,
  onResolveVotes,
  onSelfExplode,
  onHunterShoot,
  onKnightDuel,
}: Props) {
  const [speechInput, setSpeechInput] = useState("");
  const [selectedTarget, setSelectedTarget] = useState<number | null>(null);

  const { phase, is_first_night } = game.game;
  const isGameOver = phase === "game_over";
  const alivePlayers = game.players.filter((p) => p.is_alive && !p.is_human);
  const humanRole = game.human?.role ?? "";
  const humanFaction = game.human?.faction ?? "";
  const prompt = game.pending_human_prompt;
  const promptAction = game.pending_human_action_type;

  const handleSpeechSubmit = () => {
    if (!speechInput.trim()) return;
    onSubmitSpeech(speechInput);
    setSpeechInput("");
  };

  if (isGameOver) {
    const winnerMap: Record<string, string> = {
      good: "好人阵营", wolf: "狼人阵营",
      third: "第三方阵营", cursed_fox: "咒狐",
    };
    return (
      <div className="bg-gray-800/80 rounded-2xl p-6 border border-gray-700 text-center">
        <h3 className="text-2xl font-bold text-amber-400 mb-2">游戏结束</h3>
        <p className="text-lg text-gray-200">{winnerMap[game.game.winner ?? ""] ?? game.game.winner} 获胜</p>
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {game.players.map((p) => (
            <span key={p.id} className={`px-3 py-1 rounded-full text-sm ${p.is_human ? "bg-blue-600 text-white" : p.faction === "wolf" ? "bg-red-900/50 text-red-300 border border-red-700" : "bg-gray-700 text-gray-300"}`}>
              {p.seat_number}号 {p.name}: {p.role_name ?? p.role ?? "?"}
            </span>
          ))}
        </div>
      </div>
    );
  }

  // ---- Role dealt / start game ----
  if (phase === "role_dealt") {
    return (
      <div className="bg-gray-800/80 rounded-2xl p-6 border border-gray-700 text-center">
        <Shield size={32} className="text-amber-400 mx-auto mb-3" />
        <p className="text-gray-300 text-lg">身份已确认</p>
        <p className="text-gray-500 text-sm mt-1">
          {game.human?.role_name ?? game.human?.role} -- {humanFaction === "wolf" ? "狼人阵营" : "好人阵营"}
        </p>
        <button onClick={onStartNight} disabled={loading}
          className="mt-4 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 text-white rounded-xl font-medium transition-colors flex items-center gap-2 mx-auto">
          <Moon size={18} />进入首夜
        </button>
      </div>
    );
  }

  // ---- Night phases ----
  if (phase.startsWith("night_")) {
    const isWolf = humanFaction === "wolf" && humanRole !== "gargoyle" && humanRole !== "hidden_wolf" && humanRole !== "mechanical_wolf";
    const isSeer = humanRole === "seer" || humanRole === "psychic";
    const isWitch = humanRole === "witch";
    const isGuard = humanRole === "guard";
    const isWitchSave = promptAction === "witch_save";
    const isWitchPoison = promptAction === "witch_poison";
    const needsTarget = isWolf || isSeer || isGuard || isWitchPoison;

    // Witch save: binary yes/no choice
    if (prompt && isWitchSave) {
      return (
        <div className="bg-gray-800/80 rounded-2xl p-5 border border-indigo-700">
          <div className="flex items-center gap-2 mb-4">
            <Moon size={20} className="text-indigo-400" />
            <h3 className="text-lg font-semibold text-gray-100">{prompt}</h3>
          </div>
          <div className="flex gap-3">
            <button onClick={() => { onSubmitNightAction("witch_save", null); }}
              disabled={loading}
              className="flex-1 py-3 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 text-white rounded-xl font-medium transition-colors">
              {loading ? "提交中..." : "使用解药"}
            </button>
            <button onClick={() => { onSubmitNightAction("witch_skip", null); }}
              disabled={loading}
              className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-xl font-medium transition-colors">
              不用
            </button>
          </div>
        </div>
      );
    }

    // Witch poison or other roles needing a target
    if (prompt && (needsTarget || isWitch)) {
      return (
        <div className="bg-gray-800/80 rounded-2xl p-5 border border-indigo-700">
          <div className="flex items-center gap-2 mb-4">
            <Moon size={20} className="text-indigo-400" />
            <h3 className="text-lg font-semibold text-gray-100">{prompt}</h3>
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {alivePlayers.map((p) => (
              <button key={p.id} onClick={() => setSelectedTarget(p.seat_number)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${selectedTarget === p.seat_number ? "bg-indigo-500 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"}`}>
                {p.seat_number}号 {p.name}
              </button>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={() => { onSubmitNightAction(promptAction ?? "wolf_kill", selectedTarget); setSelectedTarget(null); }}
              disabled={loading || selectedTarget === null}
              className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-colors">
              {loading ? "提交中..." : "确认"}
            </button>
            {isWitchPoison && (
              <button onClick={() => { onSubmitNightAction("witch_skip", null); }}
                disabled={loading}
                className="py-3 px-5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-xl font-medium transition-colors">
                不用
              </button>
            )}
          </div>
        </div>
      );
    }

    // Villager at night or no prompt - just show night screen
    return (
      <div className="bg-gray-800/80 rounded-2xl p-6 border border-gray-700 text-center">
        <Moon size={32} className="text-indigo-400 mx-auto mb-3" />
        <p className="text-gray-300 text-lg">天黑请闭眼</p>
        <p className="text-gray-500 text-sm mt-1">{prompt ?? "等待夜晚结算..."}</p>
        {phase === "night_end" && (
          <button onClick={onStartDay} disabled={loading}
            className="mt-4 px-6 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 text-white rounded-xl text-sm transition-colors flex items-center gap-2 mx-auto">
            <ArrowRight size={16} />进入白天
          </button>
        )}
      </div>
    );
  }

  // ---- Police election phases ----
  if (phase.startsWith("police_")) {
    return (
      <div className="bg-gray-800/80 rounded-2xl p-5 border border-amber-700 text-center">
        <Shield size={32} className="text-amber-400 mx-auto mb-3" />
        <p className="text-gray-300 text-lg">{game.phase_label}</p>
        <p className="text-gray-500 text-sm mt-1">{prompt ?? "警长竞选进行中..."}</p>
        {phase === "police_vote" && (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-2 justify-center">
              {game.players.filter((p) => p.is_alive && p.is_sheriff !== undefined).map((p) => (
                <button key={p.id} onClick={() => setSelectedTarget(p.seat_number)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${selectedTarget === p.seat_number ? "bg-amber-500 text-gray-900" : "bg-gray-700 text-gray-300 hover:bg-gray-600"}`}>
                  {p.seat_number}号 {p.name}
                </button>
              ))}
            </div>
            <button onClick={() => { onSubmitVote(selectedTarget ?? 0); setSelectedTarget(null); }}
              disabled={loading || selectedTarget === null}
              className="px-6 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 text-white rounded-xl text-sm transition-colors">
              投票
            </button>
          </div>
        )}
      </div>
    );
  }

  // ---- Day discuss / speech phase ----
  if (phase === "day_discuss" || phase === "day_speech") {
    return (
      <div className="bg-gray-800/80 rounded-2xl p-5 border border-gray-700">
        {prompt && (
          <p className="text-sm text-amber-400 mb-3 flex items-center gap-1"><ArrowRight size={14} />{prompt}</p>
        )}
        <div className="flex gap-3">
          <textarea value={speechInput} onChange={(e) => setSpeechInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSpeechSubmit(); } }}
            placeholder="输入你的发言..."
            maxLength={600} rows={3}
            className="flex-1 bg-gray-900 border border-gray-600 rounded-xl px-4 py-3 text-gray-100 text-sm resize-none focus:outline-none focus:border-blue-500 transition-colors" />
          <div className="flex flex-col gap-2">
            <button onClick={handleSpeechSubmit} disabled={loading || !speechInput.trim()}
              className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-colors flex items-center gap-2">
              <Send size={16} />发言
            </button>
            <button onClick={onTriggerAI} disabled={loading}
              className="px-5 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-gray-200 rounded-xl text-sm transition-colors flex items-center gap-2">
              <Bot size={16} />AI 发言
            </button>
            <button onClick={onStartVote} disabled={loading}
              className="px-5 py-3 bg-amber-700 hover:bg-amber-600 disabled:bg-gray-800 text-white rounded-xl text-sm transition-colors flex items-center gap-2">
              <Vote size={16} />进入投票
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ---- Vote phase ----
  if (phase === "day_vote" || phase === "day_pk") {
    return (
      <div className="bg-gray-800/80 rounded-2xl p-5 border border-amber-700">
        <div className="flex items-center gap-2 mb-4">
          <Vote size={20} className="text-amber-400" />
          <h3 className="text-lg font-semibold text-gray-100">{game.phase_label}</h3>
        </div>
        {prompt && (
          <p className="text-sm text-amber-400 mb-3">{prompt}</p>
        )}
        {game.votes.length > 0 && (
          <div className="mb-4 space-y-1">
            {game.votes.map((v, i) => (
              <div key={i} className="text-sm text-gray-400">
                {v.voter_seat}号 → {v.target_seat}号{v.weight > 1 && <span className="text-amber-400 ml-1">(1.5票)</span>}
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-wrap gap-2 mb-4">
          {game.players.filter((p) => p.is_alive && !p.is_human).map((p) => (
            <button key={p.id} onClick={() => setSelectedTarget(p.seat_number)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${selectedTarget === p.seat_number ? "bg-amber-500 text-gray-900" : "bg-gray-700 text-gray-300 hover:bg-gray-600"}`}>
              {p.seat_number}号 {p.name}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={() => { onSubmitVote(selectedTarget ?? 0); setSelectedTarget(null); }}
            disabled={loading || selectedTarget === null}
            className="flex-1 py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-colors">
            {loading ? "提交中..." : "投票"}
          </button>
          <button onClick={onResolveVotes} disabled={loading}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 text-white rounded-xl text-sm transition-colors">
            结算投票
          </button>
        </div>
      </div>
    );
  }

  // ---- Death announce ----
  if (phase === "day_death_announce") {
    const lastDeath = game.timeline?.filter(t => t.type === "death").pop();
    const lastSystem = game.timeline?.filter(t => t.type === "system" && t.text?.startsWith("天亮")).pop();
    const deathInfo = lastDeath?.text ?? lastSystem?.text ?? "等待公布死讯";
    return (
      <div className="bg-gray-800/80 rounded-2xl p-6 border border-gray-700 text-center">
        <Skull size={32} className="text-gray-400 mx-auto mb-3" />
        <p className="text-gray-300 text-lg">{deathInfo}</p>
        <button onClick={onContinueDay} disabled={loading}
          className="mt-4 px-6 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 text-white rounded-xl text-sm transition-colors">
          继续
        </button>
      </div>
    );
  }

  // Default fallback
  return (
    <div className="bg-gray-800/80 rounded-2xl p-5 border border-gray-700 text-center">
      <p className="text-gray-400">当前阶段: {game.phase_label}</p>
      <p className="text-gray-500 text-sm mt-1">{prompt ?? "等待游戏推进..."}</p>
      {phase === "night_end" && (
        <button onClick={onStartDay} disabled={loading}
          className="mt-4 px-6 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-sm">
          进入白天
        </button>
      )}
    </div>
  );
}
