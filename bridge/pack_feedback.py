"""Pack quality feedback: close the loop from subagent back to scoring.

After a subagent finishes a task, it logs whether the context pack was
sufficient.  Over time, compute_weights() adjusts scoring parameters
so that score_nodes() in context_pack.py produces better packs.

Storage: one JSONL file per project at graphpowers-data/pack-feedback.jsonl.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_DATA_DIR = Path("graphpowers-data")
_FEEDBACK_FILE = "pack-feedback.jsonl"


@dataclass
class PackFeedback:
    task_id: str
    timestamp: str
    pack_node_ids: list[str]
    pack_was_sufficient: bool
    extra_reads: list[str] = field(default_factory=list)
    unused_nodes: list[str] = field(default_factory=list)


@dataclass
class ScoringWeights:
    seed_boost: float = 3.0
    degree_tiebreaker: float = 0.5
    community_bonus: float = 0.0
    hub_penalty: float = 0.0


def log_feedback(feedback: PackFeedback,
                 data_dir: Path = DEFAULT_DATA_DIR) -> None:
    """Append one feedback record to the JSONL log."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / _FEEDBACK_FILE
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(feedback), ensure_ascii=False) + "\n")


def load_history(data_dir: Path = DEFAULT_DATA_DIR,
                 limit: int = 100) -> list[PackFeedback]:
    """Load recent feedback records, newest last (append order)."""
    path = data_dir / _FEEDBACK_FILE
    if not path.exists():
        return []
    entries: list[PackFeedback] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            entries.append(PackFeedback(
                task_id=d["task_id"],
                timestamp=d["timestamp"],
                pack_node_ids=d.get("pack_node_ids", []),
                pack_was_sufficient=d.get("pack_was_sufficient", True),
                extra_reads=d.get("extra_reads", []),
                unused_nodes=d.get("unused_nodes", []),
            ))
        except (json.JSONDecodeError, KeyError):
            continue  # skip corrupted lines
    return entries[-limit:]


def compute_weights(history: list[PackFeedback]) -> ScoringWeights:
    """Learn scoring weights from feedback history.

    Simple heuristics (no ML):
    - If >30% of packs were insufficient -> boost seed_boost
    - If >30% of packs had unused nodes -> apply hub_penalty
    - If extra_reads are common -> boost community_bonus
    """
    w = ScoringWeights()
    if not history:
        return w

    n = len(history)
    insufficient = sum(1 for fb in history if not fb.pack_was_sufficient)
    with_unused = sum(1 for fb in history if fb.unused_nodes)
    with_extra = sum(1 for fb in history if fb.extra_reads)

    insufficient_rate = insufficient / n
    unused_rate = with_unused / n
    extra_rate = with_extra / n

    # Boost seed relevance when packs are often insufficient
    if insufficient_rate > 0.3:
        w.seed_boost = 3.0 + min(2.0, insufficient_rate * 3.0)

    # Penalize hubs when they're often included but unused
    if unused_rate > 0.3:
        w.hub_penalty = min(1.0, unused_rate * 1.5)

    # Boost community affinity when agents need extra files
    if extra_rate > 0.3:
        w.community_bonus = min(1.5, extra_rate * 2.0)

    return w


def render_stats(history: list[PackFeedback]) -> str:
    """Markdown summary of pack quality over time."""
    if not history:
        return "# Pack quality\n\nNo feedback logged yet.\n"

    n = len(history)
    sufficient = sum(1 for fb in history if fb.pack_was_sufficient)
    with_extra = sum(1 for fb in history if fb.extra_reads)
    with_unused = sum(1 for fb in history if fb.unused_nodes)

    lines = ["# Pack quality", ""]
    lines.append(f"**{n} feedback entries** — "
                 f"{sufficient}/{n} packs sufficient "
                 f"({100 * sufficient // n}%).")
    lines.append(f"- Packs where agent needed extra files: {with_extra}")
    lines.append(f"- Packs with unused nodes: {with_unused}")

    if with_extra:
        all_extra: dict[str, int] = {}
        for fb in history:
            for f in fb.extra_reads:
                all_extra[f] = all_extra.get(f, 0) + 1
        top = sorted(all_extra.items(), key=lambda kv: -kv[1])[:5]
        lines.append("\n## Most-missed files")
        for f, count in top:
            lines.append(f"- `{f}` ({count}x)")

    w = compute_weights(history)
    lines.append("\n## Current learned weights")
    lines.append(f"- seed_boost: {w.seed_boost:.2f} (default 3.00)")
    lines.append(f"- degree_tiebreaker: {w.degree_tiebreaker:.2f}")
    lines.append(f"- community_bonus: {w.community_bonus:.2f}")
    lines.append(f"- hub_penalty: {w.hub_penalty:.2f}")

    return "\n".join(lines) + "\n"
