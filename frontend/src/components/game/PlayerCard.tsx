"use client";

import { Shield, Skull, User } from "lucide-react";
import type { Player } from "@/types/game";

type Props = {
  player: Player;
  isSelected?: boolean;
  isCurrentSpeaker?: boolean;
  onClick?: () => void;
  showRole?: boolean;
};

export default function PlayerCard({
  player,
  isSelected,
  isCurrentSpeaker,
  onClick,
  showRole,
}: Props) {
  const canClick = onClick && player.is_alive && !player.is_human;

  return (
    <button
      onClick={canClick ? onClick : undefined}
      className={`
        relative flex flex-col items-center gap-1 p-3 rounded-xl border transition-all duration-200
        ${
          player.is_alive
            ? "border-gray-700 bg-gray-800/80 hover:bg-gray-700/80"
            : "border-gray-800 bg-gray-900/50 opacity-50"
        }
        ${isSelected ? "ring-2 ring-amber-400 border-amber-500 bg-amber-900/20" : ""}
        ${isCurrentSpeaker ? "ring-2 ring-emerald-400 border-emerald-500" : ""}
        ${player.is_human ? "ring-1 ring-blue-500/50" : ""}
        ${canClick ? "cursor-pointer" : "cursor-default"}
      `}
      disabled={!canClick}
    >
      {/* Sheriff badge */}
      {player.is_sheriff && (
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-amber-500 rounded-full flex items-center justify-center">
          <Shield size={14} className="text-gray-900" />
        </div>
      )}

      {/* Avatar area */}
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center ${
          player.is_alive
            ? player.is_human
              ? "bg-blue-600"
              : "bg-gray-600"
            : "bg-gray-800"
        }`}
      >
        {player.is_alive ? (
          <User size={20} className="text-gray-200" />
        ) : (
          <Skull size={20} className="text-gray-500" />
        )}
      </div>

      {/* Seat number */}
      <span className="text-xs font-mono text-gray-400">{player.seat_number}号</span>

      {/* Name */}
      <span
        className={`text-sm font-medium truncate max-w-full ${
          player.is_alive ? "text-gray-100" : "text-gray-500 line-through"
        }`}
      >
        {player.is_human ? "你" : player.name}
      </span>

      {/* Role (if revealed) */}
      {showRole && player.role_name && (
        <span className="text-xs text-amber-400">{player.role_name}</span>
      )}

      {/* Status */}
      {!player.is_alive && (
        <span className="text-xs text-red-400">出局</span>
      )}
    </button>
  );
}
