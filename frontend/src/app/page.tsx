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
    aiConfig,
    game,
    loading,
    status,
    setDifficulty,
    setSelectedBoardId,
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
              {difficulties.map((item) => (
                <button key={item.id} onClick={() => setDifficulty(item.id)} className={`border p-4 text-left ${difficulty === item.id ? "border-red-500 bg-red-950/40" : "border-stone-800 bg-[#17191f]"}`}>
                  <strong className="block text-xl">{item.title}</strong>
                  <span className="text-sm text-stone-400">{item.desc}</span>
                </button>
              ))}
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
                  <button key={board.id} onClick={() => setSelectedBoardId(board.id)} className={`grid gap-1 border p-4 text-left ${board.id === selectedBoardId ? "border-red-500 bg-stone-950" : "border-stone-800 bg-stone-900/70"}`}>
                    <strong className="text-lg">{board.name}</strong>
                    <span className="text-sm leading-6 text-stone-400">{board.description}</span>
                    <small className="text-stone-500">{board.player_count}人 / {board.has_police ? "带上警" : "不上警"}</small>
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
          <main className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_430px]">
            <section className="border border-stone-800 bg-[#17191f] p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-stone-800 pb-3">
                <span>第 {game.game.day_number} 天</span>
                <strong className="text-2xl">{game.phase_label}</strong>
                <span>{game.game.winner ? `胜利：${game.game.winner}` : "对局进行中"}</span>
              </div>

              <div className="grid grid-cols-3 gap-3 md:grid-cols-4 xl:grid-cols-6">
                {game.players.map((player) => (
                  <PlayerCard
                    key={player.id}
                    player={player}
                    isSelected={targetSeat === player.seat_number}
                    onClick={() => setTargetSeat(player.seat_number)}
                    showRole={player.is_human || game.game.phase === "game_over"}
                  />
                ))}
              </div>

              <div className="mt-5 grid gap-3 border-t border-stone-800 pt-4 md:grid-cols-[minmax(180px,1fr)_auto_auto_auto]">
                <select className="bg-stone-950 p-3" value={targetSeat ?? ""} onChange={(e) => setTargetSeat(e.target.value ? Number(e.target.value) : null)}>
                  <option value="">选择目标座位</option>
                  {aliveTargets.map((player) => <option key={player.id} value={player.seat_number}>{player.seat_number}号 {player.name}</option>)}
                </select>
                <button onClick={() => startNight()} disabled={loading || !["role_dealt", "night_start"].includes(game.game.phase)} className="bg-indigo-700 px-4 py-3 disabled:opacity-50"><Moon className="mr-2 inline" size={18} />进入夜晚</button>
                <button onClick={startDay} disabled={loading || !["day_death_announce", "day_discuss"].includes(game.game.phase)} className="bg-indigo-600 px-4 py-3 disabled:opacity-50"><Moon className="mr-2 inline" size={18} />开始白天</button>
                <button onClick={triggerAISpeeches} disabled={loading || game.game.phase !== "day_discuss"} className="bg-stone-700 px-4 py-3 disabled:opacity-50"><Bot className="mr-2 inline" size={18} />AI 发言</button>
                <button onClick={startVote} disabled={loading || game.game.phase !== "day_discuss"} className="bg-amber-600 px-4 py-3 disabled:opacity-50"><Vote className="mr-2 inline" size={18} />进入投票</button>
                <button onClick={() => targetSeat && submitVote(targetSeat)} disabled={loading || !targetSeat || game.game.phase !== "day_vote"} className="bg-amber-700 px-4 py-3 disabled:opacity-50"><Vote className="mr-2 inline" size={18} />投票</button>
                <button onClick={resolveVotes} disabled={loading || game.game.phase !== "day_vote"} className="bg-red-700 px-4 py-3 disabled:opacity-50"><Vote className="mr-2 inline" size={18} />结算投票</button>
              </div>

              {game.pending_human_prompt && (
                <div className="mt-3 border border-indigo-700 bg-indigo-950/40 p-3 text-sm text-indigo-200">
                  {game.pending_human_prompt}
                </div>
              )}

              {game.last_check && (
                <div className="mt-3 border border-amber-700 bg-amber-950/40 p-3 text-sm text-amber-100">
                  <ShieldQuestion className="mr-2 inline" size={16} />
                  {game.last_check.target_seat}号查验：{game.last_check.result === "good" ? "好人" : "狼人"}{game.last_check.role ? ` / ${game.last_check.role}` : ""}
                </div>
              )}

              <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto]">
                <textarea className="min-h-24 resize-y bg-stone-950 p-3" value={speechText} onChange={(e) => setSpeechText(e.target.value)} placeholder="输入你的发言，或用语音识别填入" />
                <button onClick={useBrowserSpeech} className="bg-stone-700 px-4 py-3"><Mic className="mr-2 inline" size={18} />语音</button>
                <button onClick={sendSpeech} disabled={loading || !speechText.trim()} className="bg-red-700 px-4 py-3 disabled:opacity-50"><Send className="mr-2 inline" size={18} />发送</button>
              </div>
            </section>

            <aside className="grid content-start gap-4">
              <section className="border border-stone-800 bg-[#17191f] p-4">
                <h2 className="mb-3 text-xl font-semibold">逐字发言</h2>
                <div className="grid max-h-[440px] gap-3 overflow-y-auto pr-1">
                  {game.speeches.length === 0 ? <p className="text-sm text-stone-500">等待第一轮发言</p> : game.speeches.map((speech) => (
                    <SpeechBubble key={`${speech.player_id}-${speech.timestamp}`} text={speech.text} charsPerSecond={speech.typing_cps} seatNumber={speech.seat_number} name={speech.name} isHuman={speech.player_id === game.human?.id} />
                  ))}
                </div>
              </section>
              <section className="border border-stone-800 bg-[#17191f] p-4">
                <h2 className="mb-3 text-xl font-semibold">AI 隔离线程</h2>
                <div className="grid grid-cols-2 gap-2">
                  {game.agents.map((agent) => (
                    <div key={agent.thread_id} className="min-w-0 border border-stone-800 bg-stone-950 p-2 text-sm">
                      <strong>{agent.seat_number}号 {agent.personality}</strong>
                      <p className="truncate text-xs text-stone-500">{agent.thread_id}</p>
                    </div>
                  ))}
                </div>
              </section>
              <section className="h-[260px] border border-stone-800 bg-[#17191f] p-4">
                <h2 className="mb-3 text-xl font-semibold">日志</h2>
                <Timeline items={game.timeline} />
              </section>
            </aside>
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
