import { apiRequest, clearTokens, storeTokens } from "./client";
import type { TokenPair, User } from "./types";

export async function register(input: {
  email: string;
  password: string;
  firstname: string;
  lastname: string;
}): Promise<User> {
  return apiRequest<User>("/api/v1/auth/register", { method: "POST", body: input, auth: false });
}

/** Logs in and persists the token pair to secure storage — callers don't
 * need to touch storeTokens() themselves. */
export async function login(email: string, password: string): Promise<User> {
  const tokens = await apiRequest<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  await storeTokens(tokens.access_token, tokens.refresh_token);
  return me();
}

export async function me(): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me");
}

export async function logout(refreshToken: string): Promise<void> {
  try {
    await apiRequest<void>("/api/v1/auth/logout", { method: "POST", body: { refresh_token: refreshToken } });
  } finally {
    await clearTokens();
  }
}
