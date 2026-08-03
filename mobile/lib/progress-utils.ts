import type { ColorScheme } from "../constants/theme";
import type { ConceptMastery } from "./api";

/** Flattens a concept-mastery tree into concept_id -> name, for resolving a
 * WeakConcept (which only carries a concept_id) to a display name. Shared
 * between the per-subject concept map and the cross-subject Progress tab so
 * both resolve names the same way. */
export function flattenConceptNames(nodes: ConceptMastery[], out: Map<string, string> = new Map()): Map<string, string> {
  for (const node of nodes) {
    out.set(node.concept_id, node.name);
    if (node.children.length > 0) flattenConceptNames(node.children, out);
  }
  return out;
}

export function masteryColor(colors: ColorScheme, score: number | null): string {
  if (score === null) return colors.textMuted;
  if (score >= 70) return colors.sage;
  if (score >= 40) return colors.accent;
  return colors.error;
}
