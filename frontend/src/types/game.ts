export type Difficulty = "novice" | "basic" | "advanced" | "expert";

export type AIConfig = {
  provider: string;
  base_url: string;
  api_key: string;
  model: string;
  temperature: number;
  timeout_seconds: number;
};

export type TTSConfig = {
  provider: string;
  model: string;
  voice: string;
  speed: number;
  enabled: boolean;
  sttEnabled: boolean;
};

export type Board = {
  id: string;
  name: string;
  description: string;
  player_count: number;
  has_police: boolean;
  difficulty: Difficulty[];
  roles: { role: string; name: string; pool: string }[];
  role_counts: Record<string, number>;
  night_order: string[];
  special_rules: Record<string, unknown>;
};

export type Player = {
  id: string;
  seat_number: number;
  name: string;
  is_human: boolean;
  is_alive: boolean;
  is_sheriff: boolean;
  is_revealed_idiot: boolean;
  role?: string;
  role_name?: string;
  faction?: string;
};

export type Speech = {
  player_id: string;
  seat_number: number;
  name: string;
  text: string;
  phase: string;
  day_number: number;
  timestamp: number;
  typing_cps: number;
};

export type VoteRecord = {
  voter_seat: number;
  target_seat: number;
  weight: number;
};

export type TimelineItem = {
  type: string;
  text: string;
  player_id?: string;
};

export type AgentInfo = {
  player_id: string;
  seat_number: number;
  thread_id: string;
  personality: string;
  memory_items: number;
  private_note_items: number;
  api_failures: number;
  known_teammate_seats: number[];
};

export type LastCheck = {
  target_seat: number;
  result: "good" | "wolf";
  role?: string | null;
};

export type GameResponse = {
  game: {
    game_id: string;
    board_id: string;
    difficulty: Difficulty;
    phase: string;
    day_number: number;
    is_first_night: boolean;
    sheriff_id: string | null;
    winner: string | null;
  };
  board: Board;
  phase_label: string;
  human: Player | null;
  players: Player[];
  timeline: TimelineItem[];
  speeches: Speech[];
  votes: VoteRecord[];
  last_check: LastCheck | null;
  agents: AgentInfo[];
  provider: {
    provider: string;
    base_url: string;
    model: string;
    temperature: number;
    has_api_key: boolean;
  };
  new_speeches?: Speech[];
  pending_human_prompt?: string | null;
  pending_human_action_type?: string | null;
};
