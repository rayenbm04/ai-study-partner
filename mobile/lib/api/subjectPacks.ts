import { apiRequest } from "./client";
import type { AppliedSubjectPack, SubjectPackApplyResult, SubjectPackRemoveResult } from "./types";

export async function listAppliedPacks(): Promise<AppliedSubjectPack[]> {
  return apiRequest<AppliedSubjectPack[]>("/api/v1/subject-packs");
}

export async function applyPack(input: {
  academicLevelId: string;
  sectionId?: string | null;
}): Promise<SubjectPackApplyResult> {
  return apiRequest<SubjectPackApplyResult>("/api/v1/subject-packs/apply", {
    method: "POST",
    body: { academic_level_id: input.academicLevelId, section_id: input.sectionId ?? null },
  });
}

export async function removePack(input: {
  academicLevelId: string;
  sectionId?: string | null;
}): Promise<SubjectPackRemoveResult> {
  return apiRequest<SubjectPackRemoveResult>("/api/v1/subject-packs/remove", {
    method: "POST",
    body: { academic_level_id: input.academicLevelId, section_id: input.sectionId ?? null },
  });
}
