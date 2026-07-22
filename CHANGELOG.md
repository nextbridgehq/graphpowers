# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1](https://github.com/nextbridgehq/graphpowers/compare/v0.1.0...v0.1.1) (2026-07-22)


### Bug Fixes

* detect newly created untracked files during freshness checks ([8238845](https://github.com/nextbridgehq/graphpowers/commit/82388453343b07e85b891340875e1dd8b437191e))
* display impact degree, not raw degree, for new god nodes in drift ([964c54c](https://github.com/nextbridgehq/graphpowers/commit/964c54cb9dc6c5bb289f69be0d65543dd4a991f1))
* god-node degree, who-uses paths, hook exec bit, and freshness gaps (0.2.0) ([7113dbf](https://github.com/nextbridgehq/graphpowers/commit/7113dbf867fc223a698071478a23cf7a77f00d83))
* rank god nodes by impact-only degree, not raw edge count ([293ffe1](https://github.com/nextbridgehq/graphpowers/commit/293ffe1b180efb82f77aeb8bed73ba9a404066f9))
* resolve JSON syntax error in plugin.json ([4e4ef62](https://github.com/nextbridgehq/graphpowers/commit/4e4ef620373fd9017461361e7ef186c05bd4dabd))
* resolve who-uses file-path lookups via the graph file index ([5ce3f83](https://github.com/nextbridgehq/graphpowers/commit/5ce3f832c381fad6cb7581d6ff8f6da57d85aa15))
* track hooks/session-start as executable in git ([36be54e](https://github.com/nextbridgehq/graphpowers/commit/36be54eb8fa7bc2e991cceedfaf9266858559cdd))


### Documentation

* add AGENTS.md/CLAUDE.md/GEMINI.md, log drift.py fix in changelog ([caf1e68](https://github.com/nextbridgehq/graphpowers/commit/caf1e6851ca24b655f2b738d506b5b00047b615f))
* add local-commits-only policy to AGENTS.md, reflect in pointers ([c305d21](https://github.com/nextbridgehq/graphpowers/commit/c305d21efc765cef25e082c62b9637e1c7be3c4f))
* adopt Keep a Changelog format, update README and third-party notices ([46318ec](https://github.com/nextbridgehq/graphpowers/commit/46318ecd7e834d48fafeaa02f5ea01abb7cddde0))
* log new AGENTS.md/CLAUDE.md/GEMINI.md in the 0.2.0 changelog entry ([1476b09](https://github.com/nextbridgehq/graphpowers/commit/1476b0989584f9f1f08ba993b0886a9966a10154))
* widen schema compatibility table to 0.2.x, tidy README attribution ([13c5772](https://github.com/nextbridgehq/graphpowers/commit/13c5772801e2ea95a9a9c7e38de1ca4a62996304))

## [Unreleased]

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
