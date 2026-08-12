import { apiRequest } from "./client";
import type { Subject } from "./types";

export async function listSubjects(): Promise<Subject[]> {
  return apiRequest<Subject[]>("/api/v1/subjects");
}

export async function createSubject(input: {
  name: string;
  description?: string | null;
  color?: string | null;
  icon?: string | null;
}): Promise<Subject> {
  return apiRequest<Subject>("/api/v1/subjects", { method: "POST", body: input });
}

export async function getSubject(subjectId: string): Promise<Subject> {
  return apiRequest<Subject>(`/api/v1/subjects/${subjectId}`);
}

export async function archiveSubject(subjectId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/subjects/${subjectId}`, { method: "DELETE" });
}
