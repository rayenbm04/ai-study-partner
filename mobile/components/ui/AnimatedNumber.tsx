import { useEffect, useRef, useState } from "react";
import type { TextStyle } from "react-native";

import { Text } from "./text";

/** Counts up from 0 to `value` on mount/change — same easeOutQuart timing
 * used by RingProgress and RadarChart's reveal, kept in sync visually. */
export function AnimatedNumber({
  value,
  duration = 900,
  suffix = "",
  style,
}: {
  value: number;
  duration?: number;
  suffix?: string;
  style?: TextStyle;
}) {
  const [count, setCount] = useState(0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const startedAt = Date.now();
    const tick = () => {
      const t = Math.min(1, (Date.now() - startedAt) / duration);
      const eased = 1 - Math.pow(1 - t, 4);
      setCount(Math.round(eased * value));
      if (t < 1) frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [value, duration]);

  return (
    <Text style={style}>
      {count}
      {suffix}
    </Text>
  );
}
