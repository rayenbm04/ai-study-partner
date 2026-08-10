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
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from "react-native";

import { IconButton, Screen, Text } from "../../components/ui";
import { fontFamilies, radii, spacing } from "../../constants/theme";
import { chatApi, documentsApi, subjectsApi } from "../../lib/api";
import type { Citation, Document, Message, Subject } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

export default function CoachScreen() {
  const { subjectId, prompt, documentId } = useLocalSearchParams<{
    subjectId: string;
    prompt?: string;
    documentId?: string;
  }>();
  const router = useRouter();
  const { colors } = useTheme();
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
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={16}
      >
        <View style={styles.header}>
          <IconButton name="chevron-back" onPress={() => router.back()} />
          <View style={styles.headerText}>
            <Text variant="title">{t("coach.title")}</Text>
            <Text variant="caption" style={{ color: colors.sageDark }} numberOfLines={1}>
              {document?.original_filename ?? subject?.name ?? "…"}
            </Text>
          </View>
        </View>

        {isLoading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.accent} />
          </View>
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            contentContainerStyle={styles.list}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
            ListEmptyComponent={
              <View style={styles.empty}>
                <Text variant="display">{t("coach.emptyTitle")}</Text>
                <Text variant="body" style={[styles.emptyBody, { color: colors.textSecondary }]}>
                  {documentId ? t("coach.emptyBodyDocument") : t("coach.emptyBody")}
                </Text>
                <View style={styles.prompts}>
                  {SUGGESTED_PROMPTS.map((p) => (
                    <Pressable
                      key={p}
                      onPress={() => send(p)}
                      style={[styles.promptChip, { backgroundColor: colors.surface, shadowColor: colors.shadow }]}
                    >
                      <Text style={{ fontFamily: fontFamilies.semibold, fontSize: 13.5 }}>{p}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            }
            renderItem={({ item }) => {
              const mine = item.role === "user";
              return (
                <View style={[styles.bubbleWrap, mine ? styles.bubbleWrapMine : styles.bubbleWrapTheirs]}>
                  <View
                    style={[
                      styles.bubble,
                      mine
                        ? { backgroundColor: colors.primary, borderBottomRightRadius: 8 }
                        : { backgroundColor: colors.surface, shadowColor: colors.shadow, borderBottomLeftRadius: 8 },
                    ]}
                  >
                    <Text style={{ color: mine ? colors.textOnPrimary : colors.textPrimary, fontSize: 15.5, lineHeight: 23 }}>
                      {item.content}
                    </Text>
                  </View>
                  {item.citations.length > 0 ? (
                    <View style={styles.citations}>
                      {item.citations.map((c: Citation) => (
                        <View
                          key={c.chunk_id}
                          style={[styles.citationChip, { backgroundColor: colors.surface, shadowColor: colors.shadow }]}
                        >
                          <Ionicons name="document-text-outline" size={13} color={colors.sageDark} />
                          <Text variant="caption" style={styles.citationText}>
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
                <View style={[styles.typing, { backgroundColor: colors.surface, shadowColor: colors.shadow }]}>
                  <ActivityIndicator size="small" color={colors.accent} />
                </View>
              ) : null
            }
          />
        )}

        <View style={[styles.inputBar, { backgroundColor: colors.surface, shadowColor: colors.shadowStrong }]}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            placeholder={t("coach.inputPlaceholder")}
            placeholderTextColor={colors.textMuted}
            style={[styles.input, { color: colors.textPrimary }]}
            multiline
          />
          <Pressable
            onPress={() => send(draft)}
            disabled={!draft.trim() || isSending}
            style={[styles.sendButton, { backgroundColor: colors.accent, opacity: draft.trim() ? 1 : 0.5 }]}
          >
            <Ionicons name="arrow-up" size={20} color={colors.textOnAccent} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  headerText: {
    flex: 1,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  list: {
    paddingVertical: spacing.md,
    gap: spacing.lg,
    flexGrow: 1,
  },
  empty: {
    paddingTop: spacing.xl,
  },
  emptyBody: {
    marginTop: spacing.md,
  },
  prompts: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.xl,
  },
  promptChip: {
    borderRadius: radii.full,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 1,
    shadowRadius: 14,
    elevation: 2,
  },
  bubbleWrap: {
    maxWidth: "88%",
  },
  bubbleWrapMine: {
    alignSelf: "flex-end",
    alignItems: "flex-end",
  },
  bubbleWrapTheirs: {
    alignSelf: "flex-start",
    alignItems: "flex-start",
  },
  bubble: {
    borderRadius: 22,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 18,
    elevation: 2,
  },
  citations: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
    marginTop: spacing.sm,
  },
  citationChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderRadius: radii.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 6,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 10,
    elevation: 1,
  },
  citationText: {
    maxWidth: 200,
  },
  typing: {
    alignSelf: "flex-start",
    borderRadius: 22,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 18,
    elevation: 2,
  },
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    borderRadius: radii.xl,
    padding: spacing.sm,
    marginBottom: spacing.lg,
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 1,
    shadowRadius: 24,
    elevation: 4,
  },
  input: {
    flex: 1,
    maxHeight: 100,
    fontSize: 15,
    fontFamily: fontFamilies.regular,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
  },
});
