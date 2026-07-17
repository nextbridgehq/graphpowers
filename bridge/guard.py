"""Implementation guard: catch scope creep during a task.

Plan time: blast radius computed for the planned file set.
Mid-task:  compare actual touched files against the plan.
If the actual blast radius exceeds the planned one, flag it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .graphio import Graph
from . import blast_radius as br


@dataclass
class GuardReport:
    planned_files: list[str]
    touched_files: list[str]
    planned_radius_size: int
    actual_radius_size: int
    surprise_nodes: list[str] = field(default_factory=list)
    surprise_communities: list[int] = field(default_factory=list)
    scope_creep: bool = False
    recommendation: str = ""

    def to_dict(self, graph: "Graph") -> dict:
        return {
            "scope_creep": self.scope_creep,
            "planned_files": self.planned_files,
            "touched_files": self.touched_files,
            "planned_radius_size": self.planned_radius_size,
            "actual_radius_size": self.actual_radius_size,
            "surprise_nodes": [
                {"id": n, "label": graph.label(n), "location": graph.location(n)}
                for n in self.surprise_nodes
            ],
            "surprise_communities": self.surprise_communities,
            "recommendation": self.recommendation,
        }


def implementation_guard(graph: Graph,
                         planned_files: list[str],
                         touched_files: list[str] | None = None,
                         max_depth: int = 2) -> GuardReport:
    """Compare planned vs actual blast radius.

    Returns a report flagging scope creep — nodes reachable from
    actual changes that weren't reachable from the plan.
    """
    if touched_files is None:
        touched_files = br.git_changed_files()

    planned_report = br.blast_radius(graph, planned_files, max_depth=max_depth)
    actual_report = br.blast_radius(graph, touched_files, max_depth=max_depth)

    planned_ids = {h.node_id for h in planned_report.hits}
    actual_ids = {h.node_id for h in actual_report.hits}

    surprise = sorted(actual_ids - planned_ids)

    surprise_comms: list[int] = []
    planned_comms = {graph.community(nid) for nid in planned_ids}
    for nid in surprise:
        c = graph.community(nid)
        if c is not None and c not in planned_comms and c not in surprise_comms:
            surprise_comms.append(c)

    creep = len(surprise) > 0

    if creep:
        if surprise_comms:
            rec = (f"Scope creep into {len(surprise_comms)} new communit(ies). "
                   "Split this task or update the plan before continuing.")
        else:
            rec = ("Additional nodes in blast radius. "
                   "Review whether these changes are intentional, "
                   "then update the plan or split the task.")
    else:
        rec = "Implementation is within planned scope."

    return GuardReport(
        planned_files=planned_files,
        touched_files=touched_files,
        planned_radius_size=len(planned_report.hits),
        actual_radius_size=len(actual_report.hits),
        surprise_nodes=surprise,
        surprise_communities=surprise_comms,
        scope_creep=creep,
        recommendation=rec,
    )


def render_markdown(graph: Graph, report: GuardReport,
                    max_rows: int = 20) -> str:
    """Markdown report of guard findings."""
    lines = ["# Implementation guard", ""]

    if report.scope_creep:
        lines.append(f"**⚠️ Scope creep detected** — "
                     f"{len(report.surprise_nodes)} surprise node(s) outside "
                     f"planned blast radius.")
    else:
        lines.append("**✅ No scope creep** — actual changes are within "
                     "planned blast radius.")

    lines.append(f"\nPlanned radius: {report.planned_radius_size} node(s) "
                 f"from {len(report.planned_files)} file(s).")
    lines.append(f"Actual radius: {report.actual_radius_size} node(s) "
                 f"from {len(report.touched_files)} file(s).")

    if report.surprise_nodes:
        lines.append("\n## Surprise nodes")
        for nid in report.surprise_nodes[:max_rows]:
            lines.append(f"- **{graph.label(nid)}** — {graph.location(nid)}")
        if len(report.surprise_nodes) > max_rows:
            lines.append(f"- …and {len(report.surprise_nodes) - max_rows} more")

    if report.surprise_communities:
        comms = ", ".join(str(c) for c in report.surprise_communities)
        lines.append(f"\n**New communities entered:** {comms}")

    lines.append(f"\n**Recommendation:** {report.recommendation}")

    return "\n".join(lines) + "\n"
