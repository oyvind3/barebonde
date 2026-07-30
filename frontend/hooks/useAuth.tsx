/**
 * useAuth hook
 * Provides authentication state and functions
 */

"use client";

import { useState, useEffect, useCallback, useContext, createContext } from "react";
import { useRouter } from "next/navigation";
import { authClient, type UserData } from "@/lib/auth-client";

interface AuthContextType {
  user: UserData | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  verifySession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider component
 * Wrap your app with this to provide auth context
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  // Verify session on mount
  useEffect(() => {
    const verifySession = async () => {
      try {
        if (authClient.isAuthenticated()) {
          const currentUser = await authClient.getCurrentUser();
          if (currentUser) {
            setUser(currentUser);
          } else {
            // Token invalid, clear it
            await authClient.logout();
          }
        }
      } catch (err) {
        console.error("Error verifying session:", err);
      } finally {
        setLoading(false);
      }
    };

    verifySession();
  }, []);

  const login = useCallback(async () => {
    try {
      setError(null);
      const { login_url } = await authClient.getLoginUrl();
      // Redirect to better-auth.com login
      window.location.href = login_url;
    } catch (err: any) {
      setError(err.message || "Login failed");
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authClient.logout();
      setUser(null);
      router.push("/");
    } catch (err) {
      console.error("Logout error:", err);
    }
  }, [router]);

  const verifySession = useCallback(async (): Promise<boolean> => {
    try {
      const session = await authClient.verifySession();
      if (session?.user) {
        setUser(session.user);
        return true;
      } else {
        setUser(null);
        return false;
      }
    } catch (err) {
      console.error("Session verification error:", err);
      return false;
    }
  }, []);

  const value: AuthContextType = {
    user,
    loading,
    error,
    isAuthenticated: user !== null,
    login,
    logout,
    verifySession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * useAuth hook
 * Use in client components to access auth context
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
