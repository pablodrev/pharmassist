import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  apiClient,
  getStoredToken,
  setOnUnauthorized,
  setStoredToken,
} from "../api/client";
import type { components } from "../api/schema";

export type User = components["schemas"]["UserResponse"];
export type UserRole = components["schemas"]["UserRole"];

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setOnUnauthorized(() => logout());
    return () => setOnUnauthorized(null);
  }, [logout]);

  // Restore session on mount
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient
      .GET("/api/v1/auth/users/me")
      .then(({ data, error }) => {
        if (data && !error) setUser(data);
        else setStoredToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data, error } = await apiClient.POST("/api/v1/auth/login", {
      body: { email, password },
    });
    if (error || !data) {
      throw new Error(extractError(error) ?? "Не удалось войти");
    }
    setStoredToken(data.access_token);
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const { data, error } = await apiClient.POST("/api/v1/auth/register", {
        body: {
          email,
          password,
          full_name: fullName,
          role: "reporter" as UserRole,
        },
      });
      if (error || !data) {
        throw new Error(extractError(error) ?? "Не удалось зарегистрироваться");
      }
      setStoredToken(data.access_token);
      setUser(data.user);
    },
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

function extractError(err: unknown): string | null {
  if (!err) return null;
  if (typeof err === "string") return err;
  if (typeof err === "object" && err !== null) {
    const detail = (err as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg;
    }
  }
  return null;
}
