"""Reverse-dependency lookup: who uses / renders / calls a named node?

Powers the component-blast-radius and catching-design-system-bypasses skills:
before touching a shared component, enumerate every consumer; when
auditing a design system, list what renders the raw element vs the
sanctioned component.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .graphio import Graph


@dataclass
class UsageReport:
    query: str
    matched_node: str | None = None
    candidates: list[str] = field(default_factory=list)  # other label matches
    consumers: dict[str, list[str]] = field(default_factory=dict)  # relation -> node ids


def find_node(graph: Graph, term: str) -> tuple[str | None, list[str]]:
    """Best node match for a label term or source-file path. Exact label
    (casefolded) wins, then substring label matches, then a source-file
    path match — ordered by degree (most-connected first) within each
    tier."""
    t = term.casefold().strip()
    exact: list[str] = []
    partial: list[str] = []
    for nid, attrs in graph.nodes.items():
        label = str(attrs.get("label", nid)).casefold()
        bare = label[:-2] if label.endswith("()") else label
        if bare == t or label == t or nid.casefold() == t:
            exact.append(nid)
        elif t in label:
            partial.append(nid)
    pool = exact or partial
    if not pool:
        pool = graph.nodes_for_files([term])
    pool.sort(key=lambda n: (-graph.degree.get(n, 0), n))
    if not pool:
        return None, []
    return pool[0], pool[1:6]


def who_uses(graph: Graph, term: str) -> UsageReport:
    nid, candidates = find_node(graph, term)
    rep = UsageReport(query=term, matched_node=nid, candidates=candidates)
    if nid is None:
        return rep
    consumers: dict[str, list[str]] = defaultdict(list)
    for other, edge in graph.neighbors(nid):
        consumers[edge.relation or "related"].append(other)
    for rel in consumers:
        consumers[rel].sort(key=lambda n: graph.label(n))
    rep.consumers = dict(consumers)
    return rep


def render_markdown(graph: Graph, rep: UsageReport,
                    max_per_relation: int = 30) -> str:
    if rep.matched_node is None:
        return (f"No node matching `{rep.query}` in the graph. "
                "Check spelling or rebuild the graph.\n")
    lines = [f"# Who uses `{graph.label(rep.matched_node)}`", ""]
    lines.append(f"Node: {graph.location(rep.matched_node)} — "
                 f"degree {graph.degree.get(rep.matched_node, 0)}, "
                 f"community {graph.community(rep.matched_node)}")
    if rep.candidates:
        alts = ", ".join(f"`{graph.label(c)}`" for c in rep.candidates)
        lines.append(f"\nOther matches (rerun with an exact label if wrong): {alts}")
    total = sum(len(v) for v in rep.consumers.values())
    lines.append(f"\n**{total} connected node(s):**")
    for rel in sorted(rep.consumers):
        nodes = rep.consumers[rel]
        lines.append(f"\n## {rel} ({len(nodes)})")
        for n in nodes[:max_per_relation]:
            lines.append(f"- {graph.label(n)} — {graph.location(n)}")
        if len(nodes) > max_per_relation:
            lines.append(f"- …and {len(nodes) - max_per_relation} more")
    return "\n".join(lines) + "\n"
