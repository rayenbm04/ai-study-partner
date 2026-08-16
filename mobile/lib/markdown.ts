/**
 * Minimal markdown+LaTeX parser for LLM-generated content (chat answers,
 * summaries, quiz text) — the backend's generation prompts (see
 * chat_service.py, summary_service.py, quiz_engine/generator.py) are told to
 * use **bold**, "#"/"##"/"###" headers, "- "/"1. " lists, inline $...$ math,
 * and block $$...$$/\[...\] math, so this only needs to understand that
 * subset rather than full CommonMark. Block math becomes its own MathBlock
 * (see components/markdown/MathBlock.tsx); everything else stays as flowing
 * Text runs, since a WebView (what real KaTeX rendering needs) can't be an
 * inline child of RN's <Text>.
 *
 * GFM tables are deliberately NOT rendered as real tables (would need a
 * dedicated table component) — a row's cells are joined into one flowing
 * line instead, which is legible but not aligned into columns.
 *
 * Bare (undelimited) LaTeX commands the model emits despite the prompt
 * asking for $...$ are also auto-detected and typeset — see
 * BARE_LATEX_CLUSTER below.
 */
export type InlineRun =
  | { type: "text"; content: string }
  | { type: "bold"; content: string }
  | { type: "math"; latex: string };

export type ChatBlock =
  | { type: "paragraph"; runs: InlineRun[] }
  | { type: "bullet"; runs: InlineRun[] }
  | { type: "heading"; level: 1 | 2 | 3; runs: InlineRun[] }
  | { type: "math"; latex: string };

const BLOCK_MATH_RE = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g;
const BULLET_RE = /^\s*[-*•]\s+(.*)$/;
const NUMBERED_RE = /^\s*\d+[.)]\s+(.*)$/;
const HEADING_RE = /^\s*(#{1,3})\s+(.*)$/;
const HR_RE = /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/;
const TABLE_SEPARATOR_RE = /^\s*\|?[\s:|-]+\|?\s*$/;
const TABLE_ROW_RE = /^\s*\|(.*)\|\s*$/;

// The generation prompts ask the model to wrap every equation in $...$/$$...$$,
// but it doesn't always comply — it sometimes emits bare LaTeX commands
// (\mathrm{HCl}, \rightarrow, H^+) directly in prose. Rendered as literal
// text, a bare "\" also reads wrong in the app's serif font (easy to mistake
// for "|"). BARE_LATEX_CLUSTER catches a run of such tokens — a LaTeX
// command (optionally with a {...} group) or a sub/superscripted symbol
// (H^+, NH_4^+), optionally chained with more of the same or a bare +/= —
// and inline math wraps it in real KaTeX instead of showing it raw. Anything
// already inside $...$/\(...\) is consumed by those alternatives first, so
// this only ever fires on genuinely undelimited stretches.
const LATEX_COMMAND_TOKEN = String.raw`\\[a-zA-Z]+(?:\{[^{}]*\})*`;
const SUP_SUB_TOKEN = String.raw`[A-Za-z]+[0-9]*(?:[\^_]\{?[A-Za-z0-9+\-]+\}?)+`;
const BARE_LATEX_CLUSTER = `(?:${LATEX_COMMAND_TOKEN}|${SUP_SUB_TOKEN})(?: ?(?:${LATEX_COMMAND_TOKEN}|${SUP_SUB_TOKEN}|[+=]))*`;
const BARE_LATEX_START_RE = /^(?:\\[a-zA-Z]|[A-Za-z]+[0-9]*[\^_])/;

const INLINE_SPLIT_RE = new RegExp(
  `(\\*\\*[^*\\n]+?\\*\\*|\\$[^$\\n]+?\\$|\\\\\\([^\\n]+?\\\\\\)|${BARE_LATEX_CLUSTER})`,
  "g"
);

function parseInline(text: string): InlineRun[] {
  return text
    .split(INLINE_SPLIT_RE)
    .filter((part) => part.length > 0)
    .map((part): InlineRun => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return { type: "bold", content: part.slice(2, -2) };
      }
      if (part.startsWith("\\(") && part.endsWith("\\)")) {
        return { type: "math", latex: part.slice(2, -2) };
      }
      if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
        return { type: "math", latex: part.slice(1, -1) };
      }
      if (BARE_LATEX_START_RE.test(part)) {
        return { type: "math", latex: part };
      }
      return { type: "text", content: part };
    });
}

function parseTextChunk(chunk: string): ChatBlock[] {
  const blocks: ChatBlock[] = [];
  for (const rawLine of chunk.split("\n")) {
    const line = rawLine.trim();
    if (!line || HR_RE.test(line) || TABLE_SEPARATOR_RE.test(line)) continue;

    const headingMatch = HEADING_RE.exec(line);
    if (headingMatch) {
      const level = headingMatch[1].length as 1 | 2 | 3;
      blocks.push({ type: "heading", level, runs: parseInline(headingMatch[2]) });
      continue;
    }
    const bulletMatch = BULLET_RE.exec(line);
    if (bulletMatch) {
      blocks.push({ type: "bullet", runs: parseInline(bulletMatch[1]) });
      continue;
    }
    const numberedMatch = NUMBERED_RE.exec(line);
    if (numberedMatch) {
      blocks.push({ type: "bullet", runs: parseInline(numberedMatch[1]) });
      continue;
    }
    const tableMatch = TABLE_ROW_RE.exec(line);
    if (tableMatch) {
      const cells = tableMatch[1].split("|").map((cell) => cell.trim()).filter(Boolean);
      blocks.push({ type: "paragraph", runs: parseInline(cells.join("   ·   ")) });
      continue;
    }
    blocks.push({ type: "paragraph", runs: parseInline(line) });
  }
  return blocks;
}

export function parseChatContent(content: string): ChatBlock[] {
  const blocks: ChatBlock[] = [];
  let lastIndex = 0;
  BLOCK_MATH_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = BLOCK_MATH_RE.exec(content)) !== null) {
    blocks.push(...parseTextChunk(content.slice(lastIndex, match.index)));
    const latex = (match[1] ?? match[2] ?? "").trim();
    if (latex) blocks.push({ type: "math", latex });
    lastIndex = BLOCK_MATH_RE.lastIndex;
  }
  blocks.push(...parseTextChunk(content.slice(lastIndex)));
  return blocks;
}
