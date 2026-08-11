import type { THEME } from "./theme";
import type { ConceptMastery } from "./api";

type Scheme = (typeof THEME)["light"];

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

const SAGE = "hsl(152 55% 40%)";

export function masteryColor(scheme: Scheme, score: number | null): string {
  if (score === null) return scheme.mutedForeground;
  if (score >= 70) return SAGE;
  if (score >= 40) return scheme.primary;
  return scheme.destructive;
}
