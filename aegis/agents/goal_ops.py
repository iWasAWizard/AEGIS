# aegis/agents/goal_ops.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Iterable


@dataclass(frozen=True)
class GoalSnapshot:
    """Immutable snapshot of goal state."""

    goal: str
    sub_goals: List[str]
    current_index: int


def clamp_index(idx: int, length: int) -> int:
    """Clamp idx into [0, max(0, length-1)] for non-empty sequences; for empty, returns 0."""
    if length <= 0:
        return 0
    if idx < 0:
        return 0
    if idx >= length:
        return length - 1
    return idx


def apply_insert(
    sub_goals: List[str], index: int | None, items: Iterable[str]
) -> Tuple[List[str], int]:
    """Insert items before index (or append if index is None). Returns (new_sub_goals, new_index_same_position)."""
    items = [s for s in (items or []) if isinstance(s, str) and s.strip()]
    if not items:
        return list(sub_goals), clamp_index(index or 0, len(sub_goals))
    out = list(sub_goals)
    if index is None:
        out.extend(items)
        return out, clamp_index(len(out) - 1, len(out))
    i = max(0, min(index, len(out)))
    out[i:i] = items
    return out, clamp_index(i, len(out))


def apply_remove(
    sub_goals: List[str], indices: Iterable[int], current_index: int
) -> Tuple[List[str], int]:
    """Remove by indices. Returns (new_sub_goals, new_current_index)."""
    L = len(sub_goals)
    if L == 0:
        return [], 0
    # normalize and dedupe indices
    uniq = sorted({i for i in indices if 0 <= i < L}, reverse=True)
    if not uniq:
        return list(sub_goals), clamp_index(current_index, L)
    out = list(sub_goals)
    # track how many removals occur before/at current_index
    removed_before_or_at = 0
    current_was_removed = False
    for i in uniq:
        if i == current_index:
            current_was_removed = True
        if i < current_index or i == current_index:
            removed_before_or_at += 1
        del out[i]
    if not out:
        return [], 0
    if current_was_removed:
        # keep focus at the same list position after deletion if possible
        new_idx = min(current_index, len(out) - 1)
    else:
        # shift left by how many were removed before current
        new_idx = max(0, current_index - removed_before_or_at)
    return out, clamp_index(new_idx, len(out))


def apply_reorder(
    sub_goals: List[str], order: List[int], current_index: int
) -> Tuple[List[str], int]:
    """Reorder to match the given permutation 'order'. Returns (new_sub_goals, new_current_index)."""
    L = len(sub_goals)
    if L == 0:
        return [], 0
    if len(order) != L or sorted(order) != list(range(L)):
        raise ValueError("order must be a full permutation of range(len(sub_goals))")
    out = [sub_goals[i] for i in order]
    # compute where the old current_index moved to
    new_idx = order.index(current_index)
    return out, clamp_index(new_idx, len(out))


def apply_set_current(sub_goals: List[str], index: int) -> int:
    """Return a clamped current_index."""
    return clamp_index(index, len(sub_goals))


def summarize_diff(before: GoalSnapshot, after: GoalSnapshot) -> str:
    """Produce a compact, human-readable summary of changes."""
    lines: List[str] = []
    if before.goal != after.goal:
        lines.append(f"goal_changed: '{before.goal}' → '{after.goal}'")
    if before.sub_goals != after.sub_goals:
        # compute simple add/remove/move summary
        b = before.sub_goals
        a = after.sub_goals
        added = [x for x in a if x not in b]
        removed = [x for x in b if x not in a]
        if added:
            lines.append("added: " + ", ".join(f"'{x}'" for x in added[:5]))
        if removed:
            lines.append("removed: " + ", ".join(f"'{x}'" for x in removed[:5]))
        # moves (best-effort)
        moves: List[str] = []
        pos_b = {v: i for i, v in enumerate(b)}
        for i, v in enumerate(a):
            if v in pos_b and pos_b[v] != i:
                moves.append(f"'{v}': {pos_b[v]}→{i}")
        if moves:
            lines.append("reordered: " + ", ".join(moves[:5]))
    if before.current_index != after.current_index:
        lines.append(f"current_index: {before.current_index} → {after.current_index}")
    return "; ".join(lines) if lines else "no_change"


def format_preview(before: GoalSnapshot, after: GoalSnapshot) -> str:
    """Return a short multi-line preview showing goal/sub-goal changes."""
    lines = ["Goal Edit Preview:"]
    if before.goal != after.goal:
        lines.append(f"- goal: {before.goal!r} -> {after.goal!r}")
    if before.sub_goals != after.sub_goals:
        lines.append(
            "- sub_goals(before): "
            + "; ".join(before.sub_goals[:6])
            + (" ..." if len(before.sub_goals) > 6 else "")
        )
        lines.append(
            "- sub_goals(after):  "
            + "; ".join(after.sub_goals[:6])
            + (" ..." if len(after.sub_goals) > 6 else "")
        )
    if before.current_index != after.current_index:
        lines.append(
            f"- current_index: {before.current_index} -> {after.current_index}"
        )
    if len(lines) == 1:
        lines.append("- no changes")
    return "\n".join(lines)
