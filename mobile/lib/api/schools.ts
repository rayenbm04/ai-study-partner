import { apiRequest } from "./client";
import type { School, SchoolClass } from "./types";

/** Public endpoints (no auth) — a student searches for/creates their school
 * during the registration form itself, before an account exists. See
 * backend/app/api/v1/routes/schools.py's docstring for the same reasoning. */

export async function searchSchools(query: string): Promise<School[]> {
  const q = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return apiRequest<School[]>(`/api/v1/schools${q}`, { auth: false });
}

export async function createSchool(input: { name: string; country?: string | null; city?: string | null }): Promise<School> {
  return apiRequest<School>("/api/v1/schools", { method: "POST", body: input, auth: false });
}

export async function getSchool(schoolId: string): Promise<School> {
  return apiRequest<School>(`/api/v1/schools/${schoolId}`, { auth: false });
}

export async function listSchoolClasses(schoolId: string): Promise<SchoolClass[]> {
  return apiRequest<SchoolClass[]>(`/api/v1/schools/${schoolId}/classes`, { auth: false });
}
