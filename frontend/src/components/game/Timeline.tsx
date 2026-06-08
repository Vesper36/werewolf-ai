"use client";

import { useEffect, useRef } from "react";
import { CircleDot, Skull, MessageSquare, Vote, Shield, Trophy } from "lucide-react";
import type { TimelineItem } from "@/types/game";

type Props = {
  items: TimelineItem[];
};

const typeConfig: Record<string, { icon: typeof CircleDot; color: string }> = {
  system: { icon: CircleDot, color: "text-gray-400" },
  death: { icon: Skull, color: "text-red-400" },
  speech: { icon: MessageSquare, color: "text-blue-400" },
  vote: { icon: Vote, color: "text-amber-400" },
  police: { icon: Shield, color: "text-amber-400" },
  game_over: { icon: Trophy, color: "text-emerald-400" },
};

export default function Timeline({ items }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [items.length]);

  return (
    <div ref={scrollRef} className="flex flex-col gap-1 overflow-y-auto max-h-full pr-1">
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-4">暂无事件</p>
      ) : (
        items.map((item, index) => {
          const config = typeConfig[item.type] ?? typeConfig.system;
          const Icon = config.icon;
          return (
            <div
              key={`${item.type}-${index}`}
              className="flex items-start gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-800/50 transition-colors"
            >
              <Icon size={14} className={`${config.color} flex-shrink-0 mt-0.5`} />
              <span className="text-sm text-gray-300 leading-snug">{item.text}</span>
            </div>
          );
        })
      )}
    </div>
  );
}
