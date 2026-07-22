"""Graph freshness: is graphify-out/graph.json still telling the truth?

Superpowers workflows should never plan or review against a stale map.
This module compares the graph file's mtime against source files changed
since it was built, and reports what needs re-extraction.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Mirrors graphify's watched code extensions (subset that matters most).
WATCHED_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rb", ".go", ".rs", ".java",
    ".kt", ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".php", ".scala",
    ".sql", ".sh", ".bash", ".r", ".R", ".md", ".proto", ".tf",
}
SKIP_DIRS = {".git", "node_modules", "graphify-out", "__pycache__",
             ".venv", "venv", "dist", "build", ".next", "target",
             ".ruff_cache", ".mypy_cache", ".pytest_cache", "coverage",
             ".tox", ".nox", ".eggs", ".hypothesis"}


@dataclass
class FreshnessReport:
    graph_path: Path
    graph_mtime: float
    stale_files: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def fresh(self) -> bool:
        return not self.stale_files

    def summary(self) -> str:
        if self.fresh:
            return (f"Graph is FRESH ({self.checked} source files checked "
                    f"against {self.graph_path}).")
        head = ", ".join(self.stale_files[:5])
        more = ("" if len(self.stale_files) <= 5
                else f" (+{len(self.stale_files) - 5} more)")
        return (f"Graph is STALE — {len(self.stale_files)} file(s) changed "
                f"since it was built: {head}{more}. "
                f"Run `graphify . --update` before planning or reviewing.")


def _git_tracked(root: Path) -> list[Path] | None:
    """Tracked files plus untracked-but-not-ignored files — a freshly
    created source file has no git history yet, but it's still a file
    the graph needs to know about. Mirrors the changed-file detection
    already used in blast_radius.git_changed_files()."""
    paths: list[str] = []
    for cmd in (["git", "ls-files"],
                ["git", "ls-files", "--others", "--exclude-standard"]):
        try:
            out = subprocess.run(cmd, cwd=root, text=True,
                                 capture_output=True, timeout=30, check=False)
            if out.returncode != 0:
                return None
            paths.extend(l for l in out.stdout.splitlines() if l.strip())
        except (OSError, subprocess.TimeoutExpired):
            return None
    seen: set[str] = set()
    uniq: list[Path] = []
    for l in paths:
        if l not in seen:
            seen.add(l)
            uniq.append(root / l)
    return uniq


def _walk(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            files.append(Path(dirpath) / f)
    return files


def check_freshness(root: str | Path = ".",
                    graph_path: str | Path | None = None) -> FreshnessReport:
    root = Path(root)
    gp = Path(graph_path) if graph_path else root / "graphify-out" / "graph.json"
    if not gp.exists():
        raise FileNotFoundError(f"No graph at {gp} — run graphify first.")
    gmt = gp.stat().st_mtime

    candidates = _git_tracked(root)
    if candidates is None:
        candidates = _walk(root)

    stale: list[str] = []
    checked = 0
    for f in candidates:
        if f.suffix not in WATCHED_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        checked += 1
        if mt > gmt:
            try:
                stale.append(f.relative_to(root).as_posix())
            except ValueError:
                stale.append(f.as_posix())
    stale.sort()
    return FreshnessReport(graph_path=gp, graph_mtime=gmt,
                           stale_files=stale, checked=checked)
