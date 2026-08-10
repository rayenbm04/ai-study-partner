/**
 * Home/Subjects tab — greeting, a due-flashcards hero card that drives
 * straight into the Cards tab, and the subject list with a mastery bar per
 * subject. A floating action button opens the AI Coach for a subject (picks
 * automatically when there's only one, otherwise asks which).
 */
import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { FlatList, Pressable, RefreshControl, StyleSheet, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Avatar, Button, Card, IconButton, Screen, Tag, Text } from "../../components/ui";
import { radii, spacing } from "../../constants/theme";
import { analyticsApi, subjectsApi } from "../../lib/api";
import type { OverviewAnalytics, Subject } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";

export default function SubjectsScreen() {
  const { user } = useAuth();
  const { colors } = useTheme();
  const { t, tn } = useLanguage();
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

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

  function openCoach() {
    if (subjects.length === 0) return;
    if (subjects.length === 1) {
      router.push(`/coach/${subjects[0].id}`);
      return;
    }
    setPickerOpen(true);
  }

  const analyticsBySubject = new Map((overview?.subjects ?? []).map((s) => [s.subject_id, s]));
  const dueCount = overview?.total_flashcards_due ?? 0;

  return (
    <Screen>
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <View style={styles.headerText}>
            <Text variant="label">{t("home.hello")}</Text>
            <Text variant="display" style={styles.name}>
              {user?.firstname ?? "there"}
            </Text>
          </View>
          <Avatar label={user?.firstname ?? "?"} />
        </View>
      </View>

      <FlatList
        data={subjects}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />}
        ListHeaderComponent={
          <>
            <Card style={[styles.heroCard, { backgroundColor: colors.surface }]}>
              <View style={styles.heroRow}>
                <View style={[styles.heroIcon, { backgroundColor: colors.primaryLight }]}>
                  <Ionicons name="flash" size={26} color={colors.accentDark} />
                </View>
                <View style={styles.heroText}>
                  <Text variant="label">{t("home.todaysMission")}</Text>
                  <Text variant="title" style={styles.heroTitle}>
                    {dueCount > 0 ? tn("home.cardsDue", dueCount) : t("home.allCaughtUp")}
                  </Text>
                  <Text variant="caption">
                    {dueCount > 0 ? t("home.streakBody") : t("home.nothingDueBody")}
                  </Text>
                </View>
              </View>
              <Button
                label={dueCount > 0 ? t("home.continueReviewing") : t("home.reviewAnyway")}
                onPress={() => router.push("/(tabs)/cards")}
                style={styles.heroButton}
              />
            </Card>

            <Text variant="title" style={styles.sectionLabel}>
              {t("home.yourSubjects")}
            </Text>
          </>
        }
        ListEmptyComponent={
          !isLoading ? (
            <Card style={styles.emptyCard}>
              <Text variant="title">{t("home.noSubjectsTitle")}</Text>
              <Text variant="body" style={styles.emptyBody}>
                {t("home.noSubjectsBody")}
              </Text>
              <Button
                label={t("home.newSubject")}
                variant="secondary"
                onPress={() => router.push("/subject/new")}
                style={styles.newButton}
              />
            </Card>
          ) : null
        }
        ListFooterComponent={
          subjects.length > 0 ? (
            <Button
              label={t("home.newSubject")}
              variant="secondary"
              onPress={() => router.push("/subject/new")}
              style={styles.newButton}
            />
          ) : null
        }
        renderItem={({ item }) => {
          const stats = analyticsBySubject.get(item.id);
          const mastery = stats?.average_mastery ?? null;
          return (
            <Card onPress={() => router.push(`/subject/${item.id}`)} style={styles.card}>
              <View style={styles.cardRow}>
                <Avatar label={item.name} size={44} />
                <View style={styles.cardText}>
                  <Text variant="subtitle">{item.name}</Text>
                  {stats ? (
                    <Text variant="caption">
                      {t("home.conceptsPracticed", { practiced: stats.concepts_practiced, total: stats.concepts_total })}
                    </Text>
                  ) : (
                    <Text variant="caption">{t("home.noDocumentsYet")}</Text>
                  )}
                </View>
                <Text variant="title" style={{ color: colors.accentDark }}>
                  {mastery !== null ? `${Math.round(mastery)}%` : "—"}
                </Text>
              </View>
              <View style={[styles.barTrack, { backgroundColor: colors.border }]}>
                <View
                  style={[
                    styles.barFill,
                    { width: `${Math.max(4, mastery ?? 4)}%`, backgroundColor: colors.accent },
                  ]}
                />
              </View>
              {stats && stats.flashcards_due_count > 0 ? (
                <Tag label={tn("home.dueTag", stats.flashcards_due_count)} tone="accent" style={styles.dueTag} />
              ) : null}
            </Card>
          );
        }}
      />

      <Pressable
        onPress={openCoach}
        style={[styles.fab, { backgroundColor: colors.accent, shadowColor: colors.accent }]}
      >
        <Ionicons name="chatbubble-ellipses" size={24} color={colors.textOnAccent} />
      </Pressable>

      {pickerOpen ? (
        <>
          <Pressable style={[styles.backdrop, { backgroundColor: colors.overlay }]} onPress={() => setPickerOpen(false)} />
          <View style={[styles.sheet, { backgroundColor: colors.background }]}>
            <View style={[styles.sheetHandle, { backgroundColor: colors.border }]} />
            <Text variant="display" style={styles.sheetTitle}>
              {t("home.talkAboutWhich")}
            </Text>
            {subjects.map((s) => (
              <Card
                key={s.id}
                onPress={() => {
                  setPickerOpen(false);
                  router.push(`/coach/${s.id}`);
                }}
                style={styles.sheetRow}
              >
                <Text variant="subtitle">{s.name}</Text>
              </Card>
            ))}
          </View>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerText: {
    flex: 1,
  },
  name: {
    marginTop: spacing.xs / 2,
  },
  list: {
    gap: spacing.md,
    paddingBottom: 130,
  },
  heroCard: {
    marginBottom: spacing.md,
  },
  heroRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  heroIcon: {
    width: 52,
    height: 52,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
  },
  heroText: {
    flex: 1,
  },
  heroTitle: {
    marginTop: spacing.xs / 2,
  },
  heroButton: {
    marginTop: spacing.lg,
  },
  sectionLabel: {
    marginTop: spacing.lg,
    marginBottom: spacing.xs,
  },
  card: {
    marginBottom: 0,
  },
  cardRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  cardText: {
    flex: 1,
  },
  barTrack: {
    height: 6,
    borderRadius: radii.full,
    marginTop: spacing.md,
    overflow: "hidden",
  },
  barFill: {
    height: "100%",
    borderRadius: radii.full,
  },
  dueTag: {
    marginTop: spacing.sm,
  },
  emptyCard: {
    marginTop: spacing.md,
  },
  emptyBody: {
    marginTop: spacing.xs,
  },
  newButton: {
    marginTop: spacing.sm,
  },
  fab: {
    position: "absolute",
    right: spacing.lg,
    bottom: 96,
    width: 60,
    height: 60,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.35,
    shadowRadius: 18,
    elevation: 6,
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
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  sheetHandle: {
    width: 44,
    height: 5,
    borderRadius: radii.full,
    alignSelf: "center",
    marginBottom: spacing.lg,
  },
  sheetTitle: {
    marginBottom: spacing.md,
  },
  sheetRow: {
    marginBottom: 0,
  },
});
