/**
 * AI Coach — a RAG chat scoped to one subject's documents (POST
 * /subjects/{id}/chat). Loads the most recent conversation's history if one
 * exists so returning to a subject doesn't lose context; sending a message
 * with no conversation_id yet has the backend create one.
 *
 * Optionally scoped to a single document via the `documentId` query param
 * (set when a student taps "Ask" on one of their uploads) — retrieval then
 * only searches that document instead of the whole subject, and the screen
 * starts a fresh conversation rather than resuming the subject's general one.
 */
import { ArrowUpIcon, CaretLeftIcon, FileTextIcon } from "phosphor-react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  TextInput,
  View,
} from "react-native";

import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { chatApi, documentsApi, subjectsApi } from "../../lib/api";
import type { Citation, Document, Message, Subject } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";

export default function CoachScreen() {
  const { subjectId, prompt, documentId } = useLocalSearchParams<{
    subjectId: string;
    prompt?: string;
    documentId?: string;
  }>();
  const router = useRouter();
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
  const { t } = useLanguage();
  const SUGGESTED_PROMPTS = [t("coach.promptExplain"), t("coach.promptSummarize"), t("coach.promptQuiz")];
  const listRef = useRef<FlatList<Message>>(null);
  const autoSentRef = useRef(false);

  const [subject, setSubject] = useState<Subject | null>(null);
  const [document, setDocument] = useState<Document | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const [s, doc] = await Promise.all([
        subjectsApi.getSubject(subjectId),
        documentId ? documentsApi.getDocument(documentId) : Promise.resolve(null),
      ]);
      if (cancelled) return;
      setSubject(s);
      setDocument(doc);

      // Scoped to one document: always start a fresh conversation rather than
      // resuming the subject's latest one, which may cover unrelated
      // material and would otherwise be sent along as history.
      if (!documentId) {
        const conversations = await chatApi.listConversations(subjectId);
        const latest = conversations[0];
        if (latest) {
          const history = await chatApi.listMessages(latest.id);
          if (cancelled) return;
          setConversationId(latest.id);
          setMessages(history);
        }
      }
      setIsLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [subjectId, documentId]);

  async function send(question: string) {
    const text = question.trim();
    if (!text || isSending) return;
    setDraft("");
    setIsSending(true);
    const optimistic: Message = {
      id: `pending-${Date.now()}`,
      conversation_id: conversationId ?? "",
      role: "user",
      content: text,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    try {
      const result = await chatApi.sendMessage(subjectId, {
        question: text,
        conversation_id: conversationId,
        document_id: documentId ?? null,
      });
      setConversationId(result.conversation_id);
      setMessages((m) => [...m.filter((msg) => msg.id !== optimistic.id), result.user_message, result.assistant_message]);
    } catch {
      setMessages((m) => m.filter((msg) => msg.id !== optimistic.id));
    } finally {
      setIsSending(false);
      requestAnimationFrame(() => listRef.current?.scrollToEnd({ animated: true }));
    }
  }

  // Arriving from a "Review now" gap card (Progress tab) with a concept
  // already picked — auto-ask it once the empty-conversation check has had
  // a chance to load, but only ever once per screen instance.
  useEffect(() => {
    if (isLoading || autoSentRef.current || !prompt || messages.length > 0) return;
    autoSentRef.current = true;
    send(prompt);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, prompt, messages.length]);

  return (
    <Screen>
      <KeyboardAvoidingView className="flex-1" behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={16}>
        <View className="mt-2 mb-2 flex-row items-center gap-3">
          <IconButton icon={CaretLeftIcon} onPress={() => router.back()} />
          <View className="flex-1">
            <Text className="text-base font-semibold">{t("coach.title")}</Text>
            <Text className="text-xs text-emerald-600 dark:text-emerald-400" numberOfLines={1}>
              {document?.original_filename ?? subject?.name ?? "…"}
            </Text>
          </View>
        </View>

        {isLoading ? (
          <View className="flex-1 items-center justify-center">
            <ActivityIndicator color={scheme.primary} />
          </View>
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            contentContainerClassName="gap-6 py-3 grow"
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
            ListEmptyComponent={
              <View className="pt-6">
                <Text className="text-3xl font-bold">{t("coach.emptyTitle")}</Text>
                <Text className="mt-3 text-muted-foreground">{documentId ? t("coach.emptyBodyDocument") : t("coach.emptyBody")}</Text>
                <View className="mt-6 flex-row flex-wrap gap-2">
                  {SUGGESTED_PROMPTS.map((p) => (
                    <Pressable key={p} onPress={() => send(p)} className="rounded-full bg-card px-5 py-3 shadow-sm shadow-black/5">
                      <Text className="text-[13.5px] font-semibold">{p}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            }
            renderItem={({ item }) => {
              const mine = item.role === "user";
              return (
                <View className={cn("max-w-[88%]", mine ? "items-end self-end" : "items-start self-start")}>
                  <View
                    className={cn(
                      "rounded-[22px] px-5 py-3",
                      mine ? "rounded-br-lg bg-primary" : "rounded-bl-lg bg-card shadow-sm shadow-black/5"
                    )}
                  >
                    <Text className={cn("text-[15.5px] leading-6", mine && "text-primary-foreground")}>{item.content}</Text>
                  </View>
                  {item.citations.length > 0 ? (
                    <View className="mt-2 flex-row flex-wrap gap-1">
                      {item.citations.map((c: Citation) => (
                        <View key={c.chunk_id} className="flex-row items-center gap-1.5 rounded-full bg-card px-2 py-1.5 shadow-sm shadow-black/5">
                          <FileTextIcon size={13} color="#059669" />
                          <Text className="max-w-50 text-xs text-muted-foreground">
                            {c.document_filename}
                            {c.page ? ` · p.${c.page}` : ""}
                          </Text>
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>
              );
            }}
            ListFooterComponent={
              isSending ? (
                <View className="self-start rounded-[22px] bg-card px-5 py-3 shadow-sm shadow-black/5">
                  <ActivityIndicator size="small" color={scheme.primary} />
                </View>
              ) : null
            }
          />
        )}

        <View className="mb-6 flex-row items-end gap-2 rounded-2xl bg-card p-2 shadow-lg shadow-black/10">
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder={t("coach.inputPlaceholder")}
            placeholderTextColor={scheme.mutedForeground}
            className="max-h-25 flex-1 px-3 py-2 text-[15px] text-foreground"
            multiline
          />
          <Pressable
            onPress={() => send(draft)}
            disabled={!draft.trim() || isSending}
            className="size-11 items-center justify-center rounded-full bg-primary"
            style={{ opacity: draft.trim() ? 1 : 0.5 }}
          >
            <ArrowUpIcon size={20} color={scheme.primaryForeground} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}
