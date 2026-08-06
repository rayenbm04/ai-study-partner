import { apiRequest } from "./client";
import type { AcademicLevel, Country, CurriculumSubject, EducationSystem, Section } from "./types";

export async function listCountries(): Promise<Country[]> {
  return apiRequest<Country[]>("/api/v1/curriculum/countries");
}

export async function listEducationSystems(countryId: string): Promise<EducationSystem[]> {
  return apiRequest<EducationSystem[]>(`/api/v1/curriculum/countries/${countryId}/education-systems`);
}

export async function listAcademicLevels(educationSystemId: string): Promise<AcademicLevel[]> {
  return apiRequest<AcademicLevel[]>(`/api/v1/curriculum/education-systems/${educationSystemId}/academic-levels`);
}

export async function listSections(academicLevelId: string): Promise<Section[]> {
  return apiRequest<Section[]>(`/api/v1/curriculum/academic-levels/${academicLevelId}/sections`);
}

export async function listCurriculumSubjects(
  academicLevelId: string,
  sectionId?: string | null
): Promise<CurriculumSubject[]> {
  const query = sectionId ? `?section_id=${sectionId}` : "";
  return apiRequest<CurriculumSubject[]>(`/api/v1/curriculum/academic-levels/${academicLevelId}/subjects${query}`);
}
