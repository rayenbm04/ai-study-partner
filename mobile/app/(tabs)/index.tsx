/**
 * Home/Subjects tab — greeting, a due-flashcards hero card that drives
 * straight into the Cards tab, and the subject list with a mastery bar per
 * subject. A floating action button opens the AI Coach for a subject (picks
 * automatically when there's only one, otherwise asks which).
 */
import { ChatCircleDotsIcon, LightningIcon } from "phosphor-react-native";
import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { FlatList, Pressable, RefreshControl, View } from "react-native";

import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { analyticsApi, subjectsApi } from "../../lib/api";
import type { OverviewAnalytics, Subject } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";

export default function SubjectsScreen() {
  const { user } = useAuth();
  const { isDark } = useTheme();
  const scheme = isDark ? THEME.dark : THEME.light;
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
      <View className="mt-6 mb-3">
        <View className="flex-row items-center justify-between">
          <View className="flex-1">
            <Text className="text-sm font-medium text-muted-foreground">{t("home.hello")}</Text>
            <Text className="mt-0.5 text-3xl font-bold">{user?.firstname ?? "there"}</Text>
          </View>
          <Avatar alt={user?.firstname ?? "?"}>
            <AvatarFallback>
              <Text className="font-semibold">{(user?.firstname ?? "?")[0]?.toUpperCase()}</Text>
            </AvatarFallback>
          </Avatar>
        </View>
      </View>

      <FlatList
        data={subjects}
        keyExtractor={(item) => item.id}
        contentContainerClassName="gap-3 pb-32"
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />}
        ListHeaderComponent={
          <>
            <Card className="mb-3 bg-primary/5">
              <CardContent className="gap-4">
                <View className="flex-row items-center gap-4">
                  <View className="size-13 items-center justify-center rounded-full bg-primary/15">
                    <LightningIcon size={26} color={scheme.primary} weight="fill" />
                  </View>
                  <View className="flex-1">
                    <Text className="text-sm font-medium text-muted-foreground">{t("home.todaysMission")}</Text>
                    <Text className="mt-0.5 text-lg font-semibold">
                      {dueCount > 0 ? tn("home.cardsDue", dueCount) : t("home.allCaughtUp")}
                    </Text>
                    <Text className="text-xs text-muted-foreground">
                      {dueCount > 0 ? t("home.streakBody") : t("home.nothingDueBody")}
                    </Text>
                  </View>
                </View>
                <Button onPress={() => router.push("/(tabs)/cards")}>
                  <Text>{dueCount > 0 ? t("home.continueReviewing") : t("home.reviewAnyway")}</Text>
                </Button>
              </CardContent>
            </Card>

            <Text className="mb-1 text-lg font-semibold">{t("home.yourSubjects")}</Text>
          </>
        }
        ListEmptyComponent={
          !isLoading ? (
            <Card className="mt-3">
              <CardContent className="items-center gap-2 py-8">
                <Text className="text-base font-semibold">{t("home.noSubjectsTitle")}</Text>
                <Text className="text-center text-sm text-muted-foreground">{t("home.noSubjectsBody")}</Text>
                <Button variant="secondary" onPress={() => router.push("/subject/new")} className="mt-2">
                  <Text>{t("home.newSubject")}</Text>
                </Button>
              </CardContent>
            </Card>
          ) : null
        }
        ListFooterComponent={
          subjects.length > 0 ? (
            <Button variant="secondary" onPress={() => router.push("/subject/new")} className="mt-2">
              <Text>{t("home.newSubject")}</Text>
            </Button>
          ) : null
        }
        renderItem={({ item }) => {
          const stats = analyticsBySubject.get(item.id);
          const mastery = stats?.average_mastery ?? null;
          return (
            <Pressable onPress={() => router.push(`/subject/${item.id}`)}>
              <Card>
                <CardContent className="gap-3">
                  <View className="flex-row items-center gap-3">
                    <Avatar alt={item.name}>
                      <AvatarFallback>
                        <Text className="font-semibold">{item.name.slice(0, 2).toUpperCase()}</Text>
                      </AvatarFallback>
                    </Avatar>
                    <View className="flex-1">
                      <Text className="font-semibold">{item.name}</Text>
                      {stats ? (
                        <Text className="text-xs text-muted-foreground">
                          {t("home.conceptsPracticed", { practiced: stats.concepts_practiced, total: stats.concepts_total })}
                        </Text>
                      ) : (
                        <Text className="text-xs text-muted-foreground">{t("home.noDocumentsYet")}</Text>
                      )}
                    </View>
                    <Text className="text-lg font-semibold text-primary">
                      {mastery !== null ? `${Math.round(mastery)}%` : "—"}
                    </Text>
                  </View>
                  <View className="h-1.5 overflow-hidden rounded-full bg-muted">
                    <View className="h-full rounded-full bg-primary" style={{ width: `${Math.max(4, mastery ?? 4)}%` }} />
                  </View>
                  {stats && stats.flashcards_due_count > 0 ? (
                    <View className="self-start rounded-full bg-primary/10 px-2 py-0.5">
                      <Text className="text-xs font-medium text-primary">{tn("home.dueTag", stats.flashcards_due_count)}</Text>
                    </View>
                  ) : null}
                </CardContent>
              </Card>
            </Pressable>
          );
        }}
      />

      <Pressable
        onPress={openCoach}
        className="absolute right-5 bottom-24 size-15 items-center justify-center rounded-full bg-primary shadow-lg"
      >
        <ChatCircleDotsIcon size={24} color={scheme.primaryForeground} weight="fill" />
      </Pressable>

      {pickerOpen ? (
        <>
          <Pressable className="absolute inset-0 bg-black/40" onPress={() => setPickerOpen(false)} />
          <View className="absolute right-0 bottom-0 left-0 gap-2 rounded-t-2xl bg-popover p-5">
            <View className="mb-4 h-1.5 w-11 self-center rounded-full bg-border" />
            <Text className="mb-3 text-2xl font-bold">{t("home.talkAboutWhich")}</Text>
            {subjects.map((s) => (
              <Pressable
                key={s.id}
                onPress={() => {
                  setPickerOpen(false);
                  router.push(`/coach/${s.id}`);
                }}
                className={cn("rounded-lg bg-input/30 px-4 py-3")}
              >
                <Text className="font-semibold">{s.name}</Text>
              </Pressable>
            ))}
          </View>
        </>
      ) : null}
    </Screen>
  );
}
