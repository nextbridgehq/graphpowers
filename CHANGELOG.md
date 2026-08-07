# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Gemini CLI extension support: install with `gemini extensions install`,
  sharing the same skills, session hook, and bridge as the Claude Code plugin.
- This repo's own test suite now runs in CI on every push and pull
  request.

### Changed

- The session hook now also fires on `compact`, not just session start/resume
  — harmless since it only reads state.
- Renamed 4 skills to a consistent `graph-` prefix: `architecture-drift-check`
  → `graph-drift-check`, `component-blast-radius` →
  `graph-component-blast-radius`, `catching-design-system-bypasses` →
  `graph-design-system-bypass-check`, `keeping-the-graph-fresh` →
  `graph-freshness-check`.

### Fixed

- Repaired invalid JSON in the Claude Code plugin manifest that could break
  plugin installation.

## [0.2.0] - 2026-07-22

### Added
- `AGENTS.md` — shared conventions for AI coding agents working in this repo (changelog format, commit conventions, release-please-owned version files, graph relation semantics, testing conventions, and more)
- `CLAUDE.md` and `GEMINI.md` — tool-specific entry points pointing to `AGENTS.md`

### Fixed
- God nodes now ranked by impact-only degree, not raw edge count — structural edges like `contains` no longer inflate a node into a false god node
- `who-uses` now resolves file-path lookups via the graph file index, not just node labels/ids
- `hooks/session-start` tracked as executable in git (was `100644` despite being executable locally, which a fresh clone would not preserve)
- Freshness checks now detect newly created untracked files instead of reporting the graph as fresh
- `drift` now displays impact degree (not raw edge count) for new god nodes, so the printed before/after numbers match what actually triggered the flag

## [0.1.0] - 2026-07-17

### Added
- Initial release

[Unreleased]: https://github.com/nextbridgehq/graphpowers/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/nextbridgehq/graphpowers/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nextbridgehq/graphpowers/releases/tag/v0.1.0
