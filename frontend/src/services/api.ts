import type { AIConfig, Board, Difficulty, GameResponse } from "@/types/game";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `请求失败 ${response.status}`);
  }
  return response.json() as Promise<T>;
}

// ---- 基础 ----

export async function fetchBoards() {
  return request<{ boards: Board[] }>("/api/boards");
}

export async function testSettings(ai: AIConfig) {
  return request<{ ok: boolean; mode: string; message: string }>("/api/settings/test", {
    method: "POST",
    body: JSON.stringify(ai),
  });
}

export async function createGame(payload: {
  board_id: string;
  difficulty: Difficulty;
  human_name: string;
  human_role: string | null;
  ai: AIConfig;
}) {
  return request<GameResponse>("/api/games", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchGame(gameId: string) {
  return request<GameResponse>(`/api/games/${gameId}`);
}

// ---- 夜晚流程 ----

export async function startNight(gameId: string) {
  return request<GameResponse>(`/api/games/${gameId}/night/start`, {
    method: "POST",
    body: "{}",
  });
}

export async function submitNightAction(
  gameId: string,
  actionType: string,
  targetSeat: number | null,
  secondTargetSeat?: number | null
) {
  return request<GameResponse>(`/api/games/${gameId}/night/action`, {
    method: "POST",
    body: JSON.stringify({
      action_type: actionType,
      target_seat: targetSeat,
      second_target_seat: secondTargetSeat ?? null,
    }),
  });
}

// ---- 白天流程 ----

export async function startDay(gameId: string) {
  return request<GameResponse>(`/api/games/${gameId}/day/start`, {
    method: "POST",
    body: "{}",
  });
}

export async function runAiSpeeches(gameId: string) {
  return request<GameResponse>(`/api/games/${gameId}/ai-speeches`, {
    method: "POST",
    body: "{}",
  });
}

export async function submitSpeech(gameId: string, text: string) {
  return request<GameResponse>(`/api/games/${gameId}/speech`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function submitVote(gameId: string, targetSeat: number) {
  return request<GameResponse>(`/api/games/${gameId}/vote`, {
    method: "POST",
    body: JSON.stringify({ target_seat: targetSeat }),
  });
}

export async function resolveVotes(gameId: string) {
  return request<GameResponse>(`/api/games/${gameId}/votes/resolve`, {
    method: "POST",
    body: "{}",
  });
}

// ---- 特殊行动 ----

export async function selfExplode(gameId: string, targetSeat: number | null) {
  return request<GameResponse>(`/api/games/${gameId}/self-explode`, {
    method: "POST",
    body: JSON.stringify({ target_seat: targetSeat }),
  });
}

export async function hunterShoot(gameId: string, targetSeat: number) {
  return request<GameResponse>(`/api/games/${gameId}/hunter-shoot`, {
    method: "POST",
    body: JSON.stringify({ target_seat: targetSeat }),
  });
}

export async function knightDuel(gameId: string, targetSeat: number) {
  return request<GameResponse>(`/api/games/${gameId}/knight-duel`, {
    method: "POST",
    body: JSON.stringify({ target_seat: targetSeat }),
  });
}
