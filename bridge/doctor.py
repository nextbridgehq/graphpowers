"""Graphpowers doctor: check prerequisites and project readiness."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .graphio import DEFAULT_GRAPH_PATH


@dataclass
class DoctorReport:
    python_ok: bool = False
    python_version: str = ""
    git_ok: bool = False
    git_version: str = ""
    graphpowers_version: str = ""
    graphify_ok: bool = False
    graphify_version: str = ""
    superpowers_detected: bool | None = None  # None = can't check
    graph_exists: bool = False
    graph_fresh: bool | None = None  # None = not checked
    stale_files: list[str] = field(default_factory=list)
    data_dir_exists: bool = False
    errors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """Minimum viable: python + graph exists."""
        return self.python_ok and self.graph_exists

    @property
    def fully_ready(self) -> bool:
        """Full stack: python + git + graphify + graph + fresh."""
        return (self.python_ok and self.git_ok and self.graphify_ok
                and self.graph_exists and self.graph_fresh is not False)


def _run(cmd: list[str], timeout: int = 10) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def check(root: Path = Path("."),
          graph_path: Path | None = None) -> DoctorReport:
    """Run all prerequisite and project checks."""
    rep = DoctorReport()

    # Python
    rep.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    rep.python_ok = sys.version_info >= (3, 9)
    if not rep.python_ok:
        rep.errors.append(f"Python {rep.python_version} is below minimum 3.9")
        rep.recommendations.append("Upgrade Python to 3.9 or later")

    # Graphpowers
    from . import __version__
    rep.graphpowers_version = __version__

    # Git
    git_out = _run(["git", "--version"])
    if git_out:
        rep.git_ok = True
        rep.git_version = git_out.replace("git version ", "")
    else:
        rep.errors.append("Git not found")
        rep.recommendations.append("Install git (needed for freshness checks and blast auto-detection)")

    # Graphify
    graphify_path = shutil.which("graphify")
    if graphify_path:
        rep.graphify_ok = True
        ver = _run(["graphify", "--version"])
        rep.graphify_version = ver or "installed (version unknown)"
    else:
        rep.recommendations.append(
            "Install graphify to build/update graphs: pip install graphify")

    # Superpowers (best-effort detection)
    # Check common locations for superpowers skills
    sp_locations = [
        Path.home() / ".config" / "superpowers",
        Path.home() / ".superpowers",
        root / ".superpowers",
    ]
    # Also check if the environment suggests Claude Code plugins
    claude_plugin = Path(
        subprocess.os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    ) if "CLAUDE_PLUGIN_ROOT" in subprocess.os.environ else None

    for loc in sp_locations:
        if loc.is_dir() and (loc / "skills").is_dir():
            rep.superpowers_detected = True
            break
    if claude_plugin and (claude_plugin / "skills").is_dir():
        rep.superpowers_detected = True
    if rep.superpowers_detected is None:
        rep.superpowers_detected = None  # can't determine

    # Graph
    gp = graph_path or root / DEFAULT_GRAPH_PATH
    if gp.is_dir():
        gp = gp / "graph.json"
    rep.graph_exists = gp.exists()

    if not rep.graph_exists:
        if rep.graphify_ok:
            rep.recommendations.append(
                f"No graph found at {gp}. Build one: graphify .")
        else:
            rep.recommendations.append(
                f"No graph found at {gp}. Install graphify first (pip install graphify), then run: graphify .")
    else:
        # Freshness
        try:
            from .freshness import check_freshness
            fr = check_freshness(root, gp)
            rep.graph_fresh = fr.fresh
            rep.stale_files = fr.stale_files
            if not fr.fresh:
                rep.recommendations.append(
                    f"Graph is stale ({len(fr.stale_files)} file(s) changed). "
                    f"Run: graphify . --update")
        except Exception:
            rep.graph_fresh = None

    # Data dir
    rep.data_dir_exists = (root / "graphpowers-data").is_dir()

    return rep


def render_markdown(rep: DoctorReport) -> str:
    """Render the doctor report as markdown."""
    lines = ["# Graphpowers Doctor", ""]

    # Verdict
    if rep.fully_ready:
        lines.append("**✅ READY** — all prerequisites met, graph is fresh.")
    elif rep.ready:
        lines.append("**⚠️ PARTIALLY READY** — bridge commands will work, "
                     "but some features need attention.")
    else:
        lines.append("**❌ NOT READY** — fix the issues below before using graphpowers.")

    # Prerequisites
    lines.append("\n## Prerequisites")
    lines.append("")
    lines.append(f"| Tool | Status | Details |")
    lines.append(f"|------|--------|---------|")

    # Python
    py_status = "✅" if rep.python_ok else "❌"
    lines.append(f"| Python 3.9+ | {py_status} | {rep.python_version} |")

    # Git
    git_status = "✅" if rep.git_ok else "❌"
    git_detail = rep.git_version if rep.git_ok else "not found"
    lines.append(f"| Git | {git_status} | {git_detail} |")

    # Graphify
    gfy_status = "✅" if rep.graphify_ok else "❌ not installed"
    gfy_detail = rep.graphify_version if rep.graphify_ok else "`pip install graphify`"
    lines.append(f"| Graphify | {gfy_status} | {gfy_detail} |")

    # Graphpowers
    if rep.graphpowers_version != "0.1.0":
        lines.append(f"| Graphpowers | ⚠️ | v{rep.graphpowers_version} (expected v0.1.0) |")
    else:
        lines.append(f"| Graphpowers | ✅ | v{rep.graphpowers_version} |")

    # Superpowers
    if rep.superpowers_detected is True:
        sp_status = "✅"
        sp_detail = "detected"
    elif rep.superpowers_detected is False:
        sp_status = "❌"
        sp_detail = "not found"
    else:
        sp_status = "⚠️"
        sp_detail = "cannot detect (check Claude Code plugins)"
    lines.append(f"| Superpowers | {sp_status} | {sp_detail} |")

    # Project status
    lines.append("\n## Project Status")
    lines.append("")

    # Graph
    if rep.graph_exists:
        if rep.graph_fresh is True:
            lines.append("- **graph.json:** ✅ exists and is fresh")
        elif rep.graph_fresh is False:
            lines.append(f"- **graph.json:** ⚠️ exists but STALE "
                         f"({len(rep.stale_files)} file(s) changed)")
            for f in rep.stale_files[:5]:
                lines.append(f"  - `{f}`")
            if len(rep.stale_files) > 5:
                lines.append(f"  - …and {len(rep.stale_files) - 5} more")
        else:
            lines.append("- **graph.json:** ✅ exists (freshness unknown)")
    else:
        lines.append("- **graph.json:** ❌ not found")

    # Data dir
    if rep.data_dir_exists:
        lines.append("- **graphpowers-data/:** ✅ exists (pack feedback active)")
    else:
        lines.append("- **graphpowers-data/:** — not yet created "
                     "(created on first `pack-feedback log`)")

    # Recommendations
    if rep.recommendations:
        lines.append("\n## Recommendations")
        lines.append("")
        for i, rec in enumerate(rep.recommendations, 1):
            lines.append(f"{i}. {rec}")

    # What you can do now
    lines.append("\n## What works at your current setup")
    lines.append("")
    if rep.graph_exists:
        lines.append("With `graph.json` present, these commands work now:")
        lines.append("```bash")
        lines.append("graphpowers blast [files]")
        lines.append("graphpowers pack \"task\" --file seed.py")
        lines.append("graphpowers who-uses \"NodeName\"")
        lines.append("graphpowers explain \"concept\"")
        lines.append("graphpowers guard --planned file.py")
        lines.append("graphpowers narrate")
        lines.append("graphpowers drift before.json after.json")
        lines.append("graphpowers parallel  # with JSON on stdin")
        lines.append("graphpowers snapshot")
        lines.append("```")
        if not rep.graphify_ok:
            lines.append("\nTo also build/update graphs and run semantic queries, "
                         "install graphify: `pip install graphify`")
    else:
        lines.append("No graph.json found. To get started:")
        lines.append("```bash")
        if not rep.graphify_ok:
            lines.append("pip install graphify        # install the graph builder")
        lines.append("graphify .                  # build the knowledge graph")
        lines.append("graphpowers freshness       # verify it worked")
        lines.append("graphpowers blast src/      # try your first blast radius")
        lines.append("```")

    return "\n".join(lines) + "\n"
