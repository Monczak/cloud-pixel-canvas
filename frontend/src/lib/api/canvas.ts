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

export type Snapshot = {
  snapshot_id: string;
  image_url: string;
  thumbnail_url: string;
  canvas_width: number;
  canvas_height: number;
  created_at: string;
};

export type SnapshotListResponse = {
  snapshots: Snapshot[];
  total: number;
  limit: number;
  offset: number;
}

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

  async getSnapshots(limit: number = 20, offset: number = 0): Promise<SnapshotListResponse> {
    const res = await fetch(
      `${this.baseUrl}/canvas/snapshot?limit=${limit}&offset=${offset}`
    );

    if (!res.ok) {
      throw new CanvasAPIError("Failed to fetch snapshots", res.status);
    }

    return await res.json();
  }

  async overwriteWithImage(file: File): Promise<{ message: string; pixels_updated: number }> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${this.baseUrl}/canvas/overwrite`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new CanvasAPIError(text || "Failed to upload image", res.status);
    }

    return await res.json();
  }

  getDownloadUrl(snapshotId: string): string {
    return `${this.baseUrl}/canvas/snapshot/${snapshotId}/download`;
  }
}

export const canvasApi = new CanvasAPI();
