import { apiRequest } from "./client";
import type { Conversation, Message } from "./types";

export async function sendMessage(
  subjectId: string,
  input: { question: string; conversation_id?: string | null }
): Promise<{ conversation_id: string; user_message: Message; assistant_message: Message }> {
  return apiRequest(`/api/v1/subjects/${subjectId}/chat`, { method: "POST", body: input });
}

export async function listConversations(subjectId: string): Promise<Conversation[]> {
  return apiRequest<Conversation[]>(`/api/v1/subjects/${subjectId}/conversations`);
}

export async function listMessages(conversationId: string): Promise<Message[]> {
  return apiRequest<Message[]>(`/api/v1/conversations/${conversationId}/messages`);
}
