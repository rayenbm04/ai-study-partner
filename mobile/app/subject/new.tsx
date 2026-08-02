import { useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, View } from "react-native";

import { Button, Screen, Text, TextField } from "../../components/ui";
import { spacing } from "../../constants/theme";
import { ApiError, subjectsApi } from "../../lib/api";

export default function NewSubjectScreen() {
  const router = useRouter();
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
      setError(err instanceof ApiError ? err.message : "Couldn't create the subject. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="display">New subject</Text>
      </View>
      <TextField label="Name" value={name} onChangeText={setName} placeholder="e.g. Organic Chemistry" />
      <TextField
        label="Description (optional)"
        value={description}
        onChangeText={setDescription}
        multiline
        style={styles.field}
      />
      {error ? (
        <Text variant="caption" style={styles.error}>
          {error}
        </Text>
      ) : null}
      <Button label="Create subject" onPress={handleCreate} loading={isSubmitting} disabled={!name.trim()} style={styles.action} />
      <Button label="Cancel" variant="ghost" onPress={() => router.back()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    marginTop: spacing.lg,
    marginBottom: spacing.xl,
  },
  field: {
    marginTop: spacing.lg,
  },
  action: {
    marginTop: spacing.xl,
  },
  error: {
    marginTop: spacing.md,
  },
});
