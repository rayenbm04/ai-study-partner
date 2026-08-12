import { apiRequest } from "./client";
import type { Flashcard } from "./types";

export async function listFlashcardsForSubject(subjectId: string): Promise<Flashcard[]> {
  return apiRequest<Flashcard[]>(`/api/v1/subjects/${subjectId}/flashcards`);
}

/** Cross-subject — every card due for review right now, regardless of which
 * subject it belongs to (matches GET /flashcards/due on the backend). */
export async function listDueFlashcards(): Promise<Flashcard[]> {
  return apiRequest<Flashcard[]>("/api/v1/flashcards/due");
}

export async function reviewFlashcard(flashcardId: string, quality: number): Promise<Flashcard["review"]> {
  return apiRequest(`/api/v1/flashcards/${flashcardId}/review`, { method: "POST", body: { quality } });
}
