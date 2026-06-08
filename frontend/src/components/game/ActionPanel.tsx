"use client";

import { useState } from "react";
import { Bot, Mic, Moon, Send, Vote } from "lucide-react";
import type { GameResponse } from "@/types/game";

type Props = {
  game: GameResponse;
  loading: boolean;
  onSubmitNight: (targetSeat: number | null) => void;
  onTriggerAI: () => void;
  onSubmitSpeech: (text: string) => void;
  onSubmitVote: (targetSeat: number) => void;
};

export default function ActionPanel({
  game,
  loading,
  onSubmitNight,
  onTriggerAI,
  onSubmitSpeech,
  onSubmitVote,
}: Props) {
  const [speechInput, setSpeechInput] = useState("");
  const [selectedTarget, setSelectedTarget] = useState<number | null>(null);

  const { phase } = game.game;
  const isGameOver = phase === "game_over";
  const alivePlayers = game.players.filter((p) => p.is_alive && !p.is_human);
  const humanRole = game.human?.role ?? "";

  const handleSpeechSubmit = () => {
    if (!speechInput.trim()) return;
    onSubmitSpeech(speechInput);
    setSpeechInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSpeechSubmit();
    }
  };

  if (isGameOver) {
    const winnerMap: Record<string, string> = {
      good: "好人阵营",
      wolf: "狼人阵营",
      third: "第三方阵营",
      cursed_fox: "咒狐",
    };
    return (
      <div className="bg-gray-800/80 rounded-2xl p-6 border border-gray-700 text-center">
        <h3 className="text-2xl font-bold text-amber-400 mb-2">游戏结束</h3>
        <p className="text-lg text-gray-200">
          {winnerMap[game.game.winner ?? ""] ?? game.game.winner} 获胜
        </p>
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {game.players.map((p) => (
            <span
              key={p.id}
              className={`px-3 py-1 rounded-full text-sm ${
                p.is_human
                  ? "bg-blue-600 text-white"
                  : p.faction === "wolf"
                  ? "bg-red-900/50 text-red-300 border border-red-700"
                  : "bg-gray-700 text-gray-300"
              }`}
            >
              {p.seat_number}号 {p.name}: {p.role_name ?? p.role ?? "?"}
            </span>
          ))}
        </div>
      </div>
    );
  }

  // Night phase
  if (phase === "night" || phase === "night_action") {
    const isWolf = humanRole.includes("wolf") || humanRole === "werewolf";
    const isSeer = humanRole === "seer" || humanRole === "psychic";

    if (isWolf || isSeer) {
      return (
        <div className="bg-gray-800/80 rounded-2xl p-5 border border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <Moon size={20} className="text-indigo-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {isWolf ? "选择袭击目标" : "选择查验目标"}
            </h3>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {alivePlayers.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedTarget(p.seat_number)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedTarget === p.seat_number
                    ? "bg-amber-500 text-gray-900"
                    : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                }`}
              >
                {p.seat_number}号 {p.name}
              </button>
            ))}
          </div>

          {game.last_check && (
            <div className="mb-4 p-3 bg-gray-900/50 rounded-lg text-sm">
              <span className="text-gray-400">上次查验: </span>
              <span className={game.last_check.result === "good" ? "text-emerald-400" : "text-red-400"}>
                {game.last_check.target_seat}号 -
                {game.last_check.result === "good" ? "好人" : "狼人"}
                {game.last_check.role ? ` / ${game.last_check.role}` : ""}
              </span>
            </div>
          )}

          <button
            onClick={() => onSubmitNight(selectedTarget)}
            disabled={loading || selectedTarget === null}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-colors"
          >
            {loading ? "结算中..." : "确认行动"}
          </button>
        </div>
      );
    }

    // Villager at night
    return (
      <div className="bg-gray-800/80 rounded-2xl p-6 border border-gray-700 text-center">
        <Moon size={32} className="text-indigo-400 mx-auto mb-3" />
        <p className="text-gray-300 text-lg">天黑请闭眼</p>
        <p className="text-gray-500 text-sm mt-1">等待夜晚结算...</p>
        <button
          onClick={() => onSubmitNight(null)}
          disabled={loading}
          className="mt-4 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 text-white rounded-xl text-sm transition-colors"
        >
          {loading ? "结算中..." : "结算夜晚"}
        </button>
      </div>
    );
  }

  // Day discuss phase
  if (phase === "day_discuss" || phase === "day_speech" || phase === "discuss") {
    return (
      <div className="bg-gray-800/80 rounded-2xl p-5 border border-gray-700">
        <div className="flex gap-3">
          <textarea
            value={speechInput}
            onChange={(e) => setSpeechInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的发言..."
            maxLength={600}
            rows={3}
            className="flex-1 bg-gray-900 border border-gray-600 rounded-xl px-4 py-3 text-gray-100 text-sm resize-none focus:outline-none focus:border-blue-500 transition-colors"
          />
          <div className="flex flex-col gap-2">
            <button
              onClick={handleSpeechSubmit}
              disabled={loading || !speechInput.trim()}
              className="px-5 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-colors flex items-center gap-2"
            >
              <Send size={16} />
              发言
            </button>
            <button
              onClick={onTriggerAI}
              disabled={loading}
              className="px-5 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 text-gray-200 rounded-xl text-sm transition-colors flex items-center gap-2"
            >
              <Bot size={16} />
              AI 发言
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Vote phase
  if (phase === "vote" || phase === "day_vote") {
    return (
      <div className="bg-gray-800/80 rounded-2xl p-5 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Vote size={20} className="text-amber-400" />
          <h3 className="text-lg font-semibold text-gray-100">投票放逐</h3>
        </div>

        {game.votes.length > 0 && (
          <div className="mb-4 space-y-1">
            {game.votes.map((v, i) => (
              <div key={i} className="text-sm text-gray-400">
                {v.voter_seat}号 → {v.target_seat}号
                {v.weight > 1 && <span className="text-amber-400 ml-1">(1.5票)</span>}
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-4">
          {alivePlayers.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedTarget(p.seat_number)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedTarget === p.seat_number
                  ? "bg-amber-500 text-gray-900"
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {p.seat_number}号 {p.name}
            </button>
          ))}
        </div>

        <button
          onClick={() => selectedTarget !== null && onSubmitVote(selectedTarget)}
          disabled={loading || selectedTarget === null}
          className="w-full py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition-colors"
        >
          {loading ? "结算中..." : "确认投票"}
        </button>
      </div>
    );
  }

  // Default fallback
  return (
    <div className="bg-gray-800/80 rounded-2xl p-5 border border-gray-700 text-center">
      <p className="text-gray-400">当前阶段: {game.phase_label}</p>
      <p className="text-gray-500 text-sm mt-1">等待游戏推进...</p>
    </div>
  );
}
