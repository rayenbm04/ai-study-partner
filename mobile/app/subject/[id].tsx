/**
 * Subject detail — documents, a progress snapshot, and entry points into a
 * quiz, a timed exam, an AI-generated summary, or the AI Coach. Uploaded
 * documents are classified by type (exam/résumé/TD/TP/cours) server-side
 * during ingestion, hence the polling effect below — a document sits at
 * pending/processing for a bit before that badge is available.
 */
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, Pressable, ScrollView, useColorScheme, View } from "react-native";

import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Tag } from "../../components/ui/Tag";
import { Text } from "../../components/ui/text";
import { ApiError, analyticsApi, documentsApi, examsApi, quizzesApi, subjectsApi, summariesApi } from "../../lib/api";
import type { Document, DocumentType, Subject, SubjectAnalytics, Summary, SummaryType } from "../../lib/api";
import { confirmDestructiveAction } from "../../lib/confirm";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { cn } from "../../lib/utils";

const EXAM_DURATIONS = [15, 30, 45, 60];

export default function SubjectDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { t } = useLanguage();

  const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
    exam: t("documentType.exam"),
    resume: t("documentType.resume"),
    td: "TD",
    tp: "TP",
    cours: t("documentType.cours"),
    other: t("documentType.other"),
  };

  const SUMMARY_TYPES: { type: SummaryType; label: string }[] = [
    { type: "short", label: t("summaryType.short") },
    { type: "detailed", label: t("summaryType.detailed") },
    { type: "bullet", label: t("summaryType.bullet") },
    { type: "key_concepts", label: t("summaryType.keyConcepts") },
    { type: "formula_sheet", label: t("summaryType.formulaSheet") },
    { type: "definitions", label: t("summaryType.definitions") },
  ];

  const DOCUMENT_STATUS_LABELS: Record<Document["status"], string> = {
    pending: t("documentStatus.pending"),
    processing: t("documentStatus.processing"),
    ready: t("documentStatus.ready"),
    failed: t("documentStatus.failed"),
  };
  const [subject, setSubject] = useState<Subject | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<SubjectAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [documentError, setDocumentError] = useState<string | null>(null);

  const [examSheetDocId, setExamSheetDocId] = useState<string | null>(null);
  const [isGeneratingExam, setIsGeneratingExam] = useState(false);

  const [summarySheetDocId, setSummarySheetDocId] = useState<string | null>(null);
  const [summaryResult, setSummaryResult] = useState<Summary | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      Promise.all([subjectsApi.getSubject(id), documentsApi.listDocuments(id), analyticsApi.getSubjectAnalytics(id)])
        .then(([s, docs, a]) => {
          if (cancelled) return;
          setSubject(s);
          setDocuments(docs);
          setStats(a);
        })
        .finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [id])
  );

  // Ingestion (extraction, chunking, classification) runs as a background
  // task after upload, so a freshly uploaded document sits at
  // "pending"/"processing" for a bit — poll until it settles so the status
  // tag and classification badge update without the user having to leave
  // and refocus the screen.
  useEffect(() => {
    const isSettling = documents.some((d) => d.status === "pending" || d.status === "processing");
    if (!isSettling) return;
    const interval = setInterval(() => {
      documentsApi.listDocuments(id).then(setDocuments);
    }, 3000);
    return () => clearInterval(interval);
  }, [id, documents]);

  async function handleUpload() {
    setDocumentError(null);
    const file = await documentsApi.pickDocument();
    if (!file) return;
    setIsUploading(true);
    try {
      const document = await documentsApi.uploadDocument(id, file);
      setDocuments((prev) => [document, ...prev]);
    } catch (err) {
      setDocumentError(err instanceof ApiError ? err.message : t("subjectDetail.uploadError"));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(document: Document) {
    const confirmed = await confirmDestructiveAction(
      t("subjectDetail.deleteDocTitle"),
      t("subjectDetail.deleteDocBody", { filename: document.original_filename }),
      t("common.delete"),
      t("common.cancel")
    );
    if (!confirmed) return;
    await documentsApi.deleteDocument(document.id);
    setDocuments((prev) => prev.filter((d) => d.id !== document.id));
  }

  async function handlePreview(document: Document) {
    try {
      await documentsApi.previewDocument(document);
    } catch {
      setDocumentError(t("subjectDetail.previewError"));
    }
  }

  async function handleGenerateQuiz(documentId: string) {
    setGeneratingFor(documentId);
    try {
      const quiz = await quizzesApi.generateQuiz(id, { document_id: documentId });
      router.push(`/quiz/${quiz.id}`);
    } finally {
      setGeneratingFor(null);
    }
  }

  async function handleGenerateExam(durationMinutes: number) {
    if (!examSheetDocId) return;
    setIsGeneratingExam(true);
    try {
      const exam = await examsApi.generateExam(id, { document_id: examSheetDocId, duration_minutes: durationMinutes });
      setExamSheetDocId(null);
      router.push(`/quiz/${exam.id}`);
    } finally {
      setIsGeneratingExam(false);
    }
  }

  async function handleGenerateSummary(type: SummaryType) {
    if (!summarySheetDocId) return;
    setIsSummaryLoading(true);
    try {
      const summary = await summariesApi.generateSummary(id, { document_id: summarySheetDocId, summary_type: type });
      setSummaryResult(summary);
    } finally {
      setIsSummaryLoading(false);
    }
  }

  function closeSummarySheet() {
    setSummarySheetDocId(null);
    setSummaryResult(null);
  }

  if (isLoading || !subject) {
    return (
      <Screen>
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator color={scheme.primary} />
        </View>
      </Screen>
    );
  }

  const readyDocuments = documents.filter((d) => d.status === "ready");

  return (
    <Screen>
      <ScrollView contentContainerClassName="pt-2 pb-16">
        <View className="mb-3">
          <IconButton name="chevron-back" onPress={() => router.back()} />
        </View>
        <Text className="mb-1 text-3xl font-bold">{subject.name}</Text>
        {subject.description ? <Text className="text-muted-foreground">{subject.description}</Text> : null}

        {stats ? (
          <Pressable onPress={() => router.push(`/concepts/${id}`)} className="mt-6">
            <Card>
              <CardContent>
                <View className="flex-row justify-between">
                  <Stat label={t("subjectDetail.mastery")} value={stats.average_mastery !== null ? `${Math.round(stats.average_mastery)}%` : "—"} />
                  <Stat label={t("progress.weakSpots")} value={String(stats.weak_concept_count)} />
                  <Stat label={t("subjectDetail.dueCards")} value={String(stats.flashcards_due_count)} />
                </View>
                <View className="mt-3 flex-row items-center justify-center gap-1">
                  <Text className="text-xs text-primary">{t("subjectDetail.viewConceptMap")}</Text>
                  <Ionicons name="chevron-forward" size={13} color={scheme.primary} />
                </View>
              </CardContent>
            </Card>
          </Pressable>
        ) : null}

        <View className="mt-6">
          <Button onPress={() => router.push(`/coach/${id}`)}>
            <Text>{t("subjectDetail.askCoach")}</Text>
          </Button>
        </View>
        <Pressable className="mt-3 flex-row items-center justify-center gap-1 self-center" onPress={() => router.push(`/materials/${id}`)}>
          <Text className="text-xs text-primary">{t("subjectDetail.viewSavedMaterials")}</Text>
          <Ionicons name="chevron-forward" size={13} color={scheme.primary} />
        </Pressable>

        <View className="mt-8 mb-2 flex-row items-center justify-between">
          <Text className="text-lg font-semibold">{t("subjectDetail.documents")}</Text>
          <IconButton name="add" onPress={handleUpload} size={36} />
        </View>
        {isUploading ? (
          <View className="mb-2 flex-row items-center gap-2">
            <ActivityIndicator color={scheme.primary} size="small" />
            <Text className="text-xs text-muted-foreground">{t("subjectDetail.uploading")}</Text>
          </View>
        ) : null}
        {documentError ? <Text className="mb-2 text-xs text-destructive">{documentError}</Text> : null}
        {documents.length === 0 ? (
          <Card>
            <CardContent>
              <Text className="mb-3">{t("subjectDetail.noDocuments")}</Text>
              <Button variant="secondary" onPress={handleUpload} disabled={isUploading}>
                {isUploading ? <ActivityIndicator color={scheme.foreground} /> : null}
                <Text>{t("subjectDetail.uploadDocument")}</Text>
              </Button>
            </CardContent>
          </Card>
        ) : (
          documents.map((doc) => (
            <Card key={doc.id} className="mb-3">
              <CardContent>
                <View className="flex-row items-center gap-2">
                  <Ionicons name="document-text-outline" size={20} color={scheme.mutedForeground} />
                  <Pressable className="flex-1" onPress={() => handlePreview(doc)} hitSlop={4}>
                    <Text numberOfLines={1}>{doc.original_filename}</Text>
                  </Pressable>
                  <View className="flex-row gap-1">
                    <Tag label={DOCUMENT_STATUS_LABELS[doc.status]} tone={doc.status === "ready" ? "sage" : "neutral"} />
                    {doc.document_type ? <Tag label={DOCUMENT_TYPE_LABELS[doc.document_type]} tone="accent" /> : null}
                  </View>
                  <Pressable onPress={() => handleDelete(doc)} hitSlop={8} className="ml-1">
                    <Ionicons name="close-circle" size={20} color={scheme.destructive} />
                  </Pressable>
                </View>
                {doc.status === "ready" ? (
                  <View className="mt-3 flex-row gap-2">
                    <DocAction
                      icon="help-circle-outline"
                      label={t("subjectDetail.quiz")}
                      loading={generatingFor === doc.id}
                      onPress={() => handleGenerateQuiz(doc.id)}
                    />
                    <DocAction icon="timer-outline" label={t("subjectDetail.exam")} onPress={() => setExamSheetDocId(doc.id)} />
                    <DocAction
                      icon="reader-outline"
                      label={t("subjectDetail.summary")}
                      onPress={() => {
                        setSummarySheetDocId(doc.id);
                        setSummaryResult(null);
                      }}
                    />
                    <DocAction
                      icon="chatbubble-ellipses-outline"
                      label={t("subjectDetail.ask")}
                      onPress={() => router.push(`/coach/${id}?documentId=${doc.id}`)}
                    />
                  </View>
                ) : null}
              </CardContent>
            </Card>
          ))
        )}

        {readyDocuments.length === 0 && documents.length > 0 ? (
          <Text className="mt-2 text-xs text-muted-foreground">{t("subjectDetail.processingNote")}</Text>
        ) : null}
      </ScrollView>

      {examSheetDocId ? (
        <Sheet onClose={() => (isGeneratingExam ? null : setExamSheetDocId(null))}>
          <Text className="mb-1 text-2xl font-bold">{t("subjectDetail.timedExam")}</Text>
          <Text className="mb-6 text-muted-foreground">{t("subjectDetail.examDurationPrompt")}</Text>
          <View className="flex-row gap-2">
            {EXAM_DURATIONS.map((minutes) => (
              <Pressable
                key={minutes}
                disabled={isGeneratingExam}
                onPress={() => handleGenerateExam(minutes)}
                className="h-14 flex-1 items-center justify-center rounded-full bg-card shadow-sm shadow-black/5"
              >
                {isGeneratingExam ? (
                  <ActivityIndicator color={scheme.primary} size="small" />
                ) : (
                  <Text className="font-semibold">{t("common.minutes", { minutes })}</Text>
                )}
              </Pressable>
            ))}
          </View>
        </Sheet>
      ) : null}

      {summarySheetDocId ? (
        <Sheet onClose={closeSummarySheet}>
          {summaryResult ? (
            <>
              <Text className="mb-1 text-2xl font-bold">
                {SUMMARY_TYPES.find((s) => s.type === summaryResult.summary_type)?.label ?? t("subjectDetail.summary")}
              </Text>
              <ScrollView className="max-h-90">
                <Text className="text-muted-foreground">{summaryResult.content}</Text>
              </ScrollView>
              <Button variant="secondary" onPress={() => setSummaryResult(null)} className="mt-6">
                <Text>{t("subjectDetail.chooseAnotherType")}</Text>
              </Button>
            </>
          ) : isSummaryLoading ? (
            <View className="items-center gap-3 py-10">
              <ActivityIndicator color={scheme.primary} />
              <Text className="mt-1 text-xs text-muted-foreground">{t("subjectDetail.readingDocument")}</Text>
            </View>
          ) : (
            <>
              <Text className="mb-1 text-2xl font-bold">{t("subjectDetail.summarize")}</Text>
              <Text className="mb-6 text-muted-foreground">{t("subjectDetail.summarizePrompt")}</Text>
              <View className="flex-row flex-wrap gap-2">
                {SUMMARY_TYPES.map(({ type, label }) => (
                  <Pressable
                    key={type}
                    onPress={() => handleGenerateSummary(type)}
                    className="rounded-full bg-card px-5 py-3 shadow-sm shadow-black/5"
                  >
                    <Text className="text-[13.5px] font-semibold">{label}</Text>
                  </Pressable>
                ))}
              </View>
            </>
          )}
        </Sheet>
      ) : null}
    </Screen>
  );
}

function DocAction({
  icon,
  label,
  onPress,
  loading,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
  loading?: boolean;
}) {
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  return (
    <Pressable onPress={onPress} disabled={loading} className="h-11 flex-1 flex-row items-center justify-center gap-1.5 rounded-full bg-input/30">
      {loading ? (
        <ActivityIndicator size="small" color={scheme.primary} />
      ) : (
        <Ionicons name={icon} size={16} color={scheme.foreground} />
      )}
      <Text className="text-[12.5px] font-semibold">{label}</Text>
    </Pressable>
  );
}

function Sheet({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  return (
    <>
      <Pressable className="absolute inset-0 bg-black/40" onPress={onClose} />
      <View className="absolute right-0 bottom-0 left-0 max-h-[80%] rounded-t-2xl bg-background p-6">
        <View className="mb-6">
          <View className="h-1.5 w-11 self-center rounded-full bg-border" />
          <Pressable onPress={onClose} hitSlop={12} className="absolute -top-1.5 right-0">
            <Ionicons name="close" size={20} color={scheme.mutedForeground} />
          </Pressable>
        </View>
        {children}
      </View>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View className="items-center">
      <Text className="text-lg font-semibold">{value}</Text>
      <Text className="text-xs text-muted-foreground">{label}</Text>
    </View>
  );
}
