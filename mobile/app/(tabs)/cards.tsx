/**
 * Flashcard review — cross-subject queue of everything due right now
 * (matches GET /flashcards/due), flip-to-reveal, then a 3-button SM-2
 * confidence grade. Mapped onto the 0-5 SM-2 quality scale the backend
 * expects: "Again" -> 1 (forgot), "Good" -> 3 (recalled with effort),
 * "Easy" -> 5 (recalled instantly) — see FlashcardReviewRequest on the
 * backend for the full 0-5 semantics.
 */
import { useCallback, useRef, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ActivityIndicator, Animated, Pressable, StyleSheet, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Screen, Text } from "../../components/ui";
import { fontFamilies, radii, spacing } from "../../constants/theme";
import { flashcardsApi } from "../../lib/api";
import type { Flashcard } from "../../lib/api";
import { useTheme } from "../../lib/theme-context";

const GRADES: { label: string; sub: string; quality: number; tone: "bad" | "neutral" | "good" }[] = [
  { label: "Again", sub: "in 10 min", quality: 1, tone: "bad" },
  { label: "Good", sub: "in 2 days", quality: 3, tone: "neutral" },
  { label: "Easy", sub: "in 9 days", quality: 5, tone: "good" },
];

export default function CardsScreen() {
  const { colors } = useTheme();
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviewed, setReviewed] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const spin = useRef(new Animated.Value(0)).current;

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      setIsLoading(true);
      setIndex(0);
      setFlipped(false);
      setReviewed(0);
      spin.setValue(0);
      flashcardsApi.listDueFlashcards().then((due) => {
        if (!cancelled) setCards(due);
      }).finally(() => !cancelled && setIsLoading(false));
      return () => {
        cancelled = true;
      };
    }, [])
  );

  function flip() {
    Animated.timing(spin, {
      toValue: flipped ? 0 : 1,
      duration: 450,
      useNativeDriver: true,
    }).start();
    setFlipped(!flipped);
  }

  async function grade(quality: number) {
    const card = cards[index];
    if (!card || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await flashcardsApi.reviewFlashcard(card.id, quality);
      setReviewed((r) => r + 1);
      spin.setValue(0);
      setFlipped(false);
      setIndex((i) => i + 1);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  const card = cards[index];
  const done = !card;

  if (cards.length === 0) {
    return (
      <Screen>
        <View style={styles.center}>
          <View style={[styles.doneIcon, { backgroundColor: colors.sageLight }]}>
            <Ionicons name="checkmark" size={40} color={colors.sageDark} />
          </View>
          <Text variant="display" style={styles.centerTitle}>
            Nothing due
          </Text>
          <Text variant="body" style={[styles.centerBody, { color: colors.textSecondary }]}>
            No flashcards need review right now — check back later or generate more from a subject's documents.
          </Text>
        </View>
      </Screen>
    );
  }

  if (done) {
    return (
      <Screen>
        <View style={styles.center}>
          <View style={[styles.doneIcon, { backgroundColor: colors.sageLight }]}>
            <Ionicons name="checkmark" size={40} color={colors.sageDark} />
          </View>
          <Text variant="display" style={styles.centerTitle}>
            Deck complete
          </Text>
          <Text variant="body" style={[styles.centerBody, { color: colors.textSecondary }]}>
            {reviewed} card{reviewed === 1 ? "" : "s"} reviewed.
          </Text>
        </View>
      </Screen>
    );
  }

  const frontRotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "180deg"] });
  const backRotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["180deg", "360deg"] });

  return (
    <Screen>
      <View style={styles.progressRow}>
        <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
          <View
            style={[
              styles.progressFill,
              { width: `${(reviewed / cards.length) * 100}%`, backgroundColor: colors.accent },
            ]}
          />
        </View>
        <Text variant="label">
          {index + 1}/{cards.length}
        </Text>
      </View>

      <View style={styles.stage}>
        <Pressable onPress={flip} style={styles.flipArea}>
          <Animated.View
            style={[
              styles.face,
              { backgroundColor: colors.surface, shadowColor: colors.shadowStrong, transform: [{ rotateY: frontRotate }] },
            ]}
          >
            <Text variant="label" style={{ color: colors.accentDark }}>
              {card.difficulty.toUpperCase()}
            </Text>
            <Text variant="display" style={styles.faceQuestion}>
              {card.question}
            </Text>
            <Text variant="caption">Tap the card to reveal</Text>
          </Animated.View>
          <Animated.View
            style={[
              styles.face,
              styles.faceBack,
              { backgroundColor: colors.cardBack, shadowColor: colors.shadowStrong, transform: [{ rotateY: backRotate }] },
            ]}
          >
            <Text variant="label" style={{ color: colors.accent }}>
              ANSWER
            </Text>
            <Text variant="body" style={[styles.faceAnswer, { color: colors.cardBackText }]}>
              {card.answer}
            </Text>
          </Animated.View>
        </Pressable>
      </View>

      {flipped ? (
        <View style={styles.gradeRow}>
          {GRADES.map((g) => (
            <Pressable
              key={g.label}
              onPress={() => grade(g.quality)}
              disabled={isSubmitting}
              style={[
                styles.gradeButton,
                {
                  backgroundColor: g.tone === "bad" ? colors.errorLight : g.tone === "good" ? colors.sageLight : colors.surface,
                  shadowColor: colors.shadow,
                },
              ]}
            >
              <Text
                style={{
                  fontFamily: fontFamilies.semibold,
                  color: g.tone === "bad" ? colors.error : g.tone === "good" ? colors.sageDark : colors.textPrimary,
                }}
              >
                {g.label}
              </Text>
              <Text variant="caption" style={styles.gradeSub}>
                {g.sub}
              </Text>
            </Pressable>
          ))}
        </View>
      ) : (
        <View style={styles.hint}>
          <Ionicons name="swap-horizontal" size={16} color={colors.textMuted} />
          <Text variant="caption" style={styles.hintText}>
            Tap to flip
          </Text>
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
  },
  doneIcon: {
    width: 84,
    height: 84,
    borderRadius: radii.full,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.xl,
  },
  centerTitle: {
    textAlign: "center",
  },
  centerBody: {
    textAlign: "center",
    marginTop: spacing.md,
  },
  progressRow: {
    marginTop: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  progressTrack: {
    flex: 1,
    height: 8,
    borderRadius: radii.full,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: radii.full,
  },
  stage: {
    flex: 1,
    justifyContent: "center",
    paddingVertical: spacing.lg,
  },
  flipArea: {
    height: 360,
  },
  face: {
    position: "absolute",
    width: "100%",
    height: "100%",
    borderRadius: radii.xl,
    padding: spacing.xl,
    backfaceVisibility: "hidden",
    justifyContent: "space-between",
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 1,
    shadowRadius: 30,
    elevation: 6,
  },
  faceBack: {
    justifyContent: "flex-start",
    gap: spacing.md,
  },
  faceQuestion: {
    flex: 1,
    textAlignVertical: "center",
  },
  faceAnswer: {
    flex: 1,
  },
  gradeRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginBottom: 110,
  },
  gradeButton: {
    flex: 1,
    borderRadius: radii.lg,
    paddingVertical: spacing.md,
    alignItems: "center",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 18,
    elevation: 3,
  },
  gradeSub: {
    marginTop: spacing.xs / 2,
  },
  hint: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    height: 66,
    marginBottom: 110,
  },
  hintText: {
    marginLeft: spacing.xs,
  },
});
