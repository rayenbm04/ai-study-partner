/**
 * Home/Subjects tab — the student's subject list plus a quick cross-subject
 * overview (total flashcards due). Mirrors the Brilliant "learning path"
 * card pattern: icon, title, a stat instead of a static badge, using real
 * data from the analytics engine instead of anything canned.
 */
import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { FlatList, RefreshControl, StyleSheet, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Button, Card, Screen, Text } from "../../components/ui";
import { colors, radii, spacing } from "../../constants/theme";
import { analyticsApi, subjectsApi } from "../../lib/api";
import type { OverviewAnalytics, Subject } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";

export default function SubjectsScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [subjectList, overviewData] = await Promise.all([subjectsApi.listSubjects(), analyticsApi.getOverview()]);
    setSubjects(subjectList);
    setOverview(overviewData);
  }, []);

  // Refetch every time this tab regains focus (e.g. after creating a
  // subject elsewhere) rather than only once on mount.
  useFocusEffect(
    useCallback(() => {
      setIsLoading(true);
      load().finally(() => setIsLoading(false));
    }, [load])
  );

  async function handleRefresh() {
    setIsRefreshing(true);
    await load();
    setIsRefreshing(false);
  }

  const analyticsBySubject = new Map((overview?.subjects ?? []).map((s) => [s.subject_id, s]));

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">Hi {user?.firstname ?? "there"}</Text>
        {overview && overview.total_flashcards_due > 0 ? (
          <Text variant="body" style={styles.dueSummary}>
            {overview.total_flashcards_due} flashcard{overview.total_flashcards_due === 1 ? "" : "s"} due today
          </Text>
        ) : (
          <Text variant="body" style={styles.dueSummary}>
            You're all caught up on reviews.
          </Text>
        )}
      </View>

      <FlatList
        data={subjects}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />}
        ListEmptyComponent={
          !isLoading ? (
            <Card style={styles.emptyCard}>
              <Text variant="title">No subjects yet</Text>
              <Text variant="body" style={styles.emptyBody}>
                Add your first subject to start uploading material and generating study aids.
              </Text>
            </Card>
          ) : null
        }
        renderItem={({ item }) => {
          const stats = analyticsBySubject.get(item.id);
          return (
            <Card onPress={() => router.push(`/subject/${item.id}`)} style={styles.card}>
              <View style={styles.cardRow}>
                <View style={styles.iconWrap}>
                  <Ionicons name="book" size={22} color={colors.primary} />
                </View>
                <View style={styles.cardText}>
                  <Text variant="title">{item.name}</Text>
                  {stats ? (
                    <Text variant="caption">
                      {stats.concepts_practiced}/{stats.concepts_total} concepts practiced
                      {stats.average_mastery !== null ? ` · ${Math.round(stats.average_mastery)}% mastery` : ""}
                    </Text>
                  ) : (
                    <Text variant="caption">No documents yet</Text>
                  )}
                </View>
                {stats && stats.flashcards_due_count > 0 ? (
                  <View style={styles.dueBadge}>
                    <Text variant="caption" style={styles.dueBadgeText}>
                      {stats.flashcards_due_count} due
                    </Text>
                  </View>
                ) : null}
              </View>
            </Card>
          );
        }}
      />

      <Button label="+ New subject" onPress={() => router.push("/subject/new")} style={styles.newButton} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  dueSummary: {
    marginTop: spacing.xs,
    color: colors.textSecondary,
  },
  list: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
  },
  card: {
    marginBottom: spacing.md,
  },
  cardRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radii.md,
    backgroundColor: colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  cardText: {
    flex: 1,
  },
  dueBadge: {
    backgroundColor: colors.accentLight,
    borderRadius: radii.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs / 2,
  },
  dueBadgeText: {
    color: colors.accentDark,
  },
  emptyCard: {
    marginTop: spacing.xl,
  },
  emptyBody: {
    marginTop: spacing.xs,
  },
  newButton: {
    marginBottom: spacing.lg,
  },
});
