import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { setUnauthorizedHandler, tokenStore } from "@/shared/lib/api";
import { authApi } from "@/modules/automl/api/automl-api";
import type { UserOut } from "@/modules/automl/api/types";

interface AuthState {
  user: UserOut | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      tokenStore.clear();
      setUser(null);
      navigate("/login");
    });
  }, [navigate]);

  useEffect(() => {
    const tok = tokenStore.get();
    if (!tok) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then((u) => setUser(u))
      .catch(() => {
        tokenStore.clear();
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const tok = await authApi.login({ email, password });
    tokenStore.set(tok.access_token);
    tokenStore.setEmail(email);
    const me = await authApi.me();
    setUser(me);
  };

  const register = async (email: string, password: string, fullName?: string) => {
    await authApi.register({ email, password, full_name: fullName ?? null });
    await login(email, password);
  };

  const logout = () => {
    tokenStore.clear();
    setUser(null);
    navigate("/login");
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const v = useContext(AuthContext);
  if (!v) throw new Error("useAuth must be used inside <AuthProvider>");
  return v;
}
