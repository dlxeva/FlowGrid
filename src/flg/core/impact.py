"""Read-only impact analysis over explicit decision relations."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .relations import RELATION_TYPES, incoming_relations


@dataclass(frozen=True)
class ImpactPath:
    """One shortest relation path from a changed decision to an affected one."""

    decision_id: str
    via: str
    parent: str
    depth: int


def _neighbors(
    graph: Mapping[str, Mapping[str, Sequence[str]]],
    decision_id: str,
) -> list[tuple[str, str]]:
    """Return decisions whose validity may depend on decision_id.

    Incoming relations propagate toward the relation owner. Supersedes and
    conflicts_with also propagate from the relation owner to their targets.
    Supports and depends_on do not propagate toward their prerequisites.
    """
    neighbors = [
        (source, f"incoming:{relation}")
        for relation, source in incoming_relations(graph, decision_id)
        if relation in RELATION_TYPES
    ]
    outgoing = graph.get(decision_id, {})
    for relation in ("supersedes", "conflicts_with"):
        neighbors.extend(
            (target, f"outgoing:{relation}")
            for target in outgoing.get(relation, ())
        )
    return sorted(set(neighbors))


def analyze_impact(
    graph: Mapping[str, Mapping[str, Sequence[str]]],
    decision_id: str,
) -> list[ImpactPath]:
    """Return the transitive affected subgraph without changing ledger state."""
    if decision_id not in graph:
        return []

    queue: deque[tuple[str, int]] = deque([(decision_id, 0)])
    visited = {decision_id}
    paths: list[ImpactPath] = []

    while queue:
        current, depth = queue.popleft()
        for neighbor, via in _neighbors(graph, current):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            paths.append(
                ImpactPath(
                    decision_id=neighbor,
                    via=via,
                    parent=current,
                    depth=depth + 1,
                )
            )
            queue.append((neighbor, depth + 1))
    return paths
