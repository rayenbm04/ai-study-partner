import { Fragment } from "react";
import { View } from "react-native";

import { Text } from "../ui/text";
import { parseChatContent, type InlineRun } from "../../lib/markdown";
import { cn } from "../../lib/utils";
import { MathBlock } from "./MathBlock";

type MarkdownContentProps = {
  content: string;
  /** True for a chat bubble on the "mine" (user) side — swaps text color to
   * text-primary-foreground and the math-block background to a subtler
   * overlay that reads against a filled bubble instead of a card. */
  mine?: boolean;
  textColor: string;
  /** Overrides the default paragraph/inline text style (e.g. a quiz
   * question wants "text-3xl font-bold" instead of chat's body size). Only
   * affects plain paragraph runs — headings and bullets keep their own
   * fixed styles regardless. */
  baseClassName?: string;
};

const HEADING_SIZE: Record<1 | 2 | 3, string> = {
  1: "text-xl font-bold",
  2: "text-lg font-bold",
  3: "text-base font-semibold",
};

function InlineRuns({ runs, mine, className }: { runs: InlineRun[]; mine?: boolean; className?: string }) {
  const base = className ?? "text-[15.5px] leading-6";
  return (
    <Text className={cn(base, mine && "text-primary-foreground")}>
      {runs.map((run, i) => {
        if (run.type === "bold") {
          return (
            <Text key={i} className={cn(base, "font-semibold", mine && "text-primary-foreground")}>
              {run.content}
            </Text>
          );
        }
        if (run.type === "math") {
          // Inline math can't get real KaTeX typesetting — a WebView can't be
          // an inline child of RN's <Text> — so it stays flowing text, just
          // set apart in italics to read as "this is a symbol/formula".
          return (
            <Text key={i} className={cn(base, "italic", mine && "text-primary-foreground")}>
              {run.latex}
            </Text>
          );
        }
        return <Fragment key={i}>{run.content}</Fragment>;
      })}
    </Text>
  );
}

export function MarkdownContent({ content, mine, textColor, baseClassName }: MarkdownContentProps) {
  const blocks = parseChatContent(content);

  return (
    <View className="gap-2.5">
      {blocks.map((block, i) => {
        if (block.type === "math") {
          return (
            <View key={i} className={cn("rounded-xl px-3 py-1", mine ? "bg-black/10" : "bg-foreground/5")}>
              <MathBlock latex={block.latex} display color={textColor} />
            </View>
          );
        }
        if (block.type === "heading") {
          return <InlineRuns key={i} runs={block.runs} mine={mine} className={HEADING_SIZE[block.level]} />;
        }
        if (block.type === "bullet") {
          return (
            <View key={i} className="flex-row gap-2 pl-1">
              <Text className={cn("text-[15.5px] leading-6", mine && "text-primary-foreground")}>{"•"}</Text>
              <View className="flex-1">
                <InlineRuns runs={block.runs} mine={mine} className={baseClassName} />
              </View>
            </View>
          );
        }
        return <InlineRuns key={i} runs={block.runs} mine={mine} className={baseClassName} />;
      })}
    </View>
  );
}
