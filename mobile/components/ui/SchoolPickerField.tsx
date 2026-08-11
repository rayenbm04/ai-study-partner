import { Ionicons } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  useColorScheme,
  View,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import { schoolsApi } from "../../lib/api";
import type { School } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { Button } from "./button";
import { Text } from "./text";
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
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
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
      {label ? <Text className="mb-1.5 ml-1 text-sm font-medium text-muted-foreground">{label}</Text> : null}
      <Pressable
        onPress={open}
        className="min-h-14 flex-row items-center justify-between rounded-full bg-input/30 px-4"
      >
        <Text className={value ? "text-foreground" : "text-muted-foreground"}>{value ? value.name : placeholder}</Text>
        <Ionicons name="search" size={18} color={scheme.mutedForeground} />
      </Pressable>

      <Modal visible={visible} transparent animationType="fade" onRequestClose={() => setVisible(false)}>
        <Pressable className="flex-1 justify-end bg-black/40" onPress={() => setVisible(false)}>
          <Pressable className="max-h-[75%] rounded-t-2xl bg-popover p-5" onPress={(e) => e.stopPropagation()}>
            <View className="mb-4 flex-row items-center justify-between">
              <Text className="text-base font-semibold">{t("auth.schoolPickerTitle")}</Text>
              <Pressable onPress={() => setVisible(false)} hitSlop={8}>
                <Ionicons name="close" size={22} color={scheme.foreground} />
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
              className="mb-4"
            />

            <ScrollView className="max-h-64" keyboardShouldPersistTaps="handled">
              {isLoading ? (
                <ActivityIndicator color={scheme.primary} className="mt-5" />
              ) : (
                <>
                  {results.map((school) => (
                    <Pressable key={school.id} onPress={() => select(school)} className="gap-1 px-1 py-3">
                      <Text>{school.name}</Text>
                      {school.city || school.country ? (
                        <Text className="text-xs text-muted-foreground">
                          {[school.city, school.country].filter(Boolean).join(", ")}
                        </Text>
                      ) : null}
                    </Pressable>
                  ))}
                  {results.length === 0 && !query.trim() ? (
                    <Text className="mt-5 text-center text-xs text-muted-foreground">
                      {t("auth.schoolSearchHint")}
                    </Text>
                  ) : null}
                </>
              )}
            </ScrollView>

            {query.trim() ? (
              showCreateForm ? (
                <View className="mt-2">
                  <TextField
                    label={t("auth.schoolCountry")}
                    value={newCountry}
                    onChangeText={setNewCountry}
                    className="mt-2"
                  />
                  <TextField label={t("auth.schoolCity")} value={newCity} onChangeText={setNewCity} className="mt-2" />
                  <Button onPress={handleCreate} disabled={isCreating} className="mt-2">
                    {isCreating ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
                    <Text>{t("auth.schoolCreateConfirm", { name: query.trim() })}</Text>
                  </Button>
                </View>
              ) : (
                <Pressable onPress={() => setShowCreateForm(true)} className="mt-2 flex-row items-center gap-2 px-1 py-3">
                  <Ionicons name="add-circle-outline" size={20} color={scheme.primary} />
                  <Text style={{ color: scheme.primary }}>{t("auth.schoolNotListed", { name: query.trim() })}</Text>
                </Pressable>
              )
            ) : null}
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}
