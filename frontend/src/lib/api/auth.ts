import { getApiBase, fetchWithAuth } from "./common";

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
  private _pendingRequests = new Map<string, Promise<string | null>>();

  private get baseUrl() {
    return getApiBase();
  }

  private async handleResponse(res: Response, errorMsg: string) {
    const data = await res.json();
    if (!res.ok) {
      let message = data.detail || errorMsg;
      
      // Handle pydantic validation errors
      if (Array.isArray(message) && message.length > 0 && typeof message[0] === 'object') {
        message = message.map((err: any) => err.msg).join(", ");
      } else if (typeof message === 'object') {
        message = JSON.stringify(message);
      }

      throw new AuthAPIError(message, res.status);
    }
    return data;
  }

  async register(email: string, username: string, password: string): Promise<RegisterResponse> {
    const res = await fetch(`${this.baseUrl}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });

    return this.handleResponse(res, "Registration failed");
  }

  async verify(email: string, code: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/auth/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, code }),
    });

    return this.handleResponse(res, "Verification failed");
  }

  async login(email: string, password: string): Promise<LoginResponse> {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    return this.handleResponse(res, "Login failed");
  }

  async logout(): Promise<void> {
    const res = await fetchWithAuth(`${this.baseUrl}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    if (!res.ok && res.status !== 401) {
        // Ignore 401 on logout
        throw new AuthAPIError("Logout failed", res.status);
    }
  }

  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const res = await fetchWithAuth(`${this.baseUrl}/auth/me`, {
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

    if (this._pendingRequests.has(userId)) {
      return this._pendingRequests.get(userId)!;
    }

    const promise = this.getUserById(userId).then(res => {
      this._pendingRequests.delete(userId);
      if (res) {
        this._usernameCache.set(userId, res.username);
        return res.username;
      }
      return null;
    });
    
    this._pendingRequests.set(userId, promise);
    return promise;
  }
}

export const authApi = new AuthAPI();
