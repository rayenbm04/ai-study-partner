import { apiRequest } from "./client";

/** Wipes every subject, document, quiz, flashcard, and progress record for
 * the current user — but not the account/login itself (see
 * app/services/account_service.py for exactly what's deleted). */
export async function resetAccount(): Promise<void> {
  return apiRequest<void>("/api/v1/account/reset", { method: "POST" });
}
