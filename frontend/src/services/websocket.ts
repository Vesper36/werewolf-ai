import type { GameResponse } from "@/types/game";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE ??
  (process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000")
    .replace(/^http/, "ws");

type MessageHandler = (msg: { type: string; data: GameResponse }) => void;

class GameSocket {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private gameId: string | null = null;
  private _connected = false;

  get connected() {
    return this._connected;
  }

  connect(gameId: string) {
    if (this.ws && this.gameId === gameId && this.ws.readyState < 2) {
      return;
    }
    this.disconnect();
    this.gameId = gameId;

    const url = `${WS_BASE}/ws/game/${gameId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._connected = true;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "pong") return;
        this.handlers.forEach((h) => h(msg));
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      this.stopHeartbeat();
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this._connected = false;
    };
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      if (this.ws.readyState < 2) {
        this.ws.close();
      }
      this.ws = null;
    }
    this._connected = false;
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.reconnectTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send("ping");
      }
    }, 25000) as unknown as ReturnType<typeof setTimeout>;
  }

  private stopHeartbeat() {
    if (this.reconnectTimer) {
      clearInterval(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private scheduleReconnect() {
    if (!this.gameId) return;
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.gameId!);
    }, 3000) as unknown as ReturnType<typeof setTimeout>;
  }
}

export const gameSocket = new GameSocket();
