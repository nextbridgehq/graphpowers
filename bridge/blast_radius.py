"""Blast radius: given changed files, report what the change can reach.

Used by the graph-first-planning skill (scope each plan task), the
graph-impact-review skill (what should reviewers look at), and the
graph-first-debugging skill (what could this regression touch).

TRAVERSAL SEMANTICS:
  Blast radius traverses impact relations BIDIRECTIONALLY regardless of
  edge direction in the graph. This is intentional — it answers "what
  could possibly be affected by OR affect this code?"

  For example, if A --calls--> B:
    - Changing A: B is in range (A's call target may see different inputs)
    - Changing B: A is in range (A depends on B's behavior)

  This conservative approach avoids false negatives at the cost of
  occasional false positives. For a safety/risk tool, over-flagging
  is preferable to under-flagging.

  Relations traversed: calls, indirect_call, references, imports,
  imports_from, re_exports, inherits, extends, implements, uses,
  mixes_in, embeds.

  Relations NOT traversed (structural only): contains, defines,
  declares, documents — these don't represent runtime/compile-time
  dependency.
"""

from __future__ import annotations

import subprocess
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .graphio import Graph, IMPACT_RELATIONS


@dataclass
class Hit:
    node_id: str
    depth: int
    via: str  # relation on the edge that first reached this node


@dataclass
class BlastReport:
    seeds: list[str]
    hits: list[Hit]
    by_community: dict = field(default_factory=dict)
    god_nodes_touched: list[str] = field(default_factory=list)
    unmatched_files: list[str] = field(default_factory=list)

    def risk(self) -> str:
        n = len(self.hits)
        if self.god_nodes_touched:
            return "HIGH"
        if n > 40 or len(self.by_community) > 3:
            return "MEDIUM"
        return "LOW"

    def to_dict(self, graph: "Graph") -> dict:
        """Structured output for JSON consumers."""
        return {
            "risk": self.risk(),
            "seed_count": len(self.seeds),
            "hit_count": len(self.hits),
            "community_count": len(self.by_community),
            "god_nodes_touched": [graph.label(n) for n in self.god_nodes_touched],
            "unmatched_files": self.unmatched_files,
            "hits": [
                {
                    "node_id": h.node_id,
                    "label": graph.label(h.node_id),
                    "depth": h.depth,
                    "via": h.via,
                    "location": graph.location(h.node_id),
                }
                for h in self.hits
            ],
        }


def git_changed_files(ref: str = "HEAD") -> list[str]:
    """Changed files vs ref, plus untracked. Empty list if not a git repo."""
    files: list[str] = []
    for cmd in (["git", "diff", "--name-only", ref],
                ["git", "ls-files", "--others", "--exclude-standard"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=30, check=False)
            if out.returncode == 0:
                files.extend(l.strip() for l in out.stdout.splitlines()
                             if l.strip())
        except (OSError, subprocess.TimeoutExpired):
            return []
    seen, uniq = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def blast_radius(graph: Graph,
                 files: Iterable[str],
                 max_depth: int = 2,
                 relations: Optional[Iterable[str]] = None) -> BlastReport:
    files = list(files)
    seeds = graph.nodes_for_files(files)
    matched_files = {graph.nodes[nid].get("source_file") for nid in seeds}
    unmatched = [f for f in files
                 if not any(str(mf or "").endswith(f) or f.endswith(str(mf or ""))
                            for mf in matched_files)]

    rel = set(relations) if relations is not None else set(IMPACT_RELATIONS)
    visited: dict[str, Hit] = {}
    q: deque[tuple[str, int]] = deque((s, 0) for s in seeds)
    for s in seeds:
        visited[s] = Hit(s, 0, "seed")

    while q:
        nid, depth = q.popleft()
        if depth >= max_depth:
            continue
        for other, edge in graph.neighbors(nid, relations=rel):
            if other in visited:
                continue
            visited[other] = Hit(other, depth + 1, edge.relation)
            q.append((other, depth + 1))

    hits = sorted(visited.values(), key=lambda h: (h.depth, graph.label(h.node_id)))

    by_comm: dict = defaultdict(list)
    for h in hits:
        by_comm[graph.community(h.node_id)].append(h.node_id)

    top_god = {nid for nid, _ in graph.god_nodes(top_n=10)}
    god_touched = [nid for nid in visited if nid in top_god]

    return BlastReport(seeds=seeds, hits=hits, by_community=dict(by_comm),
                       god_nodes_touched=god_touched, unmatched_files=unmatched)


def render_markdown(graph: Graph, report: BlastReport,
                    max_rows: int = 40) -> str:
    lines = ["# Blast radius", ""]
    lines.append(f"**Risk: {report.risk()}** — "
                 f"{len(report.seeds)} seed node(s), "
                 f"{len(report.hits)} reachable node(s), "
                 f"{len(report.by_community)} communit(ies) touched.")
    if report.god_nodes_touched:
        gods = ", ".join(f"`{graph.label(g)}`" for g in report.god_nodes_touched)
        lines.append(f"\n⚠️ **God nodes in range:** {gods} — extra review "
                     "and regression tests required here.")
    if report.unmatched_files:
        lines.append("\nFiles with no graph node (graph may be stale): "
                     + ", ".join(f"`{f}`" for f in report.unmatched_files[:10]))
    lines.append("\n| depth | node | via | location |")
    lines.append("|---|---|---|---|")
    from .graphio import _md_table_safe
    for h in report.hits[:max_rows]:
        lines.append(f"| {h.depth} | {_md_table_safe(graph.label(h.node_id))} | {h.via} | "
                     f"{_md_table_safe(graph.location(h.node_id))} |")
    if len(report.hits) > max_rows:
        lines.append(f"\n…and {len(report.hits) - max_rows} more.")
    return "\n".join(lines) + "\n"
