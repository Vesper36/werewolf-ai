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

export async function resolveNight(gameId: string, targetSeat: number | null) {
  return request<GameResponse>(`/api/games/${gameId}/night`, {
    method: "POST",
    body: JSON.stringify({ target_seat: targetSeat }),
  });
}

export async function runAiSpeeches(gameId: string) {
  return request<GameResponse>(`/api/games/${gameId}/ai-speeches`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function submitSpeech(gameId: string, text: string) {
  return request<GameResponse>(`/api/games/${gameId}/speech`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function resolveVote(gameId: string, targetSeat: number) {
  return request<GameResponse>(`/api/games/${gameId}/vote`, {
    method: "POST",
    body: JSON.stringify({ target_seat: targetSeat }),
  });
}
