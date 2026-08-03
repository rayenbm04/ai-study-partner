import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { View } from "react-native";
import Svg, { Circle } from "react-native-svg";

const DURATION_MS = 900;

/** Animated ring, driven by a plain requestAnimationFrame loop (same
 * pattern as AnimatedNumber/RadarChart) rather than
 * Animated.createAnimatedComponent(Circle) — that wrapper leaks an
 * RN-internal `collapsable` prop straight onto the real DOM <circle> on
 * web, which React DOM then warns about as an invalid attribute. Plain
 * state avoids the wrapper entirely. */
export function RingProgress({
  percentage,
  size = 80,
  strokeWidth = 8,
  color,
  trackColor,
  children,
}: {
  percentage: number;
  size?: number;
  strokeWidth?: number;
  color: string;
  trackColor: string;
  children?: ReactNode;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const target = Math.max(0, Math.min(100, percentage));
  const [reveal, setReveal] = useState(0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    setReveal(0);
    const startedAt = Date.now();
    const tick = () => {
      const t = Math.min(1, (Date.now() - startedAt) / DURATION_MS);
      setReveal(1 - Math.pow(1 - t, 4));
      if (t < 1) frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [target]);

  const strokeDashoffset = circumference - (target / 100) * reveal * circumference;

  return (
    <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Svg width={size} height={size} style={{ position: "absolute", transform: [{ rotate: "-90deg" }] }}>
        <Circle cx={size / 2} cy={size / 2} r={radius} stroke={trackColor} strokeWidth={strokeWidth} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
        />
      </Svg>
      {children}
    </View>
  );
}
