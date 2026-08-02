import { apiRequest } from "./client";
import type { Document } from "./types";

export async function listDocuments(subjectId: string): Promise<Document[]> {
  return apiRequest<Document[]>(`/api/v1/subjects/${subjectId}/documents`);
}

export async function getDocument(documentId: string): Promise<Document> {
  return apiRequest<Document>(`/api/v1/documents/${documentId}`);
}

// Upload isn't wired up yet — needs a multipart/form-data request via
// expo-document-picker + FormData, which is its own follow-up piece of
// work rather than something to bolt on here.
