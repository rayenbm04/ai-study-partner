import { View } from "react-native";

import { cn } from "../../lib/utils";

/** A row of segments (one per quiz question, one per plan day, etc.) rather
 * than a single continuous bar — matches the step-by-step exercise pattern
 * from the Brilliant reference screens, and reads more clearly as "3 of 8
 * done" than a plain percentage fill would. */
export function ProgressBar({ total, completed, className }: { total: number; completed: number; className?: string }) {
  return (
    <View className={cn("flex-row gap-1", className)}>
      {Array.from({ length: total }).map((_, index) => (
        <View key={index} className={cn("h-1.5 flex-1 rounded-full", index < completed ? "bg-primary" : "bg-border")} />
      ))}
    </View>
  );
}
