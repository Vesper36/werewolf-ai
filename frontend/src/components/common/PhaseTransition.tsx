"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Moon, Sun, Swords, Skull } from "lucide-react";

type Props = {
  phase: string;
  phaseLabel: string;
};

const PHASE_CONFIG: Record<string, { icon: typeof Moon; color: string; bg: string; gradient: string }> = {
  night: { icon: Moon, color: "text-blue-300", bg: "bg-blue-950", gradient: "from-blue-950/90 to-gray-950/90" },
  day: { icon: Sun, color: "text-amber-300", bg: "bg-amber-950", gradient: "from-amber-950/90 to-gray-950/90" },
  vote: { icon: Swords, color: "text-red-300", bg: "bg-red-950", gradient: "from-red-950/90 to-gray-950/90" },
  death: { icon: Skull, color: "text-gray-300", bg: "bg-gray-900", gradient: "from-gray-900/90 to-gray-950/90" },
};

function getPhaseType(phase: string): string {
  if (phase.startsWith("night") || phase === "role_dealt") return "night";
  if (phase === "day_vote" || phase === "day_pk") return "vote";
  if (phase === "day_death_announce") return "death";
  return "day";
}

export default function PhaseTransition({ phase, phaseLabel }: Props) {
  const type = getPhaseType(phase);
  const config = PHASE_CONFIG[type];
  const Icon = config.icon;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={type}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="pointer-events-none fixed inset-0 z-40"
      >
        {/* 全屏半透明遮罩 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.15 }}
          className={`absolute inset-0 ${config.bg}`}
        />

        {/* 中央图标 + 标签 */}
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.5, opacity: 0 }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center"
        >
          <Icon size={48} className={`${config.color} mx-auto mb-3 opacity-60`} />
          <h2 className={`text-2xl font-bold ${config.color} opacity-80`}>{phaseLabel}</h2>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
