import { useRouter } from "expo-router";
import { XIcon } from "phosphor-react-native";
import { useState } from "react";
import { ActivityIndicator, useColorScheme, View } from "react-native";

import { Button } from "../../components/ui/button";
import { IconButton } from "../../components/ui/IconButton";
import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { TextField } from "../../components/ui/TextField";
import { ApiError, subjectsApi } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";

export default function NewSubjectScreen() {
  const router = useRouter();
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleCreate() {
    setError(null);
    setIsSubmitting(true);
    try {
      const subject = await subjectsApi.createSubject({
        name: name.trim(),
        description: description.trim() || null,
      });
      router.replace(`/subject/${subject.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("subjectNew.createError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View className="mt-2">
        <IconButton icon={XIcon} onPress={() => router.back()} />
      </View>
      <View className="mt-6 mb-8">
        <Text className="text-3xl font-bold">{t("subjectNew.title")}</Text>
      </View>
      <TextField label={t("subjectNew.name")} value={name} onChangeText={setName} placeholder={t("subjectNew.namePlaceholder")} />
      <TextField
        label={t("subjectNew.descriptionOptional")}
        value={description}
        onChangeText={setDescription}
        multiline
        className="mt-4"
      />
      {error ? <Text className="mt-3 text-sm text-destructive">{error}</Text> : null}
      <Button onPress={handleCreate} disabled={isSubmitting || !name.trim()} className="mt-6">
        {isSubmitting ? <ActivityIndicator color={scheme.primaryForeground} /> : null}
        <Text>{t("subjectNew.createSubject")}</Text>
      </Button>
    </Screen>
  );
}
