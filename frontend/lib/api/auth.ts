import { apiRequest, clearTokens, storeTokens } from "./client";
import type { TokenPair, User } from "./types";

export async function register(input: {
  email: string;
  password: string;
  confirm_password: string;
  firstname: string;
  lastname: string;
  pseudo: string;
  date_of_birth: string;
  school_id?: string | null;
}): Promise<User> {
  return apiRequest<User>("/api/v1/auth/register", { method: "POST", body: input, auth: false });
}

/** Logs in and persists the token pair to storage — callers don't need to
 * touch storeTokens() themselves. */
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

export async function verifyEmail(token: string): Promise<User> {
  return apiRequest<User>("/api/v1/auth/verify-email", { method: "POST", body: { token }, auth: false });
}

/** Always resolves (even for an unknown email) — the backend deliberately
 * doesn't reveal whether an account exists, so there's nothing to branch on
 * here besides a network/validation failure. */
export async function forgotPassword(email: string): Promise<void> {
  return apiRequest<void>("/api/v1/auth/forgot-password", { method: "POST", body: { email }, auth: false });
}

export async function resetPassword(input: {
  token: string;
  new_password: string;
  confirm_new_password: string;
}): Promise<void> {
  return apiRequest<void>("/api/v1/auth/reset-password", { method: "POST", body: input, auth: false });
}
