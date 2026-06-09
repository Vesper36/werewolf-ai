"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useGameStore } from "@/stores/gameStore";
import PlayerCard from "@/components/game/PlayerCard";
import SpeechBubble from "@/components/game/SpeechBubble";
import Timeline from "@/components/game/Timeline";
import ActionPanel from "@/components/game/ActionPanel";
import { Loader2 } from "lucide-react";

export default function GamePage() {
  const params = useParams();
  const gameId = params.id as string;
  const {
    game, loading, fetchGame,
    startNight, submitNightAction, startDay,
    triggerAISpeeches, submitSpeech, submitVote, resolveVotes,
    selfExplode, hunterShoot, knightDuel, status,
  } = useGameStore();

  useEffect(() => {
    if (gameId) fetchGame(gameId);
  }, [gameId, fetchGame]);

  if (!game) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-56px)]">
        <Loader2 className="animate-spin text-amber-400" size={40} />
      </div>
    );
  }

  const { phase_label, human, players, timeline, speeches, game: gameState, board } = game;
  const phase = gameState.phase;
  const isGameOver = phase === "game_over";
  const isNight = phase.startsWith("night") || phase === "role_dealt";
  const isDay = phase.startsWith("day");

  return (
    <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col lg:flex-row gap-4 h-[calc(100vh-56px)]">
      {/* Main game area */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Phase indicator */}
        <div className="bg-gray-900 rounded-xl px-5 py-3 border border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${isNight ? "bg-blue-500" : isGameOver ? "bg-red-500" : "bg-amber-500"} ${!isGameOver ? "animate-pulse" : ""}`} />
            <span className="font-semibold text-lg">{phase_label}</span>
          </div>
          <div className="text-sm text-gray-400">
            第 {gameState.day_number} 天{board.has_police && " · 有警长"}
            {gameState.sheriff_id && ` · 警长: ${players.find((p) => p.id === gameState.sheriff_id)?.seat_number ?? "?"}号`}
          </div>
        </div>

        {/* Player grid */}
        <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800 flex-1">
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {players.map((p) => (
              <PlayerCard key={p.id} player={p} />
            ))}
          </div>
        </div>

        {/* Speech area */}
        {isDay && speeches.length > 0 && (
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 max-h-60 overflow-y-auto space-y-2">
            {speeches.slice(-8).map((s, i) => (
              <SpeechBubble
                key={`${s.player_id}-${s.day_number}-${i}`}
                seatNumber={s.seat_number}
                name={s.name}
                text={s.text}
                charsPerSecond={s.typing_cps}
                isHuman={s.player_id === human?.id}
              />
            ))}
          </div>
        )}

        {/* Action panel */}
        <ActionPanel
          game={game}
          loading={loading}
          onStartNight={() => startNight()}
          onSubmitNightAction={(actionType, targetSeat) => submitNightAction(actionType, targetSeat)}
          onStartDay={() => startDay()}
          onTriggerAI={() => triggerAISpeeches()}
          onSubmitSpeech={(text) => submitSpeech(text)}
          onSubmitVote={(seat) => submitVote(seat)}
          onResolveVotes={() => resolveVotes()}
          onSelfExplode={(seat) => selfExplode(seat)}
          onHunterShoot={(seat) => hunterShoot(seat)}
          onKnightDuel={(seat) => knightDuel(seat)}
        />

        {/* Status bar */}
        <div className="text-center text-xs text-gray-500 py-1">{status}</div>
      </div>

      {/* Timeline sidebar */}
      <div className="w-full lg:w-80 flex-shrink-0">
        <Timeline items={timeline} />
      </div>

      {/* Game over overlay */}
      {isGameOver && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center">
          <div className="bg-gray-900 rounded-2xl p-8 border border-amber-600 max-w-md w-full mx-4 text-center space-y-4">
            <h2 className="text-3xl font-bold text-amber-400">
              {gameState.winner === "good" && "好人阵营获胜!"}
              {gameState.winner === "wolf" && "狼人阵营获胜!"}
              {gameState.winner === "third" && "第三方阵营获胜!"}
              {gameState.winner === "cursed_fox" && "咒狐获胜!"}
            </h2>
            <div className="text-sm text-gray-400 space-y-1">
              {players.map((p) => (
                <div key={p.id} className={p.is_human ? "text-blue-300" : ""}>
                  {p.seat_number}号 {p.name} -- {p.role_name ?? p.role ?? "?"}
                  {p.is_human && "（你）"}
                </div>
              ))}
            </div>
            <a href="/"
              className="inline-block mt-4 px-6 py-2 bg-amber-600 hover:bg-amber-500 text-sm font-medium rounded-lg transition-colors">
              返回大厅
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
