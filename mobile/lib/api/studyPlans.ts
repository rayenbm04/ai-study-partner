import { apiRequest } from "./client";
import type { StudyPlan, StudyPlanItem } from "./types";

export async function generateStudyPlan(input: {
  name: string;
  subject_ids: string[];
  exam_date?: string | null; // "YYYY-MM-DD"
  daily_minutes_available: number;
}): Promise<StudyPlan> {
  return apiRequest<StudyPlan>("/api/v1/study-plans", { method: "POST", body: input });
}

export async function getStudyPlan(studyPlanId: string): Promise<StudyPlan> {
  return apiRequest<StudyPlan>(`/api/v1/study-plans/${studyPlanId}`);
}

export async function updateStudyPlanItemStatus(
  itemId: string,
  status: StudyPlanItem["status"]
): Promise<StudyPlanItem> {
  return apiRequest<StudyPlanItem>(`/api/v1/study-plan-items/${itemId}`, { method: "PATCH", body: { status } });
}
