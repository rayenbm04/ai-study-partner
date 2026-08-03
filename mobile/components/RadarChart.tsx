/**
 * A small multi-axis radar/spider chart for "mastery per chapter within a
 * subject" — hand-built on react-native-svg rather than a charting library
 * (recharts et al. are web/React-DOM-only, not React Native). Needs at
 * least 3 axes to read as a polygon rather than a line; callers should
 * fall back to a plain bar list below that threshold.
 *
 * The reveal animation drives the polygon's `points` string directly from a
 * requestAnimationFrame loop (state, not Animated.Value.interpolate) —
 * Animated's string interpolation only reliably handles single-token
 * patterns like colors or "12px"; a multi-coordinate SVG points string is
 * outside what it's documented to support.
 */
import { useEffect, useRef, useState } from "react";
import { View } from "react-native";
import Svg, { Circle, Line, Polygon, Text as SvgText } from "react-native-svg";

export type RadarDatum = { label: string; value: number };

const RING_FRACTIONS = [0.25, 0.5, 0.75, 1];
const MAX_LABEL_CHARS = 12;
const DURATION_MS = 600;

function truncate(label: string): string {
  return label.length > MAX_LABEL_CHARS ? `${label.slice(0, MAX_LABEL_CHARS - 1)}…` : label;
}

function pointAt(center: number, radius: number, fraction: number, angle: number) {
  return {
    x: center + radius * fraction * Math.cos(angle),
    y: center + radius * fraction * Math.sin(angle),
  };
}

export function RadarChart({
  data,
  size = 220,
  color,
  gridColor,
  labelColor,
}: {
  data: RadarDatum[];
  size?: number;
  color: string;
  gridColor: string;
  labelColor: string;
}) {
  const [reveal, setReveal] = useState(0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    setReveal(0);
    const startedAt = Date.now();
    const tick = () => {
      const t = Math.min(1, (Date.now() - startedAt) / DURATION_MS);
      // easeOutQuart
      setReveal(1 - Math.pow(1 - t, 4));
      if (t < 1) frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(data)]);

  const center = size / 2;
  const labelPad = 22;
  const radius = center - labelPad;
  const n = data.length;

  if (n < 3) return null;

  const angleFor = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;

  const dataPoints = data
    .map((d, i) => {
      const p = pointAt(center, radius, (Math.max(0, d.value) / 100) * reveal, angleFor(i));
      return `${p.x},${p.y}`;
    })
    .join(" ");

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size}>
        {RING_FRACTIONS.map((fraction) => (
          <Polygon
            key={fraction}
            points={data.map((_, i) => { const p = pointAt(center, radius, fraction, angleFor(i)); return `${p.x},${p.y}`; }).join(" ")}
            fill="none"
            stroke={gridColor}
            strokeWidth={1}
          />
        ))}
        {data.map((_, i) => {
          const p = pointAt(center, radius, 1, angleFor(i));
          return <Line key={i} x1={center} y1={center} x2={p.x} y2={p.y} stroke={gridColor} strokeWidth={1} />;
        })}
        <Polygon points={dataPoints} fill={color} fillOpacity={0.35} stroke={color} strokeWidth={2} />
        {data.map((d, i) => {
          const p = pointAt(center, radius, (Math.max(0, d.value) / 100) * reveal, angleFor(i));
          return <Circle key={i} cx={p.x} cy={p.y} r={3} fill={color} />;
        })}
        {data.map((d, i) => {
          const angle = angleFor(i);
          const p = pointAt(center, radius, 1.18, angle);
          const cos = Math.cos(angle);
          const anchor = cos > 0.3 ? "start" : cos < -0.3 ? "end" : "middle";
          return (
            <SvgText key={i} x={p.x} y={p.y} fontSize={9} fill={labelColor} textAnchor={anchor}>
              {truncate(d.label)}
            </SvgText>
          );
        })}
      </Svg>
    </View>
  );
}
