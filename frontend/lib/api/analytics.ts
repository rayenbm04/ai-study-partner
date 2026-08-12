import { apiRequest } from "./client";
import type { OverviewAnalytics, SubjectAnalytics } from "./types";

export async function getOverview(): Promise<OverviewAnalytics> {
  return apiRequest<OverviewAnalytics>("/api/v1/analytics/overview");
}

export async function getSubjectAnalytics(subjectId: string): Promise<SubjectAnalytics> {
  return apiRequest<SubjectAnalytics>(`/api/v1/analytics/subjects/${subjectId}`);
}
