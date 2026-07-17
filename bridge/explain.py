"""Explain: unified view of a concept in the codebase.

One command answers: what is it, what connects to it, what's at stake
if you change it, and what context does a subagent need to work on it.

Orchestrates existing modules: lookup, blast_radius, context_pack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .graphio import Graph
from . import blast_radius as br
from . import context_pack as cp
from . import lookup


@dataclass
class ExplainReport:
    term: str
    matched_node: Optional[str] = None
    candidates: list[str] = field(default_factory=list)
    usage: Optional[lookup.UsageReport] = None
    blast: Optional[br.BlastReport] = None
    pack_text: str = ""


def explain(graph: Graph, term: str,
            budget: int = 800) -> ExplainReport:
    """Build a unified explanation of a term in the codebase."""
    nid, candidates = lookup.find_node(graph, term)
    report = ExplainReport(term=term, matched_node=nid, candidates=candidates)

    if nid is None:
        return report

    # Usage (who connects to this node)
    report.usage = lookup.who_uses(graph, term)

    # Blast radius (what's at stake)
    source_file = graph.nodes.get(nid, {}).get("source_file")
    if source_file:
        report.blast = br.blast_radius(graph, [str(source_file)])

    # Context pack (subagent briefing)
    seed_files = [str(source_file)] if source_file else []
    report.pack_text = cp.build_pack(graph, term, seed_files=seed_files,
                                     budget_tokens=budget)

    return report


def render_markdown(graph: Graph, report: ExplainReport) -> str:
    """Render the unified explanation as markdown."""
    if report.matched_node is None:
        lines = [f"# \"{report.term}\" in this codebase", ""]
        lines.append(f"No node matching `{report.term}` in the graph. "
                     "Check spelling or rebuild the graph.")
        if report.candidates:
            alts = ", ".join(f"`{graph.label(c)}`" for c in report.candidates)
            lines.append(f"\nDid you mean: {alts}")
        return "\n".join(lines) + "\n"

    nid = report.matched_node
    lines = [f"# \"{report.term}\" in this codebase", ""]

    # Section 1: Graph says
    lines.append("## Graph says")
    deg = graph.degree.get(nid, 0)
    comm = graph.community(nid)
    lines.append(f"- **{graph.label(nid)}** — {graph.location(nid)} "
                 f"(degree {deg}, community {comm})")

    if report.candidates:
        alts = ", ".join(f"`{graph.label(c)}`" for c in report.candidates[:3])
        lines.append(f"- Other matches: {alts}")

    if report.usage and report.usage.consumers:
        lines.append("\n**Relationships:**")
        for rel, nodes in sorted(report.usage.consumers.items()):
            for n in nodes[:5]:
                lines.append(f"- `{graph.label(nid)}` —{rel}→ "
                             f"`{graph.label(n)}`")
            if len(nodes) > 5:
                lines.append(f"- …and {len(nodes) - 5} more {rel}")

    # Section 2: Blast radius
    if report.blast:
        lines.append(f"\n## Blast radius if you touch it")
        lines.append(f"**Risk: {report.blast.risk()}** — "
                     f"{len(report.blast.hits)} node(s), "
                     f"{len(report.blast.by_community)} communit(ies)")
        if report.blast.god_nodes_touched:
            gods = ", ".join(f"`{graph.label(g)}`"
                            for g in report.blast.god_nodes_touched)
            lines.append(f"\n⚠️ God nodes in range: {gods}")

    # Section 3: Context pack
    if report.pack_text:
        lines.append(f"\n## Context pack (for subagent)")
        # Demote headings inside the pack
        for pack_line in report.pack_text.splitlines():
            if pack_line.startswith("# "):
                lines.append(f"####{pack_line[1:]}")
            else:
                lines.append(pack_line)

    return "\n".join(lines) + "\n"
