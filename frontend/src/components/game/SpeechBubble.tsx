"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  text: string;
  charsPerSecond?: number;
  seatNumber: number;
  name: string;
  isHuman?: boolean;
};

export default function SpeechBubble({
  text,
  charsPerSecond = 3.8,
  seatNumber,
  name,
  isHuman,
}: Props) {
  const [visibleLength, setVisibleLength] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setVisibleLength(0);
    setIsComplete(false);

    const cps = Math.max(2, charsPerSecond);
    const intervalMs = 1000 / cps;

    intervalRef.current = setInterval(() => {
      setVisibleLength((prev) => {
        if (prev >= text.length) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setIsComplete(true);
          return text.length;
        }
        return prev + 1;
      });
    }, intervalMs);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [text, charsPerSecond]);

  const handleClick = () => {
    if (!isComplete) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setVisibleLength(text.length);
      setIsComplete(true);
    }
  };

  const displayText = text.slice(0, visibleLength);

  return (
    <div
      className={`flex gap-3 ${isHuman ? "flex-row-reverse" : "flex-row"}`}
      onClick={handleClick}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold ${
          isHuman ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-300"
        }`}
      >
        {seatNumber}
      </div>

      {/* Bubble */}
      <div
        className={`relative max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
          isHuman
            ? "bg-blue-600 text-white rounded-tr-sm"
            : "bg-gray-800 text-gray-200 rounded-tl-sm"
        }`}
      >
        <div className="text-xs text-gray-400 mb-1">
          {seatNumber}号 {name}
        </div>
        <span>{displayText}</span>
        {!isComplete && (
          <span className="inline-block w-0.5 h-4 bg-current ml-0.5 animate-pulse" />
        )}
      </div>
    </div>
  );
}
