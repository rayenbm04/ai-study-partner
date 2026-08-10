import { apiRequest } from "./client";
import type { User } from "./types";

/** Wipes every subject, document, quiz, flashcard, and progress record for
 * the current user — but not the account/login itself (see
 * app/services/account_service.py for exactly what's deleted). */
export async function resetAccount(): Promise<void> {
  return apiRequest<void>("/api/v1/account/reset", { method: "POST" });
}

/** Sets (or clears, when both are null) the student's own academic level and
 * section — separate from applying a subject pack, which uses the same ids
 * to decide which curriculum subjects to add but doesn't remember them as
 * *the student's own* level (see backend/app/services/account_service.py). */
export async function setClasse(input: {
  academicLevelId: string | null;
  sectionId: string | null;
}): Promise<User> {
  return apiRequest<User>("/api/v1/account/classe", {
    method: "PATCH",
    body: { academic_level_id: input.academicLevelId, section_id: input.sectionId },
  });
}
