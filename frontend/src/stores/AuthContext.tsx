import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { api, tokenStore, User } from "../services/apiClient";

interface AuthResult {
  access_token: string;
  refresh_token: string;
  user: User;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, phone: string, password: string) => Promise<void>;
  completeOAuth: (access: string, refresh: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!tokenStore.access && !tokenStore.refresh) {
      setLoading(false);
      return;
    }
    try {
      setUser(await api<User>("/auth/me"));
    } catch {
      tokenStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const applyResult = (result: AuthResult) => {
    tokenStore.set(result.access_token, result.refresh_token);
    setUser(result.user);
  };

  const login = async (email: string, password: string) => {
    applyResult(await api<AuthResult>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }));
  };

  const register = async (fullName: string, email: string, phone: string, password: string) => {
    applyResult(
      await api<AuthResult>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ full_name: fullName, email, phone: phone || null, password }),
      })
    );
  };

  const completeOAuth = async (access: string, refresh: string) => {
    tokenStore.set(access, refresh);
    setUser(await api<User>("/auth/me"));
  };

  const logout = async () => {
    const refresh = tokenStore.refresh;
    if (refresh) await api("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: refresh }) }).catch(() => {});
    tokenStore.clear();
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, register, completeOAuth, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
