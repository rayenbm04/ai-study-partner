"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { authApi, getAccessToken, getRefreshToken, type User } from "@/lib/api";

type AuthContextValue = {
  user: User | null;
  /** True while the initial "am I already logged in" check is running. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    confirm_password: string;
    firstname: string;
    lastname: string;
    pseudo: string;
    date_of_birth: string;
    school_id?: string | null;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) {
      setUser(null);
      return;
    }
    try {
      setUser(await authApi.me());
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    async function boot() {
      await refreshUser();
      setIsLoading(false);
    }
    void boot();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const loggedInUser = await authApi.login(email, password);
    setUser(loggedInUser);
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
      school_id?: string | null;
    }) => {
      await authApi.register(input);
      setUser(await authApi.login(input.email, input.password));
    },
    []
  );

  const logout = useCallback(async () => {
    const refreshToken = await getRefreshToken();
    if (refreshToken) await authApi.logout(refreshToken);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
