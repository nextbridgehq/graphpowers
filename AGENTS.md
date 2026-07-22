# Agent Instructions

Shared conventions for AI coding agents (Claude Code, Codex, Gemini, etc.)
working in this repository. Tool-specific entry points (`CLAUDE.md`,
`GEMINI.md`) point back here — this file is the source of truth.

## Changelog conventions

When updating `CHANGELOG.md`:

- Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
  Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
- New, unreleased work goes under `## [Unreleased]` first. Only move it
  under a dated `## [X.Y.Z] - YYYY-MM-DD` section once a version is
  actually cut/tagged.
- Use only the categories that apply, in this order: `### Added`,
  `### Changed`, `### Deprecated`, `### Removed`, `### Fixed`,
  `### Security`.
- Entries are short, user-facing bullet points describing the effect of
  a change — no commit hashes, PR numbers, or internal implementation
  detail.
- Keep the comparison links at the bottom of the file in sync:
  ```
  [Unreleased]: https://github.com/nextbridgehq/graphpowers/compare/vX.Y.Z...HEAD
  [X.Y.Z]: https://github.com/nextbridgehq/graphpowers/compare/vPREV...vX.Y.Z
  ```
- This repo's `release-please` workflow generates its own changelog
  format on release PRs. When editing `CHANGELOG.md` by hand, use the
  format above rather than release-please's default style.

## Commit conventions

- Use [Conventional Commits](https://www.conventionalcommits.org/)
  (`fix:`, `feat:`, `chore:`, `docs:`, `test:`, ...). `release-please`
  parses these directly to decide the next version bump and to
  auto-generate its own release-PR changelog — a non-conventional
  subject line breaks that.
- Do not add AI/bot co-author trailers (e.g. `Co-Authored-By: Claude`)
  or otherwise attribute commits to an AI tool. Commits should read as
  if written by the human maintainer.
- One logical fix per commit where practical — `release-please` and
  `CHANGELOG.md` both read at commit granularity, so bundling unrelated
  fixes into one commit produces a single muddy changelog line instead
  of several clean ones.

## Local commits only — never push or open a PR unannounced

- Committing to a local branch is normal working state — do it freely,
  without asking each time.
- **Never push to the remote (`origin`) and never open a pull request
  unless the current instruction explicitly and specifically asks for
  that push/PR.** Being told to "commit," "finish the fix," or "wrap up
  the branch" is not authorization to push — those mean commit locally
  and stop.
- This holds even once work is complete and tests pass. "Ready to
  push" and "push it" are different instructions; wait for the second
  one.
- Prior approval to push or open a PR does not carry forward to later
  work in the same session — a separate task needs a separate,
  explicit go-ahead.

## Version files are release-please-owned

`pyproject.toml`'s `version`, `.claude-plugin/plugin.json`'s `version`,
and `.release-please-manifest.json` are only ever updated by a
`release-please`-generated release PR (see `release-please-config.json`
for the `extra-files` wiring). Never hand-edit a version number in
these files directly — doing so drifts them out of sync with each
other and with what `release-please` computes from commit history.

## Graph relation semantics

`bridge/graphio.py`'s `IMPACT_RELATIONS` frozenset is the single source
of truth for which edge relations represent real dependency/impact
(`calls`, `imports`, `inherits`, ...) versus purely structural
organization (`contains`, `defines`, `declares`, `documents`). Every
piece of logic that reasons about impact, centrality, or god-node
status — `blast_radius`, `Graph.impact_degree`/`god_nodes`, `drift`,
`guard` — must filter through `IMPACT_RELATIONS`, never define its own
ad hoc relation list. A god-node/blast-risk bug already happened once
from a code path that counted structural edges as if they were impact
edges — don't reintroduce that class of bug elsewhere.

## Architecture principle: bridge computes facts, skills own judgment

`bridge/` (the Python CLI) should only ever report facts: risk level,
freshness, drift, degree, reachable nodes. Judgment calls like "HIGH
risk → require tests before merging" belong in the markdown skill
files under `skills/`, not in `bridge/` code. Keep new logic on the
correct side of that line.

## Testing conventions

- All bridge tests live in the single file `tests/test_bridge.py` as
  flat `pytest` functions — no test classes, no `tests/unit/` or
  `tests/integration/` subfolder split.
- Reuse the module-level `FIXTURE` dict and `graph()` helper for
  graph-based tests; build a small, purpose-built fixture inline only
  when the shared one can't demonstrate the behavior (see
  `test_god_nodes_ignore_structural_edges` for the pattern).
- Use `tmp_path` for anything that touches the filesystem or git (e.g.
  freshness checks) — never assume a git repo exists at the real repo
  root during a test.
- Run `pytest tests/` before considering any `bridge/` change
  complete. A drop in the passing-test count versus the baseline on
  `main` is a hard stop, not a detail to mention in passing.

## Zero-dependency constraint

`bridge/` intentionally has zero runtime dependencies (stdlib only —
see `pyproject.toml`'s `dependencies = []`) and supports Python 3.9+.
Don't add a third-party import to `bridge/`, and don't use syntax that
requires Python 3.10+.

## CLI exit-code contract

Every `bridge` subcommand follows: `0` = ok/clean/fresh, `1` = error
(missing file, bad input, node not found), `2` = needs attention (stale
graph, drift detected, high risk, scope creep, conflicts). Any new
subcommand must return codes that fit this contract — see the
"Exit Code Contract" section of `README.md` for the full table.

## CI templates vs this repo's CI

Files under `ci/` (e.g. `graphpowers-drift.yml`, `upstream-watch.yml`)
are workflow *templates* this plugin ships for consumer repositories
to adopt — they do not run as part of this repo's own CI. The only
workflow that actually executes here is `.github/workflows/release-please.yml`.
Don't "fix" `ci/` templates thinking they're broken pipelines for this
repo.

## Path matching

Internally, file paths are normalized to POSIX form and matched
exact-first-then-suffix (e.g. `auth.py` matches `src/auth.py`). See
`KNOWN_LIMITATIONS.md` → "Path Normalization" before changing anything
in `Graph.by_file` / `Graph.nodes_for_files` — the suffix-matching
heuristic is deliberate, not an oversight.
