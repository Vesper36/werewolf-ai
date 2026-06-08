import { create } from "zustand";
import * as api from "@/services/api";
import type { AIConfig, Board, Difficulty, GameResponse } from "@/types/game";

type GameState = {
  // Lobby state
  boards: Board[];
  difficulty: Difficulty;
  selectedBoardId: string;
  aiConfig: AIConfig;

  // Game state
  gameId: string | null;
  game: GameResponse | null;

  // UI state
  loading: boolean;
  status: string;

  // Actions
  setDifficulty: (d: Difficulty) => void;
  setSelectedBoardId: (id: string) => void;
  setAiConfig: (config: Partial<AIConfig>) => void;
  setStatus: (s: string) => void;

  fetchBoards: () => Promise<void>;
  createGame: () => Promise<void>;
  fetchGame: (gameId: string) => Promise<void>;
  submitNight: (targetSeat: number | null) => Promise<void>;
  triggerAISpeeches: () => Promise<void>;
  submitSpeech: (text: string) => Promise<void>;
  submitVote: (targetSeat: number) => Promise<void>;
  testConnection: () => Promise<void>;
};

const DEFAULT_AI: AIConfig = {
  provider: "offline",
  base_url: "https://api.openai.com/v1",
  api_key: "",
  model: "gpt-4o-mini",
  temperature: 0.75,
  timeout_seconds: 25,
};

export const useGameStore = create<GameState>((set, get) => ({
  boards: [],
  difficulty: "expert",
  selectedBoardId: "",
  aiConfig: { ...DEFAULT_AI },

  gameId: null,
  game: null,

  loading: false,
  status: "离线策略已就绪",

  setDifficulty: (d) => set({ difficulty: d }),
  setSelectedBoardId: (id) => set({ selectedBoardId: id }),
  setAiConfig: (config) =>
    set((state) => ({ aiConfig: { ...state.aiConfig, ...config } })),
  setStatus: (s) => set({ status: s }),

  fetchBoards: async () => {
    try {
      const { boards } = await api.fetchBoards();
      const defaultBoard =
        boards.find((b) => b.id === "expert_mech_psychic") ?? boards[0];
      set({
        boards,
        selectedBoardId: defaultBoard?.id ?? "",
      });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "加载板子失败" });
    }
  },

  createGame: async () => {
    const { selectedBoardId, boards, difficulty, aiConfig } = get();
    const board = boards.find((b) => b.id === selectedBoardId);
    if (!board) return;

    set({ loading: true });
    try {
      const humanRole = board.roles.some((r) => r.role === "seer")
        ? "seer"
        : "psychic";
      const result = await api.createGame({
        board_id: board.id,
        difficulty,
        human_name: "你",
        human_role: humanRole,
        ai: aiConfig,
      });
      set({
        game: result,
        gameId: result.game.game_id,
        status: "已开局，身份已发放",
      });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "创建游戏失败" });
    } finally {
      set({ loading: false });
    }
  },

  fetchGame: async (gameId) => {
    try {
      const result = await api.fetchGame(gameId);
      set({ game: result, gameId });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "获取游戏状态失败" });
    }
  },

  submitNight: async (targetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.resolveNight(gameId, targetSeat);
      set({ game: result, status: "夜晚已结算" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "夜晚结算失败" });
    } finally {
      set({ loading: false });
    }
  },

  triggerAISpeeches: async () => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.runAiSpeeches(gameId);
      set({ game: result, status: "AI 发言已生成" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "AI 发言失败" });
    } finally {
      set({ loading: false });
    }
  },

  submitSpeech: async (text) => {
    const { gameId } = get();
    if (!gameId || !text.trim()) return;
    set({ loading: true });
    try {
      const result = await api.submitSpeech(gameId, text);
      set({ game: result, status: "你的发言已发送" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "发言发送失败" });
    } finally {
      set({ loading: false });
    }
  },

  submitVote: async (targetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.resolveVote(gameId, targetSeat);
      set({ game: result, status: "投票已结算" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "投票失败" });
    } finally {
      set({ loading: false });
    }
  },

  testConnection: async () => {
    const { aiConfig } = get();
    set({ loading: true });
    try {
      const result = await api.testSettings(aiConfig);
      set({ status: result.message });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "连接失败" });
    } finally {
      set({ loading: false });
    }
  },
}));
