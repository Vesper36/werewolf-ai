import { create } from "zustand";
import * as api from "@/services/api";
import type { AIConfig, Board, Difficulty, GameResponse } from "@/types/game";

type GameState = {
  // Lobby state
  boards: Board[];
  difficulty: Difficulty;
  selectedBoardId: string;
  selectedRole: string | null;
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
  setSelectedRole: (role: string | null) => void;
  setAiConfig: (config: Partial<AIConfig>) => void;
  setStatus: (s: string) => void;

  fetchBoards: () => Promise<void>;
  createGame: () => Promise<void>;
  fetchGame: (gameId: string) => Promise<void>;

  // Night flow
  startNight: () => Promise<void>;
  submitNightAction: (actionType: string, targetSeat: number | null, secondTargetSeat?: number | null) => Promise<void>;

  // Day flow
  startDay: () => Promise<void>;
  continueDay: () => Promise<void>;
  triggerAISpeeches: () => Promise<void>;
  submitSpeech: (text: string) => Promise<void>;
  submitVote: (targetSeat: number) => Promise<void>;
  resolveVotes: () => Promise<void>;
  startVote: () => Promise<void>;

  // Special actions
  selfExplode: (targetSeat: number | null) => Promise<void>;
  hunterShoot: (targetSeat: number) => Promise<void>;
  knightDuel: (targetSeat: number) => Promise<void>;

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
  selectedRole: null,
  aiConfig: { ...DEFAULT_AI },

  gameId: null,
  game: null,

  loading: false,
  status: "离线策略已就绪",

  setDifficulty: (d) => set({ difficulty: d }),
  setSelectedBoardId: (id) => set({ selectedBoardId: id }),
  setSelectedRole: (role) => set({ selectedRole: role }),
  setAiConfig: (config) =>
    set((state) => ({ aiConfig: { ...state.aiConfig, ...config } })),
  setStatus: (s) => set({ status: s }),

  fetchBoards: async () => {
    try {
      const { boards } = await api.fetchBoards();
      set({
        boards,
        selectedBoardId: boards.find((b) => b.id === "expert_mech_psychic")?.id ?? boards[0]?.id ?? "",
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
      const humanRole = board.roles.some((r) => r.role === "seer") ? "seer" : "psychic";
      const result = await api.createGame({
        board_id: board.id,
        difficulty,
        human_name: "你",
        human_role: get().selectedRole || humanRole,
        ai: aiConfig,
      });
      set({ game: result, gameId: result.game.game_id, status: "身份已发放" });
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

  // ---- 夜晚 ----

  startNight: async () => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.startNight(gameId);
      set({ game: result, status: "进入夜晚" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "夜晚开始失败" });
    } finally {
      set({ loading: false });
    }
  },

  submitNightAction: async (actionType, targetSeat, secondTargetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.submitNightAction(gameId, actionType, targetSeat, secondTargetSeat);
      set({ game: result, status: "夜间行动已提交" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "夜间行动失败" });
    } finally {
      set({ loading: false });
    }
  },

  // ---- 白天 ----

  startDay: async () => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.startDay(gameId);
      set({ game: result, status: "进入白天" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "白天开始失败" });
    } finally {
      set({ loading: false });
    }
  },

  continueDay: async () => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.continueDay(gameId);
      set({ game: result, status: "进入发言阶段" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "继续失败" });
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
      set({ game: result, status: "发言已发送" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "发言失败" });
    } finally {
      set({ loading: false });
    }
  },

  submitVote: async (targetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.submitVote(gameId, targetSeat);
      set({ game: result, status: "投票已提交" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "投票失败" });
    } finally {
      set({ loading: false });
    }
  },

  resolveVotes: async () => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.resolveVotes(gameId);
      set({ game: result, status: "投票已结算" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "结算失败" });
    } finally {
      set({ loading: false });
    }
  },

  startVote: async () => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.startVote(gameId);
      set({ game: result, status: "进入投票阶段" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "切换失败" });
    } finally {
      set({ loading: false });
    }
  },

  // ---- 特殊行动 ----

  selfExplode: async (targetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.selfExplode(gameId, targetSeat);
      set({ game: result, status: "自爆" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "自爆失败" });
    } finally {
      set({ loading: false });
    }
  },

  hunterShoot: async (targetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.hunterShoot(gameId, targetSeat);
      set({ game: result, status: "猎人开枪" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "开枪失败" });
    } finally {
      set({ loading: false });
    }
  },

  knightDuel: async (targetSeat) => {
    const { gameId } = get();
    if (!gameId) return;
    set({ loading: true });
    try {
      const result = await api.knightDuel(gameId, targetSeat);
      set({ game: result, status: "骑士决斗" });
    } catch (err) {
      set({ status: err instanceof Error ? err.message : "决斗失败" });
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
