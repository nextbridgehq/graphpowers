"""Architecture drift: diff two graph snapshots (before vs after a branch).

The idea: snapshot graph.json before implementation starts, rebuild after,
and diff. This catches things code review misses — a helper that quietly
became a god node, a new dependency between communities that were
previously independent, orphaned nodes left behind by a refactor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graphio import Graph


@dataclass
class DriftReport:
    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    added_edges: list[tuple] = field(default_factory=list)
    removed_edges: list[tuple] = field(default_factory=list)
    new_god_nodes: list[str] = field(default_factory=list)
    new_cross_community_edges: list[tuple] = field(default_factory=list)
    orphaned_nodes: list[str] = field(default_factory=list)
    community_warning: str = ""

    @property
    def clean(self) -> bool:
        return not (self.new_god_nodes or self.new_cross_community_edges
                    or self.orphaned_nodes)

    def to_dict(self, before: "Graph", after: "Graph") -> dict:
        return {
            "clean": self.clean,
            "verdict": "CLEAN" if self.clean else "REVIEW NEEDED",
            "added_nodes": [{"id": n, "label": after.label(n)} for n in self.added_nodes],
            "removed_nodes": [{"id": n, "label": before.label(n)} for n in self.removed_nodes],
            "added_edge_count": len(self.added_edges),
            "removed_edge_count": len(self.removed_edges),
            "new_god_nodes": [
                {"id": n, "label": after.label(n),
                 "impact_degree_before": before.impact_degree.get(n, 0),
                 "impact_degree_after": after.impact_degree.get(n, 0)}
                for n in self.new_god_nodes
            ],
            "new_cross_community_edges": [
                {"source": a, "target": b, "relation": r,
                 "source_community": after.community(a),
                 "target_community": after.community(b)}
                for a, b, r in self.new_cross_community_edges
            ],
            "orphaned_nodes": [{"id": n, "label": after.label(n)} for n in self.orphaned_nodes],
            "community_warning": self.community_warning or None,
        }


def _edge_key(e) -> tuple:
    a, b = sorted((e.source, e.target))
    return (a, b, e.relation)


def diff(before: Graph, after: Graph, god_top_n: int = 10) -> DriftReport:
    b_nodes, a_nodes = set(before.nodes), set(after.nodes)
    b_edges = {_edge_key(e) for e in before.edges}
    a_edges = {_edge_key(e) for e in after.edges}

    added_nodes = sorted(a_nodes - b_nodes)
    removed_nodes = sorted(b_nodes - a_nodes)
    added_edges = sorted(a_edges - b_edges)
    removed_edges = sorted(b_edges - a_edges)

    # nodes that entered the god-node top list only after the change
    before_gods = {nid for nid, _ in before.god_nodes(god_top_n)}
    after_gods = {nid for nid, _ in after.god_nodes(god_top_n)}
    new_gods = sorted(after_gods - before_gods)

    # new edges linking two different communities (coupling creep)
    cross: list[tuple] = []
    for a, b, rel in added_edges:
        ca, cb = after.community(a), after.community(b)
        if ca is not None and cb is not None and ca != cb:
            cross.append((a, b, rel))

    # nodes that survived but lost all their edges
    orphaned = sorted(
        nid for nid in (a_nodes & b_nodes)
        if after.degree.get(nid, 0) == 0 and before.degree.get(nid, 0) > 0
    )

    # Detect possible community relabeling
    before_comms = {attrs.get("community") for attrs in before.nodes.values()
                    if attrs.get("community") is not None}
    after_comms = {attrs.get("community") for attrs in after.nodes.values()
                   if attrs.get("community") is not None}

    # Heuristic: if community ID sets differ significantly but node count
    # is similar, communities were likely relabeled, not restructured
    community_warning = ""
    if before_comms and after_comms:
        # Check if surviving nodes changed community en masse
        surviving = set(before.nodes) & set(after.nodes)
        if surviving:
            changed_community = sum(
                1 for nid in surviving
                if before.nodes[nid].get("community") != after.nodes.get(nid, {}).get("community")
            )
            change_rate = changed_community / len(surviving)
            if change_rate > 0.3 and len(cross) > 0:
                community_warning = (
                    f"⚠️  {change_rate:.0%} of surviving nodes changed community ID. "
                    f"Cross-community findings below may reflect community relabeling "
                    f"rather than real coupling changes. Rebuild both graphs from the "
                    f"same graphify version to confirm."
                )

    return DriftReport(added_nodes=added_nodes, removed_nodes=removed_nodes,
                       added_edges=added_edges, removed_edges=removed_edges,
                       new_god_nodes=new_gods,
                       new_cross_community_edges=cross,
                       orphaned_nodes=orphaned,
                       community_warning=community_warning)


def render_markdown(before: Graph, after: Graph, report: DriftReport,
                    max_rows: int = 25) -> str:
    lines = ["# Architecture drift report", ""]
    verdict = "CLEAN ✅" if report.clean else "REVIEW NEEDED ⚠️"
    lines.append(f"**Verdict: {verdict}** — "
                 f"+{len(report.added_nodes)}/-{len(report.removed_nodes)} nodes, "
                 f"+{len(report.added_edges)}/-{len(report.removed_edges)} edges.")

    if report.new_god_nodes:
        lines.append("\n## New god nodes (centrality spiked)")
        for nid in report.new_god_nodes:
            lines.append(f"- **{after.label(nid)}** — impact degree "
                         f"{before.impact_degree.get(nid, 0)} → {after.impact_degree.get(nid, 0)} "
                         f"({after.location(nid)})")
        lines.append("\nA node this central deserves its own tests and docs. "
                     "Was this concentration intentional?")

    if report.new_cross_community_edges:
        lines.append("\n## New cross-community coupling")
        if report.community_warning:
            lines.append(f"\n{report.community_warning}\n")
        for a, b, rel in report.new_cross_community_edges[:max_rows]:
            lines.append(f"- `{after.label(a)}` —{rel}→ `{after.label(b)}` "
                         f"(communities {after.community(a)} ↔ {after.community(b)})")
        lines.append("\nThese modules were previously independent. "
                     "Confirm the coupling is deliberate, not accidental.")

    if report.orphaned_nodes:
        lines.append("\n## Orphaned nodes (all edges removed)")
        for nid in report.orphaned_nodes[:max_rows]:
            lines.append(f"- {after.label(nid)} — {after.location(nid)}")
        lines.append("\nDead code candidates — delete or re-wire.")

    if report.added_nodes:
        lines.append("\n## Added")
        for nid in report.added_nodes[:max_rows]:
            lines.append(f"- {after.label(nid)} ({after.location(nid)})")
        if len(report.added_nodes) > max_rows:
            lines.append(f"- …and {len(report.added_nodes) - max_rows} more")
    if report.removed_nodes:
        lines.append("\n## Removed")
        for nid in report.removed_nodes[:max_rows]:
            lines.append(f"- {before.label(nid)}")
        if len(report.removed_nodes) > max_rows:
            lines.append(f"- …and {len(report.removed_nodes) - max_rows} more")
    return "\n".join(lines) + "\n"
