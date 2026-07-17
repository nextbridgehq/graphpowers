"""Community narratives: one-paragraph explanations of each community.

Derives a human-readable description from graph structure alone:
hub node, member labels, file paths, and cross-community relationships.
No LLM needed — deterministic, template-based output.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .graphio import Graph


@dataclass
class CommunityProfile:
    community_id: int
    node_count: int = 0
    hub_node: str = ""
    hub_label: str = ""
    member_labels: list[str] = field(default_factory=list)
    primary_files: list[str] = field(default_factory=list)
    incoming_relations: dict[str, int] = field(default_factory=dict)
    outgoing_relations: dict[str, int] = field(default_factory=dict)
    narrative: str = ""


def _infer_domain(files: list[str], labels: list[str]) -> str:
    """Guess a domain name from common path segments and labels."""
    # Try common directory segments first
    segments: list[str] = []
    for f in files:
        parts = f.replace("\\", "/").split("/")
        # Skip the filename itself and common roots like 'src'
        for p in parts[:-1]:
            if p.lower() not in ("src", "lib", "app", ".", ""):
                segments.append(p)
    if segments:
        most_common = Counter(segments).most_common(1)[0][0]
        return most_common

    # Fall back to common label prefix
    if labels:
        return labels[0].rstrip("()")

    return "unknown"


def profile_community(graph: Graph, community_id: int) -> CommunityProfile:
    """Build a structural profile of one community."""
    members = [nid for nid, attrs in graph.nodes.items()
               if attrs.get("community") == community_id]

    if not members:
        return CommunityProfile(
            community_id=community_id,
            narrative=f"Community {community_id} has no nodes in the graph.",
        )

    # Hub = highest-degree node in this community
    members_by_deg = sorted(members,
                            key=lambda n: (-graph.degree.get(n, 0), n))
    hub = members_by_deg[0]
    top_labels = [graph.label(n) for n in members_by_deg[:8]]

    # Primary files
    file_counts: Counter = Counter()
    for nid in members:
        sf = graph.nodes[nid].get("source_file")
        if sf:
            file_counts[str(sf)] += 1
    primary_files = [f for f, _ in file_counts.most_common(5)]

    # Cross-community edges
    member_set = set(members)
    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, int] = defaultdict(int)
    for nid in members:
        for other, edge in graph.neighbors(nid):
            if other not in member_set:
                # Determine direction
                if edge.target == nid or (not graph.directed and
                                          edge.source not in member_set):
                    incoming[edge.relation or "related"] += 1
                else:
                    outgoing[edge.relation or "related"] += 1

    profile = CommunityProfile(
        community_id=community_id,
        node_count=len(members),
        hub_node=hub,
        hub_label=graph.label(hub),
        member_labels=top_labels,
        primary_files=primary_files,
        incoming_relations=dict(incoming),
        outgoing_relations=dict(outgoing),
    )
    profile.narrative = narrate(profile)
    return profile


def narrate(profile: CommunityProfile) -> str:
    """Generate a one-paragraph narrative from the profile."""
    if profile.node_count == 0:
        return f"Community {profile.community_id} has no nodes in the graph."

    domain = _infer_domain(profile.primary_files, profile.member_labels)

    parts = [f"Community {profile.community_id} is the **{domain}** subsystem"]
    parts.append(f", centered on **{profile.hub_label}**.")
    parts.append(f" It contains {profile.node_count} node(s)")

    if profile.primary_files:
        short_files = [os.path.basename(f) for f in profile.primary_files[:3]]
        parts.append(f" primarily in {', '.join(short_files)}")

    parts.append(".")

    if profile.incoming_relations:
        rels = ", ".join(sorted(profile.incoming_relations.keys())[:3])
        parts.append(f" Other communities reach it via {rels}.")

    if profile.outgoing_relations:
        rels = ", ".join(sorted(profile.outgoing_relations.keys())[:3])
        parts.append(f" It depends outward via {rels}.")

    return "".join(parts)


def all_communities(graph: Graph) -> list[CommunityProfile]:
    """Profile every community in the graph, sorted by size (largest first)."""
    comm_ids: set[int] = set()
    for attrs in graph.nodes.values():
        c = attrs.get("community")
        if c is not None:
            comm_ids.add(int(c))

    profiles = [profile_community(graph, cid) for cid in sorted(comm_ids)]
    profiles.sort(key=lambda p: (-p.node_count, p.community_id))
    return profiles


def render_markdown(graph: Graph,
                    profiles: list[CommunityProfile]) -> str:
    """Markdown overview of all communities."""
    lines = ["# Community narratives", ""]
    lines.append(f"**{len(profiles)} communit(ies)** in the graph.")

    for p in profiles:
        lines.append(f"\n## Community {p.community_id} — "
                     f"{p.hub_label} ({p.node_count} nodes)")
        lines.append(f"\n{p.narrative}")

        if p.member_labels:
            members = ", ".join(f"`{l}`" for l in p.member_labels[:6])
            lines.append(f"\n**Key members:** {members}")

        if p.primary_files:
            files = ", ".join(f"`{f}`" for f in p.primary_files[:4])
            lines.append(f"\n**Files:** {files}")

    return "\n".join(lines) + "\n"
