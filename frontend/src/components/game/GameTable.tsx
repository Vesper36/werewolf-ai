"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Moon, Sun, Shield, Skull, User, Crown } from "lucide-react";
import type { Player, GameResponse } from "@/types/game";

type Props = {
  game: GameResponse;
  selectedSeat: number | null;
  onSelectPlayer: (seat: number) => void;
  currentSpeakerSeat?: number | null;
};

/**
 * 圆桌布局 -- 人类玩家固定在底部中央，其他玩家按座位号环绕圆桌排列
 * 座位布局逻辑：顶部弧线分布其他玩家，底部中央是人类玩家
 */
export default function GameTable({ game, selectedSeat, onSelectPlayer, currentSpeakerSeat }: Props) {
  const human = game.human;
  const players = game.players;
  const phase = game.game.phase;
  const isNight = phase.startsWith("night") || phase === "role_dealt";

  // 分离人类玩家和其他玩家
  const otherPlayers = players.filter((p) => p.id !== human?.id);
  const humanPlayer = players.find((p) => p.id === human?.id);

  // 计算其他玩家在圆桌上的位置（上半圆弧线分布）
  const getCirclePosition = (index: number, total: number) => {
    // 从左下角到右下角的弧线，避开底部中央（人类玩家位置）
    const startAngle = -160; // 左侧起点
    const endAngle = -20;    // 右侧终点
    const angleRange = endAngle - startAngle;
    const angle = startAngle + (angleRange * (index / (total - 1)));
    const rad = (angle * Math.PI) / 180;
    const radius = 42; // 圆桌半径百分比
    const cx = 50 + radius * Math.cos(rad);
    const cy = 45 + radius * Math.sin(rad);
    return { cx, cy };
  };

  const phaseColor = isNight ? "border-blue-900/50" : "border-amber-900/50";
  const tableBg = isNight ? "bg-gray-900/80" : "bg-gray-800/60";

  return (
    <div className="relative w-full min-h-[460px] flex items-end justify-center pb-2">
      {/* 圆桌背景 */}
      <div className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[45%] w-[85%] h-[80%] rounded-full ${tableBg} border ${phaseColor} backdrop-blur-sm`}>
        {/* 桌面中央装饰 */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-2 ${isNight ? "bg-blue-950/80" : "bg-amber-950/80"} border ${phaseColor}`}>
            {isNight ? <Moon size={24} className="text-blue-400" /> : <Sun size={24} className="text-amber-400" />}
          </div>
          <span className="text-xs text-gray-500 font-mono">
            {game.board.name}
          </span>
        </div>
      </div>

      {/* 其他玩家（圆弧分布） */}
      <AnimatePresence>
        {otherPlayers.map((player, index) => {
          const pos = getCirclePosition(index, otherPlayers.length);
          const isSelected = selectedSeat === player.seat_number;
          const isSpeaking = currentSpeakerSeat === player.seat_number;

          return (
            <motion.div
              key={player.id}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.3 }}
              transition={{ delay: index * 0.05, type: "spring", stiffness: 200 }}
              className="absolute"
              style={{
                left: `${pos.cx}%`,
                top: `${pos.cy}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              <PlayerNode
                player={player}
                isSelected={isSelected}
                isSpeaking={isSpeaking}
                onClick={() => player.is_alive && onSelectPlayer(player.seat_number)}
                showRole={game.game.phase === "game_over"}
              />
            </motion.div>
          );
        })}
      </AnimatePresence>

      {/* 人类玩家（底部中央） */}
      {humanPlayer && (
        <div className="relative z-10">
          <PlayerNode
            player={humanPlayer}
            isHuman
            isSelected={selectedSeat === humanPlayer.seat_number}
            isSpeaking={currentSpeakerSeat === humanPlayer.seat_number}
            showRole
          />
        </div>
      )}
    </div>
  );
}

/** 单个玩家节点 */
function PlayerNode({
  player,
  isHuman = false,
  isSelected = false,
  isSpeaking = false,
  showRole = false,
  onClick,
}: {
  player: Player;
  isHuman?: boolean;
  isSelected?: boolean;
  isSpeaking?: boolean;
  showRole?: boolean;
  onClick?: () => void;
}) {
  const isDead = !player.is_alive;

  return (
    <motion.div
      whileHover={player.is_alive && !isHuman ? { scale: 1.1 } : undefined}
      whileTap={player.is_alive && !isHuman ? { scale: 0.95 } : undefined}
      onClick={onClick}
      className={`
        relative flex flex-col items-center gap-1 cursor-pointer
        transition-all duration-200
        ${isDead ? "opacity-40 grayscale" : ""}
        ${isHuman ? "scale-110" : ""}
      `}
    >
      {/* 头像 */}
      <div
        className={`
          w-12 h-12 rounded-full flex items-center justify-center
          border-2 transition-all duration-300
          ${isHuman ? "bg-blue-600 border-blue-400" : "bg-gray-700 border-gray-600"}
          ${isSelected ? "ring-3 ring-amber-400 border-amber-400 bg-amber-900/50" : ""}
          ${isSpeaking ? "ring-3 ring-emerald-400 border-emerald-400 animate-pulse" : ""}
          ${isDead ? "border-gray-800 bg-gray-900" : ""}
        `}
      >
        {isDead ? (
          <Skull size={20} className="text-gray-600" />
        ) : (
          <User size={20} className={isHuman ? "text-blue-200" : "text-gray-300"} />
        )}
      </div>

      {/* 警长徽章 */}
      {player.is_sheriff && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -top-2 -right-2 w-6 h-6 bg-amber-500 rounded-full flex items-center justify-center shadow-lg shadow-amber-500/30"
        >
          <Crown size={14} className="text-gray-900" />
        </motion.div>
      )}

      {/* 座位号 + 名字 */}
      <span className={`text-[10px] font-mono ${isDead ? "text-gray-600" : "text-gray-400"}`}>
        {player.seat_number}号
      </span>
      <span className={`text-xs font-medium truncate max-w-16 text-center ${isDead ? "text-gray-600 line-through" : isHuman ? "text-blue-300" : "text-gray-300"}`}>
        {isHuman ? "你" : player.name}
      </span>

      {/* 角色（游戏结束或人类玩家时显示） */}
      {showRole && player.role_name && (
        <span className="text-[10px] text-amber-400 font-medium">{player.role_name}</span>
      )}

      {/* 出局标签 */}
      {isDead && (
        <span className="text-[10px] text-red-400">出局</span>
      )}

      {/* 发言指示器 */}
      {isSpeaking && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="absolute -bottom-1 left-1/2 -translate-x-1/2"
        >
          <div className="flex gap-0.5">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                animate={{ height: [4, 12, 4] }}
                transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                className="w-1 bg-emerald-400 rounded-full"
              />
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
