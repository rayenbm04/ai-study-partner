"""Mastery scoring and concept-tree rollup.

A leaf concept's mastery score is computed from two evidence signals — the
student's most recent flashcard review quality (SM-2 grade, 0-5) and their
quiz/exam answer correctness (StudentAnswer.is_correct) for questions tagged
to that concept — averaged together when both are present. A concept with no
evidence at all returns None (not 0), since "never practiced" and "practiced
and failed" are different situations a UI needs to tell apart.

Chapter/subject-level mastery is never stored — it's computed here by
rolling scores up the concept tree (parent_concept_id), averaging whichever
children actually have a score and ignoring ones that don't, so one
never-touched subtree doesn't silently drag down a chapter's rollup. A
non-leaf concept's own direct evidence (if any was tagged straight to it) is
deliberately not mixed into its rollup — docs/ARCHITECTURE.md section 3 is
explicit that "chapter/subject mastery is computed on read by aggregating
child concepts," not a blend of a concept's own score and its children's.
"""
from dataclasses import dataclass, field

from app.domain.entities.concept import Concept

TREND_UP_THRESHOLD = 1.0    # minimum point gain to call it "up" rather than noise
TREND_DOWN_THRESHOLD = 1.0  # minimum point loss to call it "down"


@dataclass(frozen=True, slots=True)
class ConceptMastery:
    """A node in the rolled-up concept tree returned to the API layer. Leaf
    concepts (no children) carry a real trend from their stored Progress row;
    rolled-up parent nodes leave trend as None since no single stored value
    backs an aggregate — only the score itself is meaningfully aggregated."""

    concept_id: str
    name: str
    mastery_score: float | None  # None if this concept (and all its descendants) have no evidence yet
    trend: str | None
    children: list["ConceptMastery"] = field(default_factory=list)


def score_from_evidence(*, flashcard_grades: list[int], answer_results: list[bool]) -> float | None:
    """Combines whatever evidence exists for one leaf concept into a 0-100
    score. flashcard_grades are the latest SM-2 quality (0-5) of each
    flashcard tagged to this concept; answer_results are is_correct booleans
    from every quiz/exam answer tagged to this concept."""
    signals: list[float] = []
    if flashcard_grades:
        signals.append(sum(g / 5 * 100 for g in flashcard_grades) / len(flashcard_grades))
    if answer_results:
        signals.append(100 * sum(1 for correct in answer_results if correct) / len(answer_results))
    if not signals:
        return None
    return round(sum(signals) / len(signals), 1)


def compute_trend(
    *,
    previous_score: float | None,
    new_score: float,
    up_threshold: float = TREND_UP_THRESHOLD,
    down_threshold: float = TREND_DOWN_THRESHOLD,
) -> str:
    """"flat" is also the answer the first time a concept is scored — there's
    no direction without a prior value to compare against. Thresholds are
    parameters (not hardcoded) so ProgressService can wire them to settings —
    unlike sm2.py's constants, these are tuned heuristics, not a fixed spec."""
    if previous_score is None:
        return "flat"
    delta = new_score - previous_score
    if delta >= up_threshold:
        return "up"
    if delta <= -down_threshold:
        return "down"
    return "flat"


def build_rollup(concepts: list[Concept], leaf_results: dict[str, tuple[float, str]]) -> list[ConceptMastery]:
    """Builds the concept tree from flat parent_concept_id links and rolls
    scores up from leaves to roots. leaf_results maps concept_id -> (score,
    trend) for concepts that have a freshly computed Progress row. Returns
    the top-level (parent_concept_id is None) nodes, each with its full
    subtree attached."""
    children_by_parent: dict[str | None, list[Concept]] = {}
    for concept in concepts:
        children_by_parent.setdefault(concept.parent_concept_id, []).append(concept)

    def build(concept: Concept) -> ConceptMastery:
        child_concepts = children_by_parent.get(concept.id, [])
        children = [build(c) for c in child_concepts]

        if not children:
            # leaf concept — score comes directly from this concept's own evidence
            score, trend = leaf_results.get(concept.id, (None, None))
            return ConceptMastery(
                concept_id=concept.id, name=concept.name, mastery_score=score, trend=trend, children=[]
            )

        # non-leaf — roll up whichever children actually have a score
        scored_children = [c for c in children if c.mastery_score is not None]
        rolled_up = (
            round(sum(c.mastery_score for c in scored_children) / len(scored_children), 1)
            if scored_children
            else None
        )
        return ConceptMastery(
            concept_id=concept.id, name=concept.name, mastery_score=rolled_up, trend=None, children=children
        )

    roots = children_by_parent.get(None, [])
    return [build(root) for root in roots]


def flatten_leaves(nodes: list[ConceptMastery]) -> list[ConceptMastery]:
    """Collects every leaf node (no children) out of a rolled-up tree —
    used by engines that need per-concept granularity (planning, analytics)
    rather than the chapter/subject-level rollup itself."""
    leaves: list[ConceptMastery] = []
    for node in nodes:
        if node.children:
            leaves.extend(flatten_leaves(node.children))
        else:
            leaves.append(node)
    return leaves
