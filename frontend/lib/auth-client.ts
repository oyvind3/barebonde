/**
 * Better Auth client wrapper
 * Provides session management and authentication
 */

import axios, { AxiosInstance } from "axios";

interface UserData {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
}

interface SessionData {
  user: UserData;
  session_token: string;
  token_type: "bearer";
}

interface AuthError {
  message: string;
  code?: string;
}

class AuthClient {
  private apiClient: AxiosInstance;
  private sessionToken: string | null = null;

  constructor(apiBaseURL: string = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") {
    this.apiClient = axios.create({
      baseURL: `${apiBaseURL}/api`,
    });

    // Load session token from localStorage if available
    if (typeof window !== "undefined") {
      this.sessionToken = localStorage.getItem("session_token");
      if (this.sessionToken) {
        this.setAuthHeader(this.sessionToken);
      }
    }
  }

  private setAuthHeader(token: string) {
    this.apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  }

  /**
   * Get login URL from backend
   * This would typically redirect to better-auth.com hosted login
   */
  async getLoginUrl(): Promise<{ login_url: string }> {
    try {
      const response = await this.apiClient.get("/auth/login");
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Handle callback after authentication
   * Called when user redirects back from better-auth.com
   */
  async handleCallback(sessionToken: string): Promise<SessionData> {
    try {
      const response = await this.apiClient.post("/auth/callback", {
        session_token: sessionToken,
      });

      const data = response.data as SessionData;
      this.sessionToken = sessionToken;

      // Save session token to localStorage
      if (typeof window !== "undefined") {
        localStorage.setItem("session_token", sessionToken);
      }

      this.setAuthHeader(sessionToken);
      return data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * Verify current session
   */
  async verifySession(): Promise<SessionData | null> {
    if (!this.sessionToken) {
      return null;
    }

    try {
      const response = await this.apiClient.post("/auth/verify");
      return response.data;
    } catch (error) {
      // Session invalid, clear it
      this.logout();
      return null;
    }
  }

  /**
   * Get current user (requires active session)
   */
  async getCurrentUser(): Promise<UserData | null> {
    if (!this.sessionToken) {
      return null;
    }

    try {
      const response = await this.apiClient.get("/auth/verify");
      return response.data.user;
    } catch (error) {
      return null;
    }
  }

  /**
   * Logout and clear session
   */
  async logout(): Promise<void> {
    try {
      if (this.sessionToken) {
        await this.apiClient.post("/auth/logout");
      }
    } catch (error) {
      // Even if logout fails, clear local session
      console.error("Logout error:", error);
    } finally {
      this.sessionToken = null;
      if (typeof window !== "undefined") {
        localStorage.removeItem("session_token");
      }
      delete this.apiClient.defaults.headers.common["Authorization"];
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.sessionToken !== null;
  }

  /**
   * Get current session token
   */
  getSessionToken(): string | null {
    return this.sessionToken;
  }

  /**
   * Handle API errors and return user-friendly messages
   */
  private handleError(error: any): AuthError {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const data = error.response?.data as any;

      switch (status) {
        case 400:
          return {
            message: data?.detail || "Invalid request",
            code: "INVALID_REQUEST",
          };
        case 401:
          return {
            message: "Authentication required. Please log in again.",
            code: "UNAUTHORIZED",
          };
        case 403:
          return {
            message: "You don't have permission to access this resource",
            code: "FORBIDDEN",
          };
        case 404:
          return {
            message: "Resource not found",
            code: "NOT_FOUND",
          };
        case 500:
          return {
            message: "Server error. Please try again later.",
            code: "SERVER_ERROR",
          };
        default:
          return {
            message: data?.detail || error.message || "An error occurred",
            code: "UNKNOWN_ERROR",
          };
      }
    }

    return {
      message: "An unexpected error occurred",
      code: "UNKNOWN_ERROR",
    };
  }
}

// Create singleton instance
export const authClient = new AuthClient();

export type { UserData, SessionData, AuthError };
