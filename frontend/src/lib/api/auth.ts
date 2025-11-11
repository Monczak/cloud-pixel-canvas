import { getApiBase } from "./common";

export type AuthUser = {
    user_id: string;
    email: string;
    username: string;
}

export type RegisterResponse = {
  requires_verification: boolean;
  user_id: string;
};

export type LoginResponse = {
  user: AuthUser;
};

export class AuthAPIError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = "AuthAPIError";
  }
}

class AuthAPI {
  private _usernameCache = new Map<string, string>();

  private get baseUrl() {
    return getApiBase();
  }

  async register(email: string, username: string, password: string): Promise<RegisterResponse> {
    const res = await fetch(`${this.baseUrl}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new AuthAPIError(data.detail || "Registration failed", res.status);
    }

    return data;
  }

  async verify(email: string, code: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, code }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new AuthAPIError(data.detail || "Verification failed", res.status);
    }
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new AuthAPIError(data.detail || "Login failed", res.status);
    }

    return data;
  }

  async logout(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    if (!res.ok) {
      throw new AuthAPIError("Logout failed", res.status);
    }
  }

  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const res = await fetch(`${this.baseUrl}/auth/me`, {
        credentials: "include",
      });

      if (res.status === 401) {
        return null;
      }

      if (!res.ok) {
        throw new AuthAPIError("Failed to fetch user", res.status);
      }

      const data = await res.json();
      return {
        user_id: data.user_id,
        email: data.email,
        username: data.username,
      };
    } catch (err) {
      console.error("Failed to fetch current user:", err);
      return null;
    }
  }

  async getUserById(userId: string): Promise<{ username: string } | null> {
    try {
      const res = await fetch(`${this.baseUrl}/auth/user/${userId}`);
      if (!res.ok) return null;
      return await res.json();
    } catch (err) {
      console.error("Failed to fetch user:", err);
      return null;
    }
  }

  async getUsernameById(userId: string): Promise<string | null> {
    if (this._usernameCache.has(userId)) {
        return this._usernameCache.get(userId)!;
    }
    
    const res = await this.getUserById(userId);
    if (!res) return null;

    this._usernameCache.set(userId, res.username);
    return res.username;
  }
}

export const authApi = new AuthAPI();
