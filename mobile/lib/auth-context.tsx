/**
 * Global auth state — who's logged in, and the login/register/logout
 * actions every screen needs. Boots by checking secure storage for an
 * existing access token and calling GET /auth/me to validate it, so a
 * relaunch of the app doesn't force a fresh login every time.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { authApi, getAccessToken, getRefreshToken } from "./api";
import type { User } from "./api";

type AuthState = {
  user: User | null;
  isLoading: boolean; // true only during the initial boot check
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    confirm_password: string;
    firstname: string;
    lastname: string;
    pseudo: string;
    date_of_birth: string;
    school_name?: string | null;
  }) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        setUser(await authApi.me());
      } catch {
        // Stored token is invalid/expired past what apiRequest's one-shot
        // refresh could recover — treat as logged out rather than looping.
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setUser(await authApi.login(email, password));
  }, []);

  const register = useCallback(
    async (input: {
      email: string;
      password: string;
      confirm_password: string;
      firstname: string;
      lastname: string;
      pseudo: string;
      date_of_birth: string;
      school_name?: string | null;
    }) => {
      await authApi.register(input);
      await authApi.login(input.email, input.password).then(setUser);
    },
    []
  );

  const logout = useCallback(async () => {
    const refreshToken = await getRefreshToken();
    if (refreshToken) await authApi.logout(refreshToken);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout }),
    [user, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside an <AuthProvider>.");
  return ctx;
}
