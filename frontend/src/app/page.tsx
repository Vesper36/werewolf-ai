"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, Crown, Gauge, Mic, Moon, Play, Radio, Send, Settings, Shield, ShieldQuestion, Star, Swords, Vote, Zap } from "lucide-react";
import PlayerCard from "@/components/game/PlayerCard";
import SpeechBubble from "@/components/game/SpeechBubble";
import Timeline from "@/components/game/Timeline";
import { useGameStore } from "@/stores/gameStore";
import type { Difficulty } from "@/types/game";

const DIFFICULTIES = [
  { id: "novice" as Difficulty, title: "入门", desc: "9人不上警，练基础发言", Icon: Star, color: "emerald", players: "9人", police: false },
  { id: "basic" as Difficulty, title: "基础", desc: "12人标准局，警徽流入门", Icon: Shield, color: "blue", players: "12人", police: true },
  { id: "advanced" as Difficulty, title: "进阶", desc: "骑士、咒狐、票型压力", Icon: Zap, color: "purple", players: "12人", police: true },
  { id: "expert" as Difficulty, title: "大神", desc: "京城大师赛风格花板子", Icon: Crown, color: "amber", players: "12人", police: true },
];

const CL: Record<string, { ring: string; bg: string; border: string; text: string }> = {
  emerald: { ring: "ring-emerald-400", bg: "bg-emerald-950/40", border: "border-emerald-500", text: "text-emerald-400" },
  blue: { ring: "ring-blue-400", bg: "bg-blue-950/40", border: "border-blue-500", text: "text-blue-400" },
  purple: { ring: "ring-purple-400", bg: "bg-purple-950/40", border: "border-purple-500", text: "text-purple-400" },
  amber: { ring: "ring-amber-400", bg: "bg-amber-950/40", border: "border-amber-500", text: "text-amber-400" },
};

export default function Home() {
  const {
    boards,
    difficulty,
    selectedBoardId,
    selectedRole,
    aiConfig,
    game,
    loading,
    status,
    setDifficulty,
    setSelectedBoardId,
    setSelectedRole,
    setAiConfig,
    fetchBoards,
    createGame,
    startNight,
    startDay,
    submitNightAction,
    triggerAISpeeches,
    submitSpeech,
    submitVote,
    resolveVotes,
    startVote,
    testConnection,
  } = useGameStore();
  const [showSettings, setShowSettings] = useState(false);
  const [targetSeat, setTargetSeat] = useState<number | null>(null);
  const [speechText, setSpeechText] = useState("");

  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  const filteredBoards = useMemo(() => {
    const matched = boards.filter((board) => board.difficulty.includes(difficulty));
    return matched.length ? matched : boards;
  }, [boards, difficulty]);

  const selectedBoard = useMemo(
    () => boards.find((board) => board.id === selectedBoardId) ?? filteredBoards[0],
    [boards, filteredBoards, selectedBoardId],
  );

  const aliveTargets = game?.players.filter((player) => player.is_alive && !player.is_human) ?? [];

  useEffect(() => {
    if (!filteredBoards.find((board) => board.id === selectedBoardId) && filteredBoards[0]) {
      setSelectedBoardId(filteredBoards[0].id);
    }
  }, [filteredBoards, selectedBoardId, setSelectedBoardId]);

  useEffect(() => {
    window.render_game_to_text = () =>
      JSON.stringify({
        mode: game ? "game" : "lobby",
        status,
        phase: game?.phase_label,
        day: game?.game.day_number,
        board: selectedBoard?.name,
        aliveSeats: game?.players.filter((p) => p.is_alive).map((p) => p.seat_number),
        speechCount: game?.speeches.length ?? 0,
      });
    window.advanceTime = () => undefined;
  }, [game, selectedBoard?.name, status]);

  async function handleStartGame() {
    if (!selectedBoard || loading) return;
    await createGame();
    const g = useGameStore.getState().game;
    if (g?.game?.game_id) {
      window.location.href = "/game/" + g.game.game_id;
    }
  }

  function sendSpeech() {
    const text = speechText.trim();
    if (!text) return;
    setSpeechText("");
    submitSpeech(text);
  }

  function useBrowserSpeech() {
    const recCtor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!recCtor) return;
    const rec = new recCtor();
    rec.lang = "zh-CN";
    rec.interimResults = false;
    rec.onresult = (event) => {
      const text = Array.from(event.results).map((result) => result[0]?.transcript ?? "").join("");
      setSpeechText((prev) => `${prev}${text}`);
    };
    rec.start();
  }

  return (
    <div className="min-h-[calc(100vh-56px)] bg-[#0f1115] text-stone-100">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-5 px-4 py-5">
        <header className="flex flex-wrap items-center justify-between gap-3 border border-stone-800 bg-[#17191f] px-4 py-3">
          <div className="flex items-center gap-3">
            <Swords className="text-red-400" size={28} />
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">AI狼人杀·大师竞技场</h1>
              <p className="text-sm text-stone-400">{game ? `${game.board.name} / ${game.phase_label}` : "选择板子后直接开局"}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="max-w-[520px] truncate border border-stone-700 bg-stone-950 px-3 py-2 text-sm text-stone-300">{loading ? "处理中..." : status}</span>
            <button onClick={() => setShowSettings((v) => !v)} className="border border-stone-700 bg-stone-900 p-2 hover:bg-stone-800" title="设置">
              <Settings size={20} />
            </button>
          </div>
        </header>

        {showSettings && (
          <section className="grid gap-3 border border-stone-800 bg-[#17191f] p-4">
            <div className="grid gap-3 md:grid-cols-5">
              <label className="grid gap-1 text-sm text-stone-400">
                API 类型
                <select className="bg-stone-950 p-2 text-stone-100" value={aiConfig.provider} onChange={(e) => setAiConfig({ provider: e.target.value })}>
                  <option value="offline">离线兜底</option>
                  <option value="openai">OpenAI-compatible</option>
                  <option value="deepseek">DeepSeek</option>
                  <option value="qwen">通义千问</option>
                  <option value="ollama">Ollama</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </label>
              <label className="grid gap-1 text-sm text-stone-400 md:col-span-2">
                Base URL
                <input className="bg-stone-950 p-2 text-stone-100" value={aiConfig.base_url} onChange={(e) => setAiConfig({ base_url: e.target.value })} />
              </label>
              <label className="grid gap-1 text-sm text-stone-400">
                Model
                <input className="bg-stone-950 p-2 text-stone-100" value={aiConfig.model} onChange={(e) => setAiConfig({ model: e.target.value })} />
              </label>
              <label className="grid gap-1 text-sm text-stone-400">
                API Key
                <input className="bg-stone-950 p-2 text-stone-100" type="password" value={aiConfig.api_key} onChange={(e) => setAiConfig({ api_key: e.target.value })} />
              </label>
            </div>
            <button onClick={testConnection} className="w-fit border border-red-800 bg-red-700 px-4 py-2 text-sm hover:bg-red-600">
              <Radio className="mr-2 inline" size={16} />
              连接测试
            </button>
          </section>
        )}

        {!game ? (
          <main className="grid gap-5 lg:grid-cols-[210px_minmax(0,1fr)_360px]">
            <aside className="grid content-start gap-3">
              {DIFFICULTIES.map((item) => {
  const c = CL[item.color] || CL.emerald;
  const isActive = difficulty === item.id;
  return (
    <button key={item.id} onClick={() => setDifficulty(item.id)}
      className={`border p-4 text-left transition-all duration-200 ${
        isActive
          ? `${c.border} ${c.bg} ring-1 ${c.ring}`
          : "border-stone-800 bg-[#17191f] hover:border-stone-600"
      }`}>
      <div className="flex items-center gap-3 mb-1">
        <item.Icon size={20} className={isActive ? c.text : "text-stone-500"} />
        <strong className="text-xl">{item.title}</strong>
        <span className={`ml-auto text-xs px-2 py-0.5 rounded ${isActive ? c.bg : "bg-stone-800"} ${c.text}`}>{item.players}</span>
        {item.police && <span className="text-xs text-amber-400">警长</span>}
      </div>
      <span className="text-sm text-stone-400">{item.desc}</span>
    </button>
  );
})}

              <div className="border-t border-stone-700 pt-3 mt-2">
                <p className="text-xs text-stone-500 mb-2">选择角色</p>
                <select className="w-full bg-stone-950 p-2 text-sm text-stone-100"
                  value={selectedRole ?? ""}
                  onChange={(e) => setSelectedRole(e.target.value || null)}>
                  <option value="">随机角色</option>
                  <option value="seer">预言家</option>
                  <option value="witch">女巫</option>
                  <option value="hunter">猎人</option>
                  <option value="guard">守卫</option>
                  <option value="knight">骑士</option>
                  <option value="villager">村民</option>
                  <option value="werewolf">狼人</option>
                </select>
              </div>
            </aside>

            <section className="border border-stone-800 bg-[#17191f] p-5">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm uppercase text-red-400">Board Workshop</p>
                  <h2 className="text-4xl font-semibold">选择今晚的板子</h2>
                </div>
                <button onClick={handleStartGame} disabled={!selectedBoard || loading} className="bg-red-700 px-4 py-3 font-medium hover:bg-red-600 disabled:opacity-50">
                  <Play className="mr-2 inline" size={18} />
                  开始游戏
                </button>
              </div>
              <div className="grid gap-3">
                {filteredBoards.map((board) => (
  <button key={board.id} onClick={() => setSelectedBoardId(board.id)}
    className={`border p-4 text-left transition-all ${
      board.id === selectedBoardId
        ? "border-red-500 bg-stone-950"
        : "border-stone-800 bg-stone-900/70 hover:border-stone-600"
    }`}>
    <div className="flex items-start justify-between gap-2">
      <strong className="text-lg">{board.name}</strong>
      <div className="flex gap-1.5">
        <span className="text-xs bg-stone-800 px-1.5 py-0.5 rounded">{board.player_count}人</span>
        {board.has_police && <span className="text-xs bg-amber-900/50 text-amber-400 px-1.5 py-0.5 rounded">警长</span>}
      </div>
    </div>
    <span className="text-sm leading-6 text-stone-400 mt-1 block">{board.description}</span>
    <div className="flex flex-wrap gap-1 mt-2">
      {Object.entries(board.role_counts).map(([role, count]) => (
        <span key={role} className="text-[11px] bg-stone-800/80 text-stone-400 px-1.5 py-0.5 rounded">
          {role}{count > 1 ? `x${count}` : ""}
        </span>
      ))}
    </div>
  </button>
))}
              </div>
            </section>

            <aside className="border border-stone-800 bg-[#17191f] p-5">
              <p className="text-sm uppercase text-red-400">阵营预览</p>
              <h2 className="mt-1 text-2xl font-semibold">{selectedBoard?.name ?? "未选择"}</h2>
              <p className="mt-3 leading-7 text-stone-400">{selectedBoard?.description}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {selectedBoard && Object.entries(selectedBoard.role_counts).map(([role, count]) => (
                  <span key={role} className="border border-stone-700 bg-stone-950 px-2 py-1 text-sm">{role}{count > 1 ? ` x${count}` : ""}</span>
                ))}
              </div>
              <p className="mt-5 flex items-center gap-2 text-sm text-stone-400"><Gauge size={16} />{selectedBoard?.night_order.join(" / ")}</p>
            </aside>
          </main>
        ) : (
          <main className="min-h-[60vh] flex items-center justify-center border border-stone-800 bg-[#17191f] p-10">
            <div className="text-center">
              <Swords size={48} className="text-red-400 mx-auto mb-4" />
              <p className="text-xl text-stone-300 mb-2">游戏进行中</p>
              <p className="text-sm text-stone-500 mb-4">{game.board.name} / {game.phase_label}</p>
              <a href={`/game/${game.game.game_id}`} className="inline-block bg-red-700 px-6 py-3 font-medium hover:bg-red-600 text-white">
                进入游戏
              </a>
            </div>
          </main>
        )}
      </div>
    </div>
  );
}

type SpeechRecognitionConstructor = new () => {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  start: () => void;
};

declare global {
  interface Window {
    render_game_to_text?: () => string;
    advanceTime?: (ms: number) => void;
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}
