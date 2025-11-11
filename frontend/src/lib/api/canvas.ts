import { getApiBase } from "./common";

export type PixelData = {
  x: number;
  y: number;
  color: string;
  timestamp?: number;
  userId?: string;
};

export type CanvasState = {
  canvas_width: number;
  canvas_height: number;
  pixels: Record<string, PixelData>;
};

export class CanvasAPIError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = "CanvasAPIError";
  }
}

class CanvasAPI {
  private get baseUrl() {
    return getApiBase();
  }

  async getCanvas(): Promise<CanvasState> {
    const res = await fetch(`${this.baseUrl}/canvas`);
    if (!res.ok) {
      throw new CanvasAPIError("Failed to fetch canvas", res.status);
    }
    return await res.json();
  }

  async placePixel(x: number, y: number, color: string): Promise<PixelData> {
    const res = await fetch(`${this.baseUrl}/canvas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ x, y, color }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new CanvasAPIError(text || "Failed to place pixel", res.status);
    }

    return await res.json();
  }

  createWebSocket(): WebSocket {
    const baseUrl = this.baseUrl;
    const wsUrl = baseUrl.startsWith("http")
      ? baseUrl.replace(/^http/, "ws") + "/ws"
      : baseUrl + "/ws";
    
    return new WebSocket(wsUrl);
  }
}

export const canvasApi = new CanvasAPI();
