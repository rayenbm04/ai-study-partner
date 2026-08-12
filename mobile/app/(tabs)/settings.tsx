import { CheckCircleIcon, PlusIcon } from "phosphor-react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, Platform, Pressable, ScrollView, Switch, useColorScheme, View } from "react-native";

import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { accountApi, subjectPacksApi } from "../../lib/api";
import type { AppliedSubjectPack } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { confirmDestructiveAction } from "../../lib/confirm";
import { languageNames, type Language } from "../../lib/i18n/translations";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { useTheme } from "../../lib/theme-context";
import { cn } from "../../lib/utils";

function packLabel(pack: AppliedSubjectPack): string {
  const parts = [pack.country_name, pack.academic_level_name];
  if (pack.section_name) parts.push(pack.section_name);
  return parts.filter(Boolean).join(" · ");
}

const LANGUAGE_OPTIONS: Language[] = ["en", "fr", "ar"];

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const { isDark, setDark } = useTheme();
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { language, setLanguage, t, tn } = useLanguage();
  const router = useRouter();
  const [isResetting, setIsResetting] = useState(false);
  const [packs, setPacks] = useState<AppliedSubjectPack[]>([]);
  const [isLoadingPacks, setIsLoadingPacks] = useState(true);
  const [removingPackKey, setRemovingPackKey] = useState<string | null>(null);

  function handleSelectLanguage(next: Language) {
    const restartRequired = setLanguage(next);
    if (!restartRequired) return;
    const message = t("settings.languageRestartNote");
    if (Platform.OS === "web") {
      window.alert(message);
    } else {
      Alert.alert(t("settings.language"), message);
    }
  }

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoadingPacks(true);
      subjectPacksApi
        .listAppliedPacks()
        .then((result) => !cancelled && setPacks(result))
        .finally(() => !cancelled && setIsLoadingPacks(false));
      return () => {
        cancelled = true;
      };
    }, [])
  );

  async function handleRemovePack(pack: AppliedSubjectPack) {
    const key = `${pack.academic_level_id}:${pack.section_id ?? ""}`;
    const confirmed = await confirmDestructiveAction(
      t("settings.removePackTitle"),
      tn("settings.removePackBody", pack.subject_count, { pack: packLabel(pack) }),
      t("settings.remove"),
      t("common.cancel")
    );
    if (!confirmed) return;
    setRemovingPackKey(key);
    try {
      await subjectPacksApi.removePack({ academicLevelId: pack.academic_level_id, sectionId: pack.section_id });
      setPacks((prev) => prev.filter((p) => p !== pack));
    } finally {
      setRemovingPackKey(null);
    }
  }

  async function handleResetAccount() {
    const confirmed = await confirmDestructiveAction(
      t("settings.resetAccountTitle"),
      t("settings.resetAccountConfirmBody"),
      t("settings.resetAccount"),
      t("common.cancel")
    );
    if (!confirmed) return;
    setIsResetting(true);
    try {
      await accountApi.resetAccount();
      router.replace("/(tabs)");
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <Screen>
      <ScrollView contentContainerClassName="pb-16">
        <Text className="mt-6 mb-8 text-3xl font-bold">{t("settings.title")}</Text>

        <Card>
          <CardContent className="flex-row items-center gap-4">
            <Avatar alt={user?.firstname ?? "?"} className="size-14">
              <AvatarFallback>
                <Text className="text-lg font-semibold">{(user?.firstname ?? "?")[0]?.toUpperCase()}</Text>
              </AvatarFallback>
            </Avatar>
            <View className="flex-1">
              <Text className="text-base font-semibold">
                {user?.firstname} {user?.lastname}
              </Text>
              <Text className="mt-1 text-xs text-muted-foreground">{user?.email}</Text>
            </View>
          </CardContent>
        </Card>

        <Text className="mt-8 mb-2 ml-1 text-sm font-medium text-muted-foreground">{t("settings.appearance")}</Text>
        <Card className="overflow-hidden py-0">
          <View className="flex-row items-center justify-between px-5 py-4">
            <Text className="flex-1">{t("settings.darkMode")}</Text>
            <Switch value={isDark} onValueChange={setDark} trackColor={{ false: scheme.border, true: scheme.primary }} thumbColor="#FFFFFF" />
          </View>
        </Card>

        <Text className="mt-8 mb-2 ml-1 text-sm font-medium text-muted-foreground">{t("settings.language")}</Text>
        <Card className="overflow-hidden py-0">
          {LANGUAGE_OPTIONS.map((option, index) => (
            <Pressable
              key={option}
              onPress={() => handleSelectLanguage(option)}
              className={cn(
                "flex-row items-center justify-between px-5 py-4",
                index < LANGUAGE_OPTIONS.length - 1 && "border-b border-border"
              )}
            >
              <Text className="flex-1">{languageNames[option]}</Text>
              {language === option ? <CheckCircleIcon size={22} color={scheme.primary} weight="fill" /> : null}
            </Pressable>
          ))}
        </Card>

        <View className="mt-8 mb-2 flex-row items-center justify-between">
          <Text className="ml-1 text-sm font-medium text-muted-foreground">{t("settings.subjects")}</Text>
          <IconButton
            icon={PlusIcon}
            size={32}
            onPress={() => router.push({ pathname: "/subject-pack/new", params: { returnTo: "/(tabs)/settings" } })}
          />
        </View>
        {isLoadingPacks ? (
          <ActivityIndicator color={scheme.primary} className="mt-3" />
        ) : packs.length === 0 ? (
          <Card>
            <CardContent>
              <Text className="text-muted-foreground">{t("settings.noPacks")}</Text>
            </CardContent>
          </Card>
        ) : (
          <Card className="overflow-hidden py-0">
            {packs.map((pack, index) => {
              const key = `${pack.academic_level_id}:${pack.section_id ?? ""}`;
              return (
                <View
                  key={key}
                  className={cn(
                    "flex-row items-center justify-between px-5 py-4",
                    index < packs.length - 1 && "border-b border-border"
                  )}
                >
                  <View className="flex-1">
                    <Text>{packLabel(pack)}</Text>
                    <Text className="text-xs text-muted-foreground">{tn("settings.subjectCount", pack.subject_count)}</Text>
                  </View>
                  {removingPackKey === key ? (
                    <ActivityIndicator color={scheme.destructive} size="small" />
                  ) : (
                    <Button variant="ghost" onPress={() => handleRemovePack(pack)}>
                      <Text>{t("settings.remove")}</Text>
                    </Button>
                  )}
                </View>
              );
            })}
          </Card>
        )}

        <Text className="mt-8 mb-2 ml-1 text-sm font-medium text-destructive">{t("settings.dangerZone")}</Text>
        <Card>
          <CardContent>
            <Text className="mb-4 text-muted-foreground">{t("settings.resetAccountBody")}</Text>
            <Button variant="secondary" onPress={handleResetAccount} disabled={isResetting}>
              {isResetting ? <ActivityIndicator color={scheme.foreground} /> : null}
              <Text>{t("settings.resetAccount")}</Text>
            </Button>
          </CardContent>
        </Card>

        <Button variant="secondary" onPress={logout} className="mt-10 mb-28">
          <Text>{t("settings.signOut")}</Text>
        </Button>
      </ScrollView>
    </Screen>
  );
}
