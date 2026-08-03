/**
 * Subject detail — documents, a progress snapshot, and entry points into a
 * quiz or the AI Coach. Document upload isn't wired up on mobile yet (see
 * lib/api/documents.ts), so a subject with no ready documents shows a note
 * rather than a broken "generate quiz" button.
 */
import { Ionicons } from "@expo/vector-icons";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, ScrollView, StyleSheet, View } from "react-native";

import { Button, Card, IconButton, Screen, Tag, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { analyticsApi, documentsApi, quizzesApi, subjectsApi } from "../../lib/api";
import type { Document, Subject, SubjectAnalytics } from "../../lib/api";
import { useTheme } from "../../lib/theme-context";

export default function SubjectDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { colors } = useTheme();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<SubjectAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);

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

  async function handleGenerateQuiz(documentId: string) {
    setGeneratingFor(documentId);
    try {
      const quiz = await quizzesApi.generateQuiz(id, { document_id: documentId });
      router.push(`/quiz/${quiz.id}`);
    } finally {
      setGeneratingFor(null);
    }
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
          <Card style={styles.statsCard}>
            <View style={styles.statsRow}>
              <Stat label="Mastery" value={stats.average_mastery !== null ? `${Math.round(stats.average_mastery)}%` : "—"} />
              <Stat label="Weak spots" value={String(stats.weak_concept_count)} />
              <Stat label="Due cards" value={String(stats.flashcards_due_count)} />
            </View>
          </Card>
        ) : null}

        <View style={styles.actionsRow}>
          <Button label="Ask the Coach" onPress={() => router.push(`/coach/${id}`)} style={styles.coachButton} />
        </View>

        <Text variant="title" style={styles.sectionLabel}>
          Documents
        </Text>
        {documents.length === 0 ? (
          <Card>
            <Text variant="body">
              No documents yet. Upload from the web app for now — mobile upload is coming soon.
            </Text>
          </Card>
        ) : (
          documents.map((doc) => (
            <Card key={doc.id} style={styles.docCard}>
              <View style={styles.docRow}>
                <Ionicons name="document-text-outline" size={20} color={colors.textSecondary} />
                <Text variant="body" style={styles.docName}>
                  {doc.original_filename}
                </Text>
                <Tag label={doc.status} tone={doc.status === "ready" ? "sage" : "neutral"} />
              </View>
              {doc.status === "ready" ? (
                <Button
                  label="Generate quiz"
                  variant="secondary"
                  onPress={() => handleGenerateQuiz(doc.id)}
                  loading={generatingFor === doc.id}
                  style={styles.docAction}
                />
              ) : null}
            </Card>
          ))
        )}

        {readyDocuments.length === 0 && documents.length > 0 ? (
          <Text variant="caption" style={styles.processingNote}>
            Quiz generation unlocks once at least one document finishes processing.
          </Text>
        ) : null}
      </ScrollView>
    </Screen>
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
  stat: {
    alignItems: "center",
  },
  actionsRow: {
    marginTop: spacing.lg,
  },
  coachButton: {},
  sectionLabel: {
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  docCard: {
    marginBottom: spacing.md,
  },
  docRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  docName: {
    flex: 1,
  },
  docAction: {
    marginTop: spacing.md,
    height: 48,
  },
  processingNote: {
    marginTop: spacing.sm,
  },
});
