import { apiRequest } from "./client";
import type { Summary, SummaryType } from "./types";

/** Generating always (re)runs the LLM and caches the result — it's an
 * explicit, user-triggered action, not something recomputed on every read.
 * Use getCachedSummary to read back a previously generated one without
 * paying for another generation. */
export async function generateSummary(
  subjectId: string,
  input: { document_id: string; summary_type: SummaryType }
): Promise<Summary> {
  return apiRequest<Summary>(`/api/v1/subjects/${subjectId}/summaries`, { method: "POST", body: input });
}

export async function getCachedSummary(documentId: string, summaryType: SummaryType): Promise<Summary> {
  return apiRequest<Summary>(`/api/v1/documents/${documentId}/summary?summary_type=${summaryType}`);
}
