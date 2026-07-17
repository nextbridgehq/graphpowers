"""Context packs: token-budgeted briefings for subagents.

Superpowers' subagent-driven-development dispatches fresh subagents per
task, and each one normally re-discovers the codebase from scratch.
A context pack replaces that with a pre-digested, graph-derived brief:
the relevant nodes, their relationships, their file:line locations, and
the exact files worth reading — all trimmed to a token budget.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .pack_feedback import ScoringWeights as _SW

from .graphio import Graph, estimate_tokens

_WORD = re.compile(r"[A-Za-z0-9_]+")


def _terms(text: str) -> set[str]:
    """Lowercased terms incl. camelCase / snake_case splits."""
    out: set[str] = set()
    for w in _WORD.findall(text):
        out.add(w.lower())
        for part in re.split(r"_+", w):
            if part:
                out.add(part.lower())
        for part in re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", w):
            if part:
                out.add(part.lower())
    return out


@dataclass
class ScoredNode:
    node_id: str
    score: float


def score_nodes(graph: Graph, query: str,
                seed_files: Optional[Iterable[str]] = None,
                weights: Optional["_SW"] = None) -> list[ScoredNode]:
    qterms = _terms(query)
    seeds = set(graph.nodes_for_files(seed_files or []))

    # Use provided weights or defaults
    seed_boost = 3.0
    deg_tiebreaker = 0.5
    community_bonus = 0.0
    hub_penalty = 0.0
    if weights is not None:
        seed_boost = weights.seed_boost
        deg_tiebreaker = weights.degree_tiebreaker
        community_bonus = weights.community_bonus
        hub_penalty = weights.hub_penalty

    ranked: list[ScoredNode] = []
    max_deg = max(graph.degree.values(), default=1) or 1
    for nid, attrs in graph.nodes.items():
        label_terms = _terms(str(attrs.get("label", "")) + " " + nid)
        overlap = len(qterms & label_terms)
        score = float(overlap)
        if nid in seeds:
            score += seed_boost
        if overlap:
            # small tiebreaker: central nodes are more likely to matter
            deg_ratio = graph.degree.get(nid, 0) / max_deg
            score += deg_tiebreaker * deg_ratio
            # hub penalty: very central nodes are often included but unused
            if hub_penalty > 0 and deg_ratio > 0.7:
                score -= hub_penalty
            # community bonus: nodes in the same community as seeds
            if community_bonus > 0 and seeds:
                node_comm = graph.community(nid)
                seed_comms = {graph.community(s) for s in seeds}
                if node_comm is not None and node_comm in seed_comms:
                    score += community_bonus
        if score > 0:
            ranked.append(ScoredNode(nid, score))
    ranked.sort(key=lambda s: (-s.score, s.node_id))
    return ranked


def build_pack(graph: Graph, task: str,
               seed_files: Optional[Iterable[str]] = None,
               budget_tokens: int = 1200,
               max_core: int = 12) -> str:
    """Render a markdown context pack for one task, within budget_tokens."""
    ranked = score_nodes(graph, task, seed_files)
    core = [s.node_id for s in ranked[:max_core]]

    # one-hop expansion, highest-confidence first
    halo: dict[str, str] = {}
    for nid in core:
        for other, edge in graph.neighbors(nid):
            if other not in core and other not in halo:
                halo[other] = edge.relation

    # relationships among core + halo
    keep = set(core) | set(halo)
    rels: list[str] = []
    seen_pairs: set[tuple] = set()
    for nid in core:
        for other, edge in graph.neighbors(nid):
            if other not in keep:
                continue
            pair = tuple(sorted((nid, other))) + (edge.relation,)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            conf = f" ({edge.confidence})" if edge.confidence == "AMBIGUOUS" else ""
            rels.append(f"- `{graph.label(edge.source)}` —{edge.relation}→ "
                        f"`{graph.label(edge.target)}`{conf}")

    rels.sort()  # Deterministic output regardless of adjacency iteration order

    files: dict[str, int] = defaultdict(int)
    for nid in core:
        sf = graph.nodes[nid].get("source_file")
        if sf:
            files[str(sf)] += 1
    read_list = sorted(files, key=lambda f: -files[f])[:8]

    comms = sorted({str(graph.community(n)) for n in core
                    if graph.community(n) is not None})

    def render(n_core: int, n_rels: int, n_files: int) -> str:
        lines = [f"# Context pack: {task.strip()}", ""]
        if comms:
            lines.append(f"Touches communit(ies): {', '.join(comms)}.")
        lines.append("\n## Key nodes")
        for nid in core[:n_core]:
            lines.append(f"- **{graph.label(nid)}** — {graph.location(nid)}")
        if rels:
            lines.append("\n## Relationships")
            lines.extend(rels[:n_rels])
        if read_list:
            lines.append("\n## Read these files first")
            for f in read_list[:n_files]:
                lines.append(f"- `{f}`")
        lines.append("\n## Ground rules")
        lines.append("- Trust EXTRACTED edges; verify AMBIGUOUS ones in source "
                     "before relying on them.")
        lines.append("- If a node you need is missing here, query the graph "
                     "(`graphify query \"...\"`) instead of grepping blind.")
        return "\n".join(lines) + "\n"

    # shrink until within budget
    n_core, n_rels, n_files = len(core), len(rels), len(read_list)
    text = render(n_core, n_rels, n_files)
    while estimate_tokens(text) > budget_tokens and (n_core > 3 or n_rels > 3):
        if n_rels > 3:
            n_rels = max(3, int(n_rels * 0.7))
        elif n_core > 3:
            n_core -= 1
        n_files = min(n_files, 5)
        text = render(n_core, n_rels, n_files)
    return text
