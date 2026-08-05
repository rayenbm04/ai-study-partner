import * as DocumentPicker from "expo-document-picker";
import { Directory, File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Platform } from "react-native";

import { apiUpload, apiRequest, apiUrl, getAccessToken } from "./client";
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

export async function deleteDocument(documentId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/documents/${documentId}`, { method: "DELETE" });
}

/** Opens a document's actual content — not an in-app renderer (that would
 * need a native PDF library and a custom dev build, and still couldn't
 * render DOCX/PPTX/XLSX anyway), but handing the file to whatever the OS
 * already opens it with: a new browser tab on web, the native share/preview
 * sheet on iOS/Android. Every file type the backend supports "just works"
 * this way, not just PDFs/images. */
export async function previewDocument(document: Document): Promise<void> {
  const url = apiUrl(`/api/v1/documents/${document.id}/content`);
  const token = await getAccessToken();

  if (Platform.OS === "web") {
    // window.open() has to happen synchronously (no fetch/blob step first) —
    // confirmed by hand that Chrome's popup blocker silently rejects
    // window.open() called after any async round-trip, even a plain
    // window.open("", "_blank") pre-opened synchronously and navigated
    // later. A plain navigation can't attach an Authorization header, so the
    // token rides along as a query param instead — the backend's
    // get_current_user_from_header_or_query accepts it there for exactly
    // this route. Short-lived (ACCESS_TOKEN_EXPIRE_MINUTES) and scoped to
    // this user's own resources, the standard trade-off signed URLs make.
    const previewUrl = token ? `${url}?token=${encodeURIComponent(token)}` : url;
    window.open(previewUrl, "_blank");
    return;
  }

  const file = await File.downloadFileAsync(url, new Directory(Paths.cache), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    idempotent: true,
  });
  await Sharing.shareAsync(file.uri);
}
