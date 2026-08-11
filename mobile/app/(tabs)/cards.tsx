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
import { ActivityIndicator, Animated, Pressable, useColorScheme, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { Screen } from "../../components/ui/Screen";
import { Text } from "../../components/ui/text";
import { flashcardsApi } from "../../lib/api";
import type { Flashcard } from "../../lib/api";
import { useLanguage } from "../../lib/language-context";
import { THEME } from "../../lib/theme";
import { cn } from "../../lib/utils";

export default function CardsScreen() {
  const scheme = useColorScheme() === "dark" ? THEME.dark : THEME.light;
  const { t, tn } = useLanguage();
  const GRADES: { label: string; sub: string; quality: number; tone: "bad" | "neutral" | "good" }[] = [
    { label: t("cards.gradeAgain"), sub: t("cards.gradeAgainSub"), quality: 1, tone: "bad" },
    { label: t("cards.gradeGood"), sub: t("cards.gradeGoodSub"), quality: 3, tone: "neutral" },
    { label: t("cards.gradeEasy"), sub: t("cards.gradeEasySub"), quality: 5, tone: "good" },
  ];
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
        <View className="flex-1 items-center justify-center px-8">
          <ActivityIndicator color={scheme.primary} />
        </View>
      </Screen>
    );
  }

  const card = cards[index];
  const done = !card;

  if (cards.length === 0) {
    return (
      <Screen>
        <View className="flex-1 items-center justify-center px-8">
          <View className="mb-6 size-21 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950">
            <Ionicons name="checkmark" size={40} color={scheme.chart1} />
          </View>
          <Text className="text-center text-3xl font-bold">{t("cards.nothingDueTitle")}</Text>
          <Text className="mt-3 text-center text-muted-foreground">{t("cards.nothingDueBody")}</Text>
        </View>
      </Screen>
    );
  }

  if (done) {
    return (
      <Screen>
        <View className="flex-1 items-center justify-center px-8">
          <View className="mb-6 size-21 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-950">
            <Ionicons name="checkmark" size={40} color={scheme.chart1} />
          </View>
          <Text className="text-center text-3xl font-bold">{t("cards.deckComplete")}</Text>
          <Text className="mt-3 text-center text-muted-foreground">{tn("cards.reviewed", reviewed)}</Text>
        </View>
      </Screen>
    );
  }

  const frontRotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "180deg"] });
  const backRotate = spin.interpolate({ inputRange: [0, 1], outputRange: ["180deg", "360deg"] });

  return (
    <Screen>
      <View className="mt-4 flex-row items-center gap-3">
        <View className="h-2 flex-1 overflow-hidden rounded-full bg-border">
          <View className="h-full rounded-full bg-primary" style={{ width: `${(reviewed / cards.length) * 100}%` }} />
        </View>
        <Text className="text-sm font-medium text-muted-foreground">
          {index + 1}/{cards.length}
        </Text>
      </View>

      <View className="flex-1 justify-center py-4">
        <Pressable onPress={flip} className="h-90">
          <Animated.View
            className="absolute size-full justify-between rounded-2xl bg-card p-6 shadow-lg shadow-black/10"
            style={{ backfaceVisibility: "hidden", transform: [{ rotateY: frontRotate }] }}
          >
            <Text className="text-sm font-medium text-primary">{card.difficulty.toUpperCase()}</Text>
            <Text className="flex-1 text-center text-2xl font-bold" style={{ textAlignVertical: "center" }}>
              {card.question}
            </Text>
            <Text className="text-xs text-muted-foreground">{t("cards.tapToReveal")}</Text>
          </Animated.View>
          <Animated.View
            className="absolute size-full justify-start gap-3 rounded-2xl bg-primary p-6 shadow-lg shadow-black/10"
            style={{ backfaceVisibility: "hidden", transform: [{ rotateY: backRotate }] }}
          >
            <Text className="text-sm font-medium text-primary-foreground/80">{t("cards.answer")}</Text>
            <Text className="flex-1 text-lg text-primary-foreground">{card.answer}</Text>
          </Animated.View>
        </Pressable>
      </View>

      {flipped ? (
        <View className="mb-28 flex-row gap-2">
          {GRADES.map((g) => (
            <Pressable
              key={g.label}
              onPress={() => grade(g.quality)}
              disabled={isSubmitting}
              className={cn(
                "flex-1 items-center rounded-xl py-3 shadow-sm shadow-black/5",
                g.tone === "bad" ? "bg-destructive/10" : g.tone === "good" ? "bg-emerald-100 dark:bg-emerald-950" : "bg-card"
              )}
            >
              <Text
                className={cn(
                  "font-semibold",
                  g.tone === "bad" ? "text-destructive" : g.tone === "good" ? "text-emerald-700 dark:text-emerald-300" : "text-foreground"
                )}
              >
                {g.label}
              </Text>
              <Text className="mt-0.5 text-xs text-muted-foreground">{g.sub}</Text>
            </Pressable>
          ))}
        </View>
      ) : (
        <View className="mb-28 h-16 flex-row items-center justify-center gap-2">
          <Ionicons name="swap-horizontal" size={16} color={scheme.mutedForeground} />
          <Text className="ml-1 text-xs text-muted-foreground">{t("cards.tapToFlip")}</Text>
        </View>
      )}
    </Screen>
  );
}
