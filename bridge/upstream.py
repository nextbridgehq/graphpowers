"""Upstream contract checks: do our references still exist upstream?

Graphpowers contains no upstream code, so "staying up to date" means
verifying the contracts we depend on:

1. Every ``superpowers:<skill>`` referenced in our SKILL.md files still
   exists in the Superpowers repo.
2. Every ``graphify`` subcommand/flag our skills tell agents to run is
   still present in ``graphify --help`` output.
3. The Superpowers session-start hook still uses the output convention
   our own hook mirrors.

Run locally or in CI (see ci/upstream-watch.yml). Exit-code contract:
0 = all contracts hold, 2 = a contract broke (actionable report printed),
1 = checker itself couldn't run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SKILL_REF = re.compile(r"superpowers:([a-z0-9][a-z0-9-]*)")
# graphify invocations anywhere (for flag collection), e.g. prose mentions
GRAPHIFY_CALL = re.compile(r"\bgraphify\s+([^\n`|)]*)")
# subcommand extraction only from command position: line start (allowing
# whitespace/backtick/$/> prefixes), so prose like "keep graphify installable"
# and comments ("# graphify installable in CI") don't produce fake subcommands
GRAPHIFY_CMD_LINE = re.compile(r"(?m)^[ \t`$>]*graphify\s+([^\n`|)]*)")
FLAG = re.compile(r"(--[a-z][a-z-]*)")
SUBCOMMAND = re.compile(r"^\s*([a-z][a-z-]+)")


@dataclass
class ContractReport:
    skill_refs: set[str] = field(default_factory=set)
    missing_skills: list[str] = field(default_factory=list)
    graphify_flags: set[str] = field(default_factory=set)
    graphify_subcommands: set[str] = field(default_factory=set)
    missing_graphify: list[str] = field(default_factory=list)
    hook_ok: bool | None = None  # None = not checked
    errors: list[str] = field(default_factory=list)

    @property
    def broken(self) -> bool:
        return bool(self.missing_skills or self.missing_graphify
                    or self.hook_ok is False)


_STOPWORDS = {"the", "a", "an", "may", "in", "there", "for", "and", "or",
              "is", "to", "with", "recently", "itself", "commands"}


def collect_references(skills_dir: str | Path,
                       extra_paths: list[str | Path] | None = None
                       ) -> ContractReport:
    """Scan our SKILL.md files (plus optional extra files/dirs, e.g. ci/)
    for upstream references."""
    rep = ContractReport()
    root = Path(skills_dir)
    files = sorted(root.glob("*/SKILL.md"))
    for p in (extra_paths or []):
        p = Path(p)
        if p.is_dir():
            files += sorted(x for x in p.rglob("*")
                            if x.suffix in {".md", ".yml", ".yaml"})
        elif p.is_file():
            files.append(p)
    if not files:
        rep.errors.append(f"no files to scan under {root}")
        return rep
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        rep.skill_refs.update(SKILL_REF.findall(text))
        for call in GRAPHIFY_CALL.findall(text):
            rep.graphify_flags.update(FLAG.findall(call))
        for call in GRAPHIFY_CMD_LINE.findall(text):
            m = SUBCOMMAND.match(call)
            if m and m.group(1) not in _STOPWORDS:
                rep.graphify_subcommands.add(m.group(1))
    return rep


def check_superpowers(rep: ContractReport,
                      superpowers_dir: str | Path) -> None:
    """Verify each referenced skill exists as skills/<name>/SKILL.md."""
    sp = Path(superpowers_dir)
    skills_root = sp / "skills" if (sp / "skills").is_dir() else sp
    for name in sorted(rep.skill_refs):
        if not (skills_root / name / "SKILL.md").is_file():
            rep.missing_skills.append(name)

    hook = sp / "hooks" / "session-start"
    if hook.is_file():
        text = hook.read_text(encoding="utf-8", errors="replace")
        rep.hook_ok = ("additionalContext" in text
                       or "additional_context" in text)
    # if the hook file moved, that's a contract question too:
    elif (sp / "hooks").is_dir():
        rep.hook_ok = False


def check_graphify_help(rep: ContractReport, help_text: str) -> None:
    """Verify flags/subcommands we use appear in `graphify --help` output."""
    for flag in sorted(rep.graphify_flags):
        if flag not in help_text:
            rep.missing_graphify.append(flag)
    for sub in sorted(rep.graphify_subcommands):
        if not re.search(rf"\b{re.escape(sub)}\b", help_text):
            rep.missing_graphify.append(sub)


def render(rep: ContractReport) -> str:
    lines = ["# Upstream contract check", ""]
    lines.append(f"Referenced superpowers skills: "
                 f"{', '.join(sorted(rep.skill_refs)) or '(none)'}")
    lines.append(f"Graphify usage: subcommands "
                 f"{sorted(rep.graphify_subcommands)}, flags "
                 f"{sorted(rep.graphify_flags)}")
    if rep.hook_ok is not None:
        lines.append(f"Superpowers hook convention: "
                     f"{'OK' if rep.hook_ok else 'CHANGED'}")
    if rep.errors:
        lines.append("\n## Checker errors")
        lines += [f"- {e}" for e in rep.errors]
    if rep.missing_skills:
        lines.append("\n## BROKEN: skills referenced but missing upstream")
        lines += [f"- superpowers:{s} — update or remove the reference "
                  f"in our SKILL.md files" for s in rep.missing_skills]
    if rep.missing_graphify:
        lines.append("\n## BROKEN: graphify CLI usage not in --help")
        lines += [f"- `{g}` — graphify may have renamed/removed it; "
                  f"update our skills and CI" for g in rep.missing_graphify]
    if rep.hook_ok is False:
        lines.append("\n## BROKEN: superpowers hook output convention changed"
                     "\n- review hooks/session-start against upstream")
    lines.append("\n**Verdict: " + ("BROKEN" if rep.broken else "OK") + "**")
    return "\n".join(lines) + "\n"


def run_check(skills_dir: str | Path,
              superpowers_dir: str | Path | None = None,
              graphify_help_file: str | Path | None = None,
              extra_paths: list[str | Path] | None = None) -> ContractReport:
    rep = collect_references(skills_dir, extra_paths=extra_paths)
    if superpowers_dir:
        check_superpowers(rep, superpowers_dir)
    if graphify_help_file:
        try:
            help_text = Path(graphify_help_file).read_text(encoding="utf-8",
                                                           errors="replace")
            check_graphify_help(rep, help_text)
        except OSError as e:
            rep.errors.append(f"could not read graphify help: {e}")
    return rep
