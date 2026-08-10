import { Ionicons } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import { radii, spacing } from "../../constants/theme";
import { schoolsApi } from "../../lib/api";
import type { School } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { useTheme } from "../../lib/theme-context";
import { Button } from "./Button";
import { Text } from "./Text";
import { TextField } from "./TextField";

/** Search-or-create picker for the schools catalog (backend/app/domain/entities/school.py) —
 * used at registration instead of a free-text field. No school-catalog admin
 * tooling exists, so "add it if it's missing" is built into the picker
 * itself, same "not in list" fallback the original registration spec called
 * for. */
export function SchoolPickerField({
  label,
  value,
  onChange,
  placeholder,
  style,
}: {
  label?: string;
  value: School | null;
  onChange: (school: School | null) => void;
  placeholder?: string;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors } = useTheme();
  const { t } = useLanguage();

  const [visible, setVisible] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<School[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newCountry, setNewCountry] = useState("");
  const [newCity, setNewCity] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (!visible) return;
    setIsLoading(true);
    const handle = setTimeout(() => {
      schoolsApi
        .searchSchools(query)
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setIsLoading(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [query, visible]);

  function open() {
    setQuery("");
    setShowCreateForm(false);
    setNewCountry("");
    setNewCity("");
    setVisible(true);
  }

  function select(school: School) {
    onChange(school);
    setVisible(false);
  }

  async function handleCreate() {
    if (!query.trim()) return;
    setIsCreating(true);
    try {
      const school = await schoolsApi.createSchool({
        name: query.trim(),
        country: newCountry.trim() || null,
        city: newCity.trim() || null,
      });
      select(school);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <View style={style}>
      {label ? (
        <Text variant="label" style={styles.label}>
          {label}
        </Text>
      ) : null}
      <Pressable
        onPress={open}
        style={[styles.field, { backgroundColor: colors.surfaceAlt }]}
      >
        <Text variant="body" style={{ color: value ? colors.textPrimary : colors.textMuted }}>
          {value ? value.name : placeholder}
        </Text>
        <Ionicons name="search" size={18} color={colors.textSecondary} />
      </Pressable>

      <Modal visible={visible} transparent animationType="fade" onRequestClose={() => setVisible(false)}>
        <Pressable style={styles.overlay} onPress={() => setVisible(false)}>
          <Pressable style={[styles.sheet, { backgroundColor: colors.surface }]} onPress={(e) => e.stopPropagation()}>
            <View style={styles.sheetHeader}>
              <Text variant="subtitle">{t("auth.schoolPickerTitle")}</Text>
              <Pressable onPress={() => setVisible(false)} hitSlop={8}>
                <Ionicons name="close" size={22} color={colors.textPrimary} />
              </Pressable>
            </View>

            <TextField
              value={query}
              onChangeText={(text) => {
                setQuery(text);
                setShowCreateForm(false);
              }}
              placeholder={t("auth.schoolSearchPlaceholder")}
              autoFocus
              style={styles.searchField}
            />

            <ScrollView style={styles.results} keyboardShouldPersistTaps="handled">
              {isLoading ? (
                <ActivityIndicator color={colors.accent} style={styles.loading} />
              ) : (
                <>
                  {results.map((school) => (
                    <Pressable key={school.id} onPress={() => select(school)} style={styles.resultRow}>
                      <Text variant="body">{school.name}</Text>
                      {school.city || school.country ? (
                        <Text variant="caption">{[school.city, school.country].filter(Boolean).join(", ")}</Text>
                      ) : null}
                    </Pressable>
                  ))}
                  {results.length === 0 && !query.trim() ? (
                    <Text variant="caption" style={styles.empty}>
                      {t("auth.schoolSearchHint")}
                    </Text>
                  ) : null}
                </>
              )}
            </ScrollView>

            {query.trim() ? (
              showCreateForm ? (
                <View style={styles.createForm}>
                  <TextField
                    label={t("auth.schoolCountry")}
                    value={newCountry}
                    onChangeText={setNewCountry}
                    style={styles.createField}
                  />
                  <TextField
                    label={t("auth.schoolCity")}
                    value={newCity}
                    onChangeText={setNewCity}
                    style={styles.createField}
                  />
                  <Button
                    label={t("auth.schoolCreateConfirm", { name: query.trim() })}
                    onPress={handleCreate}
                    loading={isCreating}
                    style={styles.createField}
                  />
                </View>
              ) : (
                <Pressable onPress={() => setShowCreateForm(true)} style={styles.addRow}>
                  <Ionicons name="add-circle-outline" size={20} color={colors.accentDark} />
                  <Text variant="body" style={{ color: colors.accentDark }}>
                    {t("auth.schoolNotListed", { name: query.trim() })}
                  </Text>
                </Pressable>
              )
            ) : null}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    marginBottom: spacing.xs,
    marginLeft: spacing.sm,
  },
  field: {
    minHeight: 56,
    borderRadius: radii.full,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  overlay: {
    flex: 1,
    backgroundColor: "rgba(20,18,17,0.44)",
    justifyContent: "flex-end",
  },
  sheet: {
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    padding: spacing.lg,
    maxHeight: "75%",
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.md,
  },
  searchField: {
    marginBottom: spacing.md,
  },
  results: {
    maxHeight: 260,
  },
  loading: {
    marginTop: spacing.lg,
  },
  resultRow: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    gap: spacing.xs,
  },
  empty: {
    textAlign: "center",
    marginTop: spacing.lg,
  },
  addRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    marginTop: spacing.sm,
  },
  createForm: {
    marginTop: spacing.sm,
  },
  createField: {
    marginTop: spacing.sm,
  },
});
