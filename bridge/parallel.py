"""Parallel safety: compute which tasks can run concurrently.

Given a list of task specs (id + file list), compute blast radius for
each, find pairwise overlaps, and produce a parallel execution plan.
Tasks with overlapping blast radii must be sequential; the rest can
run in parallel.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable

from .graphio import Graph
from . import blast_radius as br


@dataclass
class TaskSpec:
    id: str
    files: list[str]


@dataclass
class Conflict:
    task_a: str
    task_b: str
    overlapping_nodes: list[str]
    shared_communities: list[int] = field(default_factory=list)


@dataclass
class ParallelPlan:
    tasks: list[TaskSpec]
    conflicts: list[Conflict] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    sequential_pairs: list[tuple[str, str]] = field(default_factory=list)


def parse_tasks(text: str) -> list[TaskSpec]:
    """Parse task specs from JSON text (stdin)."""
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError("Expected a JSON array of task specs")
    tasks: list[TaskSpec] = []
    for item in raw:
        tasks.append(TaskSpec(
            id=str(item.get("id", f"task-{len(tasks)}")),
            files=list(item.get("files", [])),
        ))
    return tasks


def parallel_safety(graph: Graph,
                    tasks: list[TaskSpec],
                    max_depth: int = 2) -> ParallelPlan:
    """Given task specs, compute which can run in parallel.

    Algorithm:
    1. Compute blast radius for each task
    2. Check all pairwise overlaps
    3. Build a conflict graph
    4. Find independent sets (greedy graph coloring)
    """
    # Step 1: blast radius per task
    radii: dict[str, set[str]] = {}
    for t in tasks:
        report = br.blast_radius(graph, t.files, max_depth=max_depth)
        radii[t.id] = {h.node_id for h in report.hits}

    # Step 2: pairwise overlaps
    conflicts: list[Conflict] = []
    conflict_graph: dict[str, set[str]] = defaultdict(set)
    for (a, ra), (b, rb) in combinations(radii.items(), 2):
        overlap = sorted(ra & rb)
        if overlap:
            shared_comms: list[int] = []
            seen: set = set()
            for nid in overlap:
                c = graph.community(nid)
                if c is not None and c not in seen:
                    seen.add(c)
                    shared_comms.append(c)
            conflicts.append(Conflict(
                task_a=a, task_b=b,
                overlapping_nodes=overlap,
                shared_communities=sorted(shared_comms),
            ))
            conflict_graph[a].add(b)
            conflict_graph[b].add(a)

    # Step 3: greedy graph coloring for independent sets
    task_ids = [t.id for t in tasks]
    colors: dict[str, int] = {}
    for tid in task_ids:
        neighbor_colors = {colors[n] for n in conflict_graph.get(tid, set())
                          if n in colors}
        color = 0
        while color in neighbor_colors:
            color += 1
        colors[tid] = color

    # Group by color
    groups: dict[int, list[str]] = defaultdict(list)
    for tid, color in colors.items():
        groups[color].append(tid)
    parallel_groups = [sorted(g) for g in
                       sorted(groups.values(), key=lambda g: min(g))]

    # Sequential pairs = conflict edges
    sequential = [(c.task_a, c.task_b) for c in conflicts]

    return ParallelPlan(
        tasks=tasks,
        conflicts=conflicts,
        parallel_groups=parallel_groups,
        sequential_pairs=sequential,
    )


def render_markdown(graph: Graph, plan: ParallelPlan) -> str:
    """Markdown report with parallel groups and conflict details."""
    lines = ["# Parallel safety analysis", ""]

    n_tasks = len(plan.tasks)
    n_conflicts = len(plan.conflicts)
    n_groups = len(plan.parallel_groups)

    if n_conflicts == 0:
        lines.append(f"**✅ All {n_tasks} tasks can run in parallel** — "
                     "no blast radius overlaps detected.")
    else:
        lines.append(f"**⚠️ {n_conflicts} conflict(s)** among {n_tasks} tasks "
                     f"— split into {n_groups} sequential group(s).")

    lines.append(f"\n## Execution groups ({n_groups})")
    lines.append("\nTasks within the same group can run in parallel. "
                 "Groups must run sequentially.")
    for i, group in enumerate(plan.parallel_groups):
        task_list = ", ".join(f"`{tid}`" for tid in group)
        lines.append(f"\n**Group {i + 1}:** {task_list}")

    if plan.conflicts:
        lines.append("\n## Conflicts")
        for c in plan.conflicts:
            lines.append(f"\n**`{c.task_a}` ↔ `{c.task_b}`** — "
                         f"{len(c.overlapping_nodes)} shared node(s)")
            if c.shared_communities:
                comms = ", ".join(str(x) for x in c.shared_communities)
                lines.append(f"  Communities: {comms}")
            top = c.overlapping_nodes[:5]
            nodes = ", ".join(f"`{graph.label(n)}`" for n in top)
            if len(c.overlapping_nodes) > 5:
                nodes += f" (+{len(c.overlapping_nodes) - 5} more)"
            lines.append(f"  Nodes: {nodes}")

    return "\n".join(lines) + "\n"
