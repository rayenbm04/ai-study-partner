import { apiRequest } from "./client";
import type { ConceptMastery, WeakConcept } from "./types";

export async function getProgress(subjectId: string): Promise<ConceptMastery[]> {
  return apiRequest<ConceptMastery[]>(`/api/v1/subjects/${subjectId}/progress`);
}

export async function getWeakConcepts(subjectId: string): Promise<WeakConcept[]> {
  return apiRequest<WeakConcept[]>(`/api/v1/subjects/${subjectId}/weak-concepts`);
}
