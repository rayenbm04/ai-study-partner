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
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";

import { Button, Card, IconButton, Screen, Tag, Text } from "../../components/ui";
import { fontFamilies, radii, spacing } from "../../constants/theme";
import { ApiError, analyticsApi, documentsApi, examsApi, quizzesApi, subjectsApi, summariesApi } from "../../lib/api";
import type { Document, DocumentType, Subject, SubjectAnalytics, Summary, SummaryType } from "../../lib/api";
import { confirmDestructiveAction } from "../../lib/confirm";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

const EXAM_DURATIONS = [15, 30, 45, 60];

export default function SubjectDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { colors } = useTheme();
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
        <View style={styles.loading}>
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  const readyDocuments = documents.filter((d) => d.status === "ready");

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.headerRow}>
          <IconButton name="chevron-back" onPress={() => router.back()} />
        </View>
        <Text variant="display" style={styles.title}>
          {subject.name}
        </Text>
        {subject.description ? <Text variant="body" style={{ color: colors.textSecondary }}>{subject.description}</Text> : null}

        {stats ? (
          <Card onPress={() => router.push(`/concepts/${id}`)} style={styles.statsCard}>
            <View style={styles.statsRow}>
              <Stat label={t("subjectDetail.mastery")} value={stats.average_mastery !== null ? `${Math.round(stats.average_mastery)}%` : "—"} />
              <Stat label={t("progress.weakSpots")} value={String(stats.weak_concept_count)} />
              <Stat label={t("subjectDetail.dueCards")} value={String(stats.flashcards_due_count)} />
            </View>
            <View style={styles.statsHint}>
              <Text variant="caption" style={{ color: colors.accentDark }}>
                {t("subjectDetail.viewConceptMap")}
              </Text>
              <Ionicons name="chevron-forward" size={13} color={colors.accentDark} />
            </View>
          </Card>
        ) : null}

        <View style={styles.actionsRow}>
          <Button label={t("subjectDetail.askCoach")} onPress={() => router.push(`/coach/${id}`)} style={styles.coachButton} />
        </View>
        <Pressable style={styles.materialsLink} onPress={() => router.push(`/materials/${id}`)}>
          <Text variant="caption" style={{ color: colors.accentDark }}>
            {t("subjectDetail.viewSavedMaterials")}
          </Text>
          <Ionicons name="chevron-forward" size={13} color={colors.accentDark} />
        </Pressable>

        <View style={styles.sectionHeaderRow}>
          <Text variant="title">{t("subjectDetail.documents")}</Text>
          <IconButton name="add" onPress={handleUpload} size={36} />
        </View>
        {isUploading ? (
          <View style={styles.uploadingRow}>
            <ActivityIndicator color={colors.accent} size="small" />
            <Text variant="caption" style={{ color: colors.textSecondary }}>
              {t("subjectDetail.uploading")}
            </Text>
          </View>
        ) : null}
        {documentError ? (
          <Text variant="caption" style={[styles.documentError, { color: colors.error }]}>
            {documentError}
          </Text>
        ) : null}
        {documents.length === 0 ? (
          <Card>
            <Text variant="body" style={styles.emptyDocsText}>
              {t("subjectDetail.noDocuments")}
            </Text>
            <Button
              label={t("subjectDetail.uploadDocument")}
              variant="secondary"
              onPress={handleUpload}
              loading={isUploading}
              style={styles.emptyUploadButton}
            />
          </Card>
        ) : (
          documents.map((doc) => (
            <Card key={doc.id} style={styles.docCard}>
              <View style={styles.docRow}>
                <Ionicons name="document-text-outline" size={20} color={colors.textSecondary} />
                <Pressable style={styles.docName} onPress={() => handlePreview(doc)} hitSlop={4}>
                  <Text variant="body" numberOfLines={1}>
                    {doc.original_filename}
                  </Text>
                </Pressable>
                <View style={styles.docTags}>
                  <Tag label={DOCUMENT_STATUS_LABELS[doc.status]} tone={doc.status === "ready" ? "sage" : "neutral"} />
                  {doc.document_type ? <Tag label={DOCUMENT_TYPE_LABELS[doc.document_type]} tone="accent" /> : null}
                </View>
                <Pressable onPress={() => handleDelete(doc)} hitSlop={8} style={styles.docDelete}>
                  <Ionicons name="close-circle" size={20} color={colors.error} />
                </Pressable>
              </View>
              {doc.status === "ready" ? (
                <View style={styles.docActions}>
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
                </View>
              ) : null}
            </Card>
          ))
        )}

        {readyDocuments.length === 0 && documents.length > 0 ? (
          <Text variant="caption" style={styles.processingNote}>
            {t("subjectDetail.processingNote")}
          </Text>
        ) : null}
      </ScrollView>

      {examSheetDocId ? (
        <Sheet onClose={() => (isGeneratingExam ? null : setExamSheetDocId(null))}>
          <Text variant="display" style={styles.sheetTitle}>
            {t("subjectDetail.timedExam")}
          </Text>
          <Text variant="body" style={{ color: colors.textSecondary, marginBottom: spacing.lg }}>
            {t("subjectDetail.examDurationPrompt")}
          </Text>
          <View style={styles.durationRow}>
            {EXAM_DURATIONS.map((minutes) => (
              <Pressable
                key={minutes}
                disabled={isGeneratingExam}
                onPress={() => handleGenerateExam(minutes)}
                style={[styles.durationChip, { backgroundColor: colors.surface, shadowColor: colors.shadow }]}
              >
                {isGeneratingExam ? (
                  <ActivityIndicator color={colors.accent} size="small" />
                ) : (
                  <Text style={{ fontFamily: fontFamilies.semibold }}>{t("common.minutes", { minutes })}</Text>
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
              <Text variant="display" style={styles.sheetTitle}>
                {SUMMARY_TYPES.find((s) => s.type === summaryResult.summary_type)?.label ?? t("subjectDetail.summary")}
              </Text>
              <ScrollView style={styles.summaryScroll}>
                <Text variant="body" style={{ color: colors.textSecondary }}>
                  {summaryResult.content}
                </Text>
              </ScrollView>
              <Button label={t("subjectDetail.chooseAnotherType")} variant="secondary" onPress={() => setSummaryResult(null)} style={styles.sheetAction} />
            </>
          ) : isSummaryLoading ? (
            <View style={styles.summaryLoading}>
              <ActivityIndicator color={colors.accent} />
              <Text variant="caption" style={styles.summaryLoadingText}>
                {t("subjectDetail.readingDocument")}
              </Text>
            </View>
          ) : (
            <>
              <Text variant="display" style={styles.sheetTitle}>
                {t("subjectDetail.summarize")}
              </Text>
              <Text variant="body" style={{ color: colors.textSecondary, marginBottom: spacing.lg }}>
                {t("subjectDetail.summarizePrompt")}
              </Text>
              <View style={styles.summaryTypeGrid}>
                {SUMMARY_TYPES.map(({ type, label }) => (
                  <Pressable
                    key={type}
                    onPress={() => handleGenerateSummary(type)}
                    style={[styles.summaryTypeChip, { backgroundColor: colors.surface, shadowColor: colors.shadow }]}
                  >
                    <Text style={{ fontFamily: fontFamilies.semibold, fontSize: 13.5 }}>{label}</Text>
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
  const { colors } = useTheme();
  return (
    <Pressable onPress={onPress} disabled={loading} style={[styles.docAction, { backgroundColor: colors.surfaceAlt }]}>
      {loading ? (
        <ActivityIndicator size="small" color={colors.accent} />
      ) : (
        <Ionicons name={icon} size={16} color={colors.textPrimary} />
      )}
      <Text style={{ fontSize: 12.5, fontFamily: fontFamilies.semibold, color: colors.textPrimary }}>{label}</Text>
    </Pressable>
  );
}

function Sheet({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const { colors } = useTheme();
  return (
    <>
      <Pressable style={[styles.backdrop, { backgroundColor: colors.overlay }]} onPress={onClose} />
      <View style={[styles.sheet, { backgroundColor: colors.background }]}>
        <View style={styles.sheetTopRow}>
          <View style={[styles.sheetHandle, { backgroundColor: colors.border }]} />
          <Pressable onPress={onClose} style={styles.sheetClose} hitSlop={12}>
            <Ionicons name="close" size={20} color={colors.textMuted} />
          </Pressable>
        </View>
        {children}
      </View>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.stat}>
      <Text variant="title">{value}</Text>
      <Text variant="caption">{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  scroll: {
    paddingTop: spacing.sm,
    paddingBottom: spacing.xxxl,
  },
  headerRow: {
    marginBottom: spacing.md,
  },
  title: {
    marginBottom: spacing.xs,
  },
  statsCard: {
    marginTop: spacing.lg,
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  statsHint: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "center",
    gap: 2,
    marginTop: spacing.md,
  },
  stat: {
    alignItems: "center",
  },
  actionsRow: {
    marginTop: spacing.lg,
  },
  coachButton: {},
  materialsLink: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "center",
    gap: 2,
    marginTop: spacing.md,
  },
  sectionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  uploadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    marginBottom: spacing.sm,
  },
  documentError: {
    marginBottom: spacing.sm,
  },
  emptyDocsText: {
    marginBottom: spacing.md,
  },
  emptyUploadButton: {},
  docCard: {
    marginBottom: spacing.md,
  },
  docRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  docTags: {
    flexDirection: "row",
    gap: spacing.xs,
  },
  docName: {
    flex: 1,
  },
  docDelete: {
    marginLeft: spacing.xs,
  },
  docActions: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  docAction: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    height: 44,
    borderRadius: radii.full,
  },
  processingNote: {
    marginTop: spacing.sm,
  },
  backdrop: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    maxHeight: "80%",
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.xl,
  },
  sheetTopRow: {
    marginBottom: spacing.lg,
  },
  sheetHandle: {
    width: 44,
    height: 5,
    borderRadius: radii.full,
    alignSelf: "center",
  },
  sheetClose: {
    position: "absolute",
    right: 0,
    top: -6,
  },
  sheetTitle: {
    marginBottom: spacing.xs,
  },
  sheetAction: {
    marginTop: spacing.lg,
  },
  durationRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  durationChip: {
    flex: 1,
    height: 56,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
  },
  summaryTypeGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  summaryTypeChip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radii.full,
  },
  summaryScroll: {
    maxHeight: 360,
  },
  summaryLoading: {
    alignItems: "center",
    paddingVertical: spacing.xxl,
    gap: spacing.md,
  },
  summaryLoadingText: {
    marginTop: spacing.xs,
  },
});
