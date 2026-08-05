import * as DocumentPicker from "expo-document-picker";
import { Platform } from "react-native";

import { apiUpload, apiRequest } from "./client";
import type { Document } from "./types";

export async function listDocuments(subjectId: string): Promise<Document[]> {
  return apiRequest<Document[]>(`/api/v1/subjects/${subjectId}/documents`);
}

export async function getDocument(documentId: string): Promise<Document> {
  return apiRequest<Document>(`/api/v1/documents/${documentId}`);
}

export type PickedDocument = {
  uri: string;
  name: string;
  mimeType: string | null;
};

/** Opens the OS file picker. No MIME allowlist — the backend already
 * validates supported extensions and returns a clear 415 for anything else
 * (see app/services/knowledge_base/extractors/registry.py), so filtering
 * here would only risk hiding a valid file behind an unreliable
 * OS-reported MIME type. Returns null if the user canceled. */
export async function pickDocument(): Promise<PickedDocument | null> {
  const result = await DocumentPicker.getDocumentAsync({ type: "*/*" });
  if (result.canceled || !result.assets?.length) return null;
  const asset = result.assets[0];
  return { uri: asset.uri, name: asset.name, mimeType: asset.mimeType ?? null };
}

export async function uploadDocument(subjectId: string, file: PickedDocument): Promise<Document> {
  const formData = new FormData();
  if (Platform.OS === "web") {
    // On web, `file.uri` is a blob: URL and fetch()/FormData are the real
    // browser APIs — appending a plain {uri,name,type} object here would
    // silently coerce to the string "[object Object]" instead of a file, so
    // the blob has to be fetched back out and appended for real.
    const blob = await (await fetch(file.uri)).blob();
    formData.append("file", blob, file.name);
  } else {
    // On native, RN's networking layer recognizes this {uri, name, type}
    // shape specially and streams the file straight from `uri` — no manual
    // read into memory needed.
    formData.append("file", {
      uri: file.uri,
      name: file.name,
      type: file.mimeType ?? "application/octet-stream",
    } as unknown as Blob);
  }
  return apiUpload<Document>(`/api/v1/subjects/${subjectId}/documents`, formData);
}
