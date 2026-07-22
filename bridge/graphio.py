"""Zero-dependency reader for graphify's graph.json (networkx node-link format).

Graphify exports via ``networkx.readwrite.json_graph.node_link_data``:

    {
      "directed": bool, "multigraph": bool,
      "nodes": [{"id", "label", "source_file", "source_location",
                 "community", ...}],
      "links" | "edges": [{"source", "target", "relation", "confidence", ...}]
    }

This module deliberately avoids networkx so that the bridge stays
dependency-free (the Superpowers philosophy) and works even where only
graph.json is present, not the graphify package itself.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

DEFAULT_GRAPH_PATH = Path("graphify-out/graph.json")

# The graph.json contract this bridge understands. If graphify changes its
# export schema, we fail LOUDLY here rather than silently misbehave in
# blast/pack/drift downstream.
SCHEMA_VERSION = "node-link-v1"


class GraphSchemaError(ValueError):
    """graph.json doesn't match the schema this bridge version supports."""


def validate_node_link(raw: object, source: str = "graph.json") -> dict:
    """Validate the raw parsed JSON against the node-link contract.

    Checks structure only (keys and types), not semantics. Raises
    GraphSchemaError with an actionable message on any mismatch.
    """
    def fail(msg: str) -> None:
        raise GraphSchemaError(
            f"{source} is not a graph this bridge understands ({msg}). "
            f"Supported schema: networkx node-link ({SCHEMA_VERSION}) as "
            f"exported by graphify. If graphify recently updated, its "
            f"export format may have changed - check for a newer "
            f"graphpowers release or pin your graphify version."
        )

    if not isinstance(raw, dict):
        fail(f"top level is {type(raw).__name__}, expected object")
    if "nodes" not in raw:
        fail("missing 'nodes' key")
    if not isinstance(raw["nodes"], list):
        fail("'nodes' is not a list")
    links_key = "links" if "links" in raw else "edges" if "edges" in raw else None
    if links_key is None:
        fail("missing 'links'/'edges' key")
    if not isinstance(raw[links_key], list):
        fail(f"'{links_key}' is not a list")
    for i, n in enumerate(raw["nodes"][:200]):
        if not isinstance(n, dict) or "id" not in n:
            fail(f"node #{i} has no 'id'")
    for i, e in enumerate(raw[links_key][:200]):
        if not isinstance(e, dict) or "source" not in e or "target" not in e:
            fail(f"edge #{i} missing 'source'/'target'")

    # Referential integrity (sample-based, like node/edge checks)
    node_ids = {str(n.get("id")) for n in raw["nodes"]}
    dangling = []
    for i, e in enumerate(raw[links_key][:500]):
        src = str(e.get("source", ""))
        tgt = str(e.get("target", ""))
        if src not in node_ids:
            dangling.append((i, "source", src))
        if tgt not in node_ids:
            dangling.append((i, "target", tgt))
        if len(dangling) >= 5:
            break
    if dangling:
        examples = "; ".join(
            f"edge #{i} {field}='{val}'" for i, field, val in dangling[:3]
        )
        fail(f"edges reference non-existent nodes: {examples}")

    return raw

# Relations along which change propagates (mirrors graphify's affected.py).
IMPACT_RELATIONS = frozenset({
    "calls", "indirect_call", "references", "imports", "imports_from",
    "re_exports", "inherits", "extends", "implements", "uses",
    "mixes_in", "embeds",
})


@dataclass
class Edge:
    source: str
    target: str
    relation: str = ""
    confidence: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class Graph:
    """Lightweight adjacency view over a graphify graph.json."""

    nodes: dict[str, dict]                 # id -> node attrs
    edges: list[Edge]
    directed: bool = False
    path: Optional[Path] = None

    # --- derived indexes (built lazily) ---
    _adj: Optional[dict[str, list[Edge]]] = None
    _by_file: Optional[dict[str, list[str]]] = None
    _degree: Optional[dict[str, int]] = None
    _impact_degree: Optional[dict[str, int]] = None

    # ---------- construction ----------

    @classmethod
    def load(cls, path: str | Path = DEFAULT_GRAPH_PATH) -> "Graph":
        p = Path(path)
        if p.is_dir():
            p = p / "graph.json"
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise GraphSchemaError(
                f"{p} is not valid JSON ({e}). The graph file may be "
                f"corrupted or a partial write - rebuild with `graphify .`."
            ) from e
        validate_node_link(raw, source=str(p))
        return cls.from_node_link(raw, path=p)

    @classmethod
    def from_node_link(cls, raw: dict, path: Optional[Path] = None) -> "Graph":
        nodes: dict[str, dict] = {}
        for n in raw.get("nodes", []):
            nid = str(n.get("id"))
            nodes[nid] = n
        links_key = "links" if "links" in raw else "edges"
        edges: list[Edge] = []
        for e in raw.get(links_key, []):
            edges.append(Edge(
                source=str(e.get("source")),
                target=str(e.get("target")),
                relation=str(e.get("relation", "") or ""),
                confidence=str(e.get("confidence", "") or ""),
                data=e,
            ))
        return cls(nodes=nodes, edges=edges,
                   directed=bool(raw.get("directed", False)), path=path)

    # ---------- indexes ----------

    @property
    def adj(self) -> dict[str, list[Edge]]:
        """Undirected adjacency: node id -> incident edges."""
        if self._adj is None:
            adj: dict[str, list[Edge]] = defaultdict(list)
            for e in self.edges:
                adj[e.source].append(e)
                adj[e.target].append(e)
            self._adj = dict(adj)
        return self._adj

    @property
    def by_file(self) -> dict[str, list[str]]:
        """source_file -> node ids. Keys are normalized with as_posix()."""
        if self._by_file is None:
            idx: dict[str, list[str]] = defaultdict(list)
            for nid, attrs in self.nodes.items():
                sf = attrs.get("source_file")
                if sf:
                    idx[Path(str(sf)).as_posix()].append(nid)
            self._by_file = dict(idx)
        return self._by_file

    @property
    def degree(self) -> dict[str, int]:
        if self._degree is None:
            deg: dict[str, int] = defaultdict(int)
            for e in self.edges:
                deg[e.source] += 1
                deg[e.target] += 1
            for nid in self.nodes:
                deg.setdefault(nid, 0)
            self._degree = dict(deg)
        return self._degree

    @property
    def impact_degree(self) -> dict[str, int]:
        """Degree counting only IMPACT_RELATIONS edges — excludes
        structural-only edges (contains, defines, declares, documents)
        so a node isn't ranked a god node merely for containing a lot
        of code."""
        if self._impact_degree is None:
            deg: dict[str, int] = defaultdict(int)
            for e in self.edges:
                if e.relation in IMPACT_RELATIONS:
                    deg[e.source] += 1
                    deg[e.target] += 1
            for nid in self.nodes:
                deg.setdefault(nid, 0)
            self._impact_degree = dict(deg)
        return self._impact_degree

    # ---------- helpers ----------

    def label(self, node_id: str) -> str:
        attrs = self.nodes.get(node_id, {})
        return str(attrs.get("label") or node_id)

    def location(self, node_id: str) -> str:
        attrs = self.nodes.get(node_id, {})
        sf = attrs.get("source_file") or "-"
        loc = attrs.get("source_location")
        return f"{sf}:{loc}" if loc else str(sf)

    def community(self, node_id: str):
        return self.nodes.get(node_id, {}).get("community")

    def neighbors(self, node_id: str,
                  relations: Optional[Iterable[str]] = None
                  ) -> Iterator[tuple[str, Edge]]:
        rel = set(relations) if relations is not None else None
        for e in self.adj.get(node_id, []):
            if rel is not None and e.relation not in rel:
                continue
            other = e.target if e.source == node_id else e.source
            yield other, e

    def god_nodes(self, top_n: int = 10,
                  min_degree: int | None = None) -> list[tuple[str, int]]:
        """Highest-impact-degree nodes — the load-bearing walls of the
        codebase.

        Ranked by ``impact_degree`` (calls/imports/inherits/... only) so
        that structural containment (a file `contains` many functions)
        doesn't by itself make a node a god node.

        A node only qualifies if its impact degree is at least
        ``min_degree`` (default: 2× the mean impact degree, floor 4) so
        that tiny graphs don't flag every node as load-bearing.
        """
        deg = self.impact_degree
        if min_degree is None:
            mean = sum(deg.values()) / len(deg) if deg else 0
            min_degree = max(4, int(mean * 2))
        ranked = sorted(deg.items(), key=lambda kv: (-kv[1], kv[0]))
        return [(nid, d) for nid, d in ranked[:top_n] if d >= min_degree]

    def nodes_for_files(self, files: Iterable[str | Path]) -> list[str]:
        """Map changed file paths to node ids (exact or suffix match)."""
        out: list[str] = []
        index = self.by_file
        keys = list(index.keys())
        for f in files:
            fp = Path(str(f)).as_posix()
            if fp in index:
                out.extend(index[fp])
                continue
            # suffix match handles graph built from a parent/child directory
            for k in keys:
                if k.endswith(fp) or fp.endswith(k):
                    out.extend(index[k])
        # dedupe, keep order
        seen: set[str] = set()
        uniq = []
        for nid in out:
            if nid not in seen:
                seen.add(nid)
                uniq.append(nid)
        return uniq


def estimate_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token) — good enough for budgeting."""
    return max(1, len(text) // 4)


def _md_table_safe(text: str) -> str:
    """Escape pipe characters for Markdown table cells."""
    return text.replace("|", "\\|")
