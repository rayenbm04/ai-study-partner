import { View, type StyleProp, type ViewStyle } from "react-native";

import { cn } from "../../lib/utils";
import { Text } from "./text";

type Tone = "accent" | "sage" | "neutral" | "error";

const TONE_CLASSES: Record<Tone, { bg: string; fg: string }> = {
  accent: { bg: "bg-primary/10", fg: "text-primary" },
  sage: { bg: "bg-emerald-100 dark:bg-emerald-950", fg: "text-emerald-700 dark:text-emerald-300" },
  neutral: { bg: "bg-muted", fg: "text-muted-foreground" },
  error: { bg: "bg-destructive/10", fg: "text-destructive" },
};

/** Small pill label — due-count badges, mastery chips, citation chips,
 * document-status chips. */
export function Tag({ label, tone = "neutral", style }: { label: string; tone?: Tone; style?: StyleProp<ViewStyle> }) {
  const t = TONE_CLASSES[tone];
  return (
    <View className={cn("self-start rounded-full px-3 py-1", t.bg)} style={style}>
      <Text className={cn("text-xs font-semibold", t.fg)}>{label}</Text>
    </View>
  );
}
