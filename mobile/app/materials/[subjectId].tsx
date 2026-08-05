/**
 * Saved study materials — browses back to everything already generated and
 * persisted server-side for this subject: past quizzes/exams (one row per
 * generation) and past summaries (upserted per document+type). Nothing here
 * is generated on this screen; it's purely a browsing view for material that
 * would otherwise be lost once its generation sheet/screen was closed.
 */
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from "react-native";

import { Card, IconButton, Screen, Tag, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { documentsApi, quizzesApi, subjectsApi, summariesApi } from "../../lib/api";
import type { Document, QuizListItem, Subject, Summary } from "../../lib/api";
import { useTheme } from "../../lib/theme-context";

const SUMMARY_TYPE_LABELS: Record<string, string> = {
  short: "Short summary",
  detailed: "Detailed summary",
  bullet: "Bullet points",
  key_concepts: "Key concepts",
  formula_sheet: "Formula sheet",
  definitions: "Definitions",
};

type DocumentSummaries = { document: Document; summaries: Summary[] };

export default function SavedMaterialsScreen() {
  const { subjectId } = useLocalSearchParams<{ subjectId: string }>();
  const router = useRouter();
  const { colors } = useTheme();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [quizzes, setQuizzes] = useState<QuizListItem[]>([]);
  const [documentSummaries, setDocumentSummaries] = useState<DocumentSummaries[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedSummaryId, setExpandedSummaryId] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      Promise.all([
        subjectsApi.getSubject(subjectId),
        quizzesApi.listQuizzesForSubject(subjectId),
        documentsApi.listDocuments(subjectId),
      ])
        .then(async ([s, quizList, documents]) => {
          const readyDocuments = documents.filter((d) => d.status === "ready");
          const summariesPerDocument = await Promise.all(
            readyDocuments.map((document) => summariesApi.listSummariesForDocument(document.id))
          );
          if (cancelled) return;
          setSubject(s);
          setQuizzes(quizList);
          setDocumentSummaries(
            readyDocuments
              .map((document, i) => ({ document, summaries: summariesPerDocument[i] }))
              .filter((entry) => entry.summaries.length > 0)
          );
        })
        .finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [subjectId])
  );

  if (isLoading || !subject) {
    return (
      <Screen>
        <View style={styles.loading}>
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.headerRow}>
          <IconButton name="chevron-back" onPress={() => router.back()} />
        </View>
        <Text variant="display" style={styles.title}>
          Saved materials
        </Text>
        <Text variant="body" style={{ color: colors.textSecondary }}>
          {subject.name}
        </Text>

        <Text variant="title" style={styles.sectionLabel}>
          Quizzes & Exams
        </Text>
        {quizzes.length === 0 ? (
          <Card>
            <Text variant="body">No quizzes or exams generated yet.</Text>
          </Card>
        ) : (
          quizzes.map((quiz) => (
            <Card key={quiz.id} onPress={() => router.push(`/quiz/${quiz.id}`)} style={styles.rowCard}>
              <View style={styles.quizRow}>
                <View style={styles.quizInfo}>
                  <Text variant="body">{quiz.title}</Text>
                  <Text variant="caption" style={{ marginTop: 2 }}>
                    {quiz.question_count} question{quiz.question_count === 1 ? "" : "s"} ·{" "}
                    {new Date(quiz.created_at).toLocaleDateString()}
                  </Text>
                </View>
                <Tag label={quiz.kind === "exam" ? "Exam" : "Quiz"} tone={quiz.kind === "exam" ? "accent" : "neutral"} />
                <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
              </View>
            </Card>
          ))
        )}

        <Text variant="title" style={styles.sectionLabel}>
          Summaries
        </Text>
        {documentSummaries.length === 0 ? (
          <Card>
            <Text variant="body">No summaries generated yet.</Text>
          </Card>
        ) : (
          documentSummaries.map(({ document, summaries }) => (
            <Card key={document.id} style={styles.rowCard}>
              <Text variant="label" style={{ marginBottom: spacing.sm }}>
                {document.original_filename}
              </Text>
              {summaries.map((summary) => (
                <View key={summary.id}>
                  <Pressable
                    style={styles.summaryRow}
                    onPress={() => setExpandedSummaryId((current) => (current === summary.id ? null : summary.id))}
                  >
                    <Text variant="body" style={styles.summaryTypeLabel}>
                      {SUMMARY_TYPE_LABELS[summary.summary_type] ?? summary.summary_type}
                    </Text>
                    <Ionicons
                      name={expandedSummaryId === summary.id ? "chevron-up" : "chevron-down"}
                      size={16}
                      color={colors.textMuted}
                    />
                  </Pressable>
                  {expandedSummaryId === summary.id ? (
                    <Text variant="body" style={[styles.summaryContent, { color: colors.textSecondary }]}>
                      {summary.content}
                    </Text>
                  ) : null}
                </View>
              ))}
            </Card>
          ))
        )}
      </ScrollView>
    </Screen>
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
  sectionLabel: {
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  rowCard: {
    marginBottom: spacing.md,
  },
  quizRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  quizInfo: {
    flex: 1,
  },
  summaryRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: spacing.sm,
  },
  summaryTypeLabel: {
    flex: 1,
  },
  summaryContent: {
    paddingBottom: spacing.sm,
  },
});
