import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, ScrollView, Switch, StyleSheet, View } from "react-native";

import { Avatar, Button, Card, IconButton, Screen, Text } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { accountApi, subjectPacksApi } from "../../lib/api";
import type { AppliedSubjectPack } from "../../lib/api";
import { useAuth } from "../../lib/auth-context";
import { confirmDestructiveAction } from "../../lib/confirm";
import { useTheme } from "../../lib/theme-context";

function packLabel(pack: AppliedSubjectPack): string {
  const parts = [pack.country_name, pack.academic_level_name];
  if (pack.section_name) parts.push(pack.section_name);
  return parts.filter(Boolean).join(" · ");
}

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const { colors, isDark, setDark } = useTheme();
  const router = useRouter();
  const [isResetting, setIsResetting] = useState(false);
  const [packs, setPacks] = useState<AppliedSubjectPack[]>([]);
  const [isLoadingPacks, setIsLoadingPacks] = useState(true);
  const [removingPackKey, setRemovingPackKey] = useState<string | null>(null);

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
      "Remove this pack?",
      `This archives the ${pack.subject_count} subject${pack.subject_count === 1 ? "" : "s"} it added (${packLabel(pack)}). Anything you've uploaded for them stays put.`,
      "Remove"
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
      "Reset your account?",
      "This permanently deletes every subject, document, quiz, flashcard, and progress record. Your login stays active. This can't be undone.",
      "Reset"
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
      <ScrollView contentContainerStyle={styles.scroll}>
      <View style={styles.header}>
        <Text variant="display">Settings</Text>
      </View>

      <Card style={styles.profileCard}>
        <Avatar label={user?.firstname ?? "?"} size={56} />
        <View style={styles.profileText}>
          <Text variant="subtitle">
            {user?.firstname} {user?.lastname}
          </Text>
          <Text variant="caption" style={{ marginTop: 4 }}>
            {user?.email}
          </Text>
        </View>
      </Card>

      <Text variant="label" style={styles.sectionLabel}>
        Appearance
      </Text>
      <Card style={styles.rowsCard}>
        <View style={styles.row}>
          <Text variant="body" style={styles.rowLabel}>
            Dark mode
          </Text>
          <Switch
            value={isDark}
            onValueChange={setDark}
            trackColor={{ false: colors.border, true: colors.accent }}
            thumbColor="#FFFFFF"
          />
        </View>
      </Card>

      <View style={styles.sectionHeaderRow}>
        <Text variant="label" style={[styles.sectionLabel, styles.sectionLabelInline]}>
          Subjects
        </Text>
        <IconButton
          name="add"
          size={32}
          onPress={() => router.push({ pathname: "/subject-pack/new", params: { returnTo: "/(tabs)/settings" } })}
        />
      </View>
      {isLoadingPacks ? (
        <ActivityIndicator color={colors.accent} style={styles.packsLoading} />
      ) : packs.length === 0 ? (
        <Card>
          <Text variant="body" style={{ color: colors.textSecondary }}>
            No curriculum packs added yet. Add one to bulk-add every subject for your year.
          </Text>
        </Card>
      ) : (
        <Card style={styles.rowsCard}>
          {packs.map((pack, index) => {
            const key = `${pack.academic_level_id}:${pack.section_id ?? ""}`;
            return (
              <View
                key={key}
                style={[styles.row, index < packs.length - 1 && { borderBottomWidth: 1, borderBottomColor: colors.border }]}
              >
                <View style={styles.rowLabel}>
                  <Text variant="body">{packLabel(pack)}</Text>
                  <Text variant="caption">
                    {pack.subject_count} subject{pack.subject_count === 1 ? "" : "s"}
                  </Text>
                </View>
                {removingPackKey === key ? (
                  <ActivityIndicator color={colors.error} size="small" />
                ) : (
                  <Button label="Remove" variant="ghost" onPress={() => handleRemovePack(pack)} />
                )}
              </View>
            );
          })}
        </Card>
      )}

      <Text variant="label" style={[styles.sectionLabel, { color: colors.error }]}>
        Danger zone
      </Text>
      <Card>
        <Text variant="body" style={{ color: colors.textSecondary, marginBottom: spacing.md }}>
          Permanently delete every subject, document, quiz, flashcard, and progress record. Your
          login stays active.
        </Text>
        <Button label="Reset account" variant="secondary" onPress={handleResetAccount} loading={isResetting} />
      </Card>

      <Button label="Sign out" variant="secondary" onPress={logout} style={styles.signOut} />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: spacing.xxxl,
  },
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.xl,
  },
  sectionHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionLabelInline: {
    marginTop: 0,
    marginBottom: 0,
  },
  packsLoading: {
    marginTop: spacing.md,
  },
  profileCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  profileText: {
    flex: 1,
  },
  sectionLabel: {
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
    marginLeft: spacing.sm,
  },
  rowsCard: {
    padding: 0,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  rowLabel: {
    flex: 1,
  },
  signOut: {
    marginTop: spacing.xxl,
    marginBottom: 110,
  },
});
