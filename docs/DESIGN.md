# Design

Why Graphpowers is shaped the way it is. Read this before proposing
structural changes.

## Goals

1. Make every phase of an agent development workflow consult the
   codebase knowledge graph — planning, dispatch, debugging, review,
   completion.
2. Turn graph data into *decisions*, not just information: risk levels,
   parallel-safety flags, gate exit codes.
3. Stay installable in seconds and runnable with nothing but Python.

## Non-goals

- **Not a graph engine.** Graphpowers never parses source code or builds
  graphs. That is Graphify's job; duplicating it would create a worse
  second implementation and a maintenance treadmill.
- **Not a workflow methodology.** The brainstorm/plan/TDD/review loop
  belongs to Superpowers. Graphpowers skills extend those skills by
  reference; they do not restate or replace them.
- **Not a general graph toolkit.** `graphio.Graph` implements exactly
  what the engines need (adjacency, degree, file index, BFS support) —
  not a networkx substitute.

## Core principles

**The graph file is the contract, not the library.** The bridge reads
`graph.json` and never imports graphify. This keeps the two projects
independently upgradable, lets the bridge run where graphify isn't
installed (CI comment jobs, hooks), and creates the provider seam.
The cost: schema changes upstream can break us — which is
why `graphio.validate_node_link` fails loudly on any structural mismatch
instead of letting blast/pack/drift misbehave quietly.

**Zero dependencies, on purpose.** Superpowers works because installing
it can't fail. The bridge inherits that: stdlib only, no venv required,
`PYTHONPATH=… python3 -m bridge` works with zero setup. Anything that
needs a dependency belongs in graphify, not here.

**Exit codes are the API.** Every command returns 0 (fine), 1 (error),
or 2 (needs attention: stale, drifted, high-risk). Hooks, CI, and shell
scripts branch on this without parsing prose. Markdown output is for
humans and agents; exit codes are for automation. Changing an exit-code
meaning is a breaking change.

**Honesty inherits.** Graphify labels edge confidence
(EXTRACTED/INFERRED/AMBIGUOUS). The bridge preserves the labels and the
skills enforce the discipline: no root-cause theory or design decision
rests on an AMBIGUOUS edge without source verification.

**Skills decide, code computes.** The Python bridge never tells the
agent what to do; it produces facts (radius, freshness, drift). The
skills own the judgment ("HIGH risk → tests before modification"). This
split keeps the code testable and the methodology editable in markdown.

## Extension strategy

- **Stable surface** (safe to build on): the CLI commands and their
  exit-code contract; the markdown report shapes; `graphio.Graph`'s
  public methods; the SKILL.md frontmatter format.
- **Internal** (may change without notice): scoring weights in
  context_pack, god-node thresholds, BFS internals, private `_` members.
- **Adding a graph provider**: implement a loader that returns
  `graphio.Graph` (e.g. `Graph.from_neo4j(...)`). Engines need no
  changes. We restructure into a providers/ package when the second
  real provider lands — not before.
- **Adding a skill**: follow the Superpowers skill format; extend an
  existing Superpowers or Graphpowers skill by reference; include a
  Red Flags section; keep commands copy-pasteable.

## Compatibility

The bridge understands networkx node-link JSON (`nodes` +
`links`/`edges`, nodes carrying `id`/`label`/`source_file`/
`source_location`/`community`, edges carrying `source`/`target`/
`relation`/`confidence`) as exported by graphify. Structure is validated
on every load; unsupported formats fail with a versioned error message
rather than wrong answers. When graphify's export schema changes, bump
`SCHEMA_VERSION` and this table:

| graphpowers | graph schema | validated against |
|---|---|---|
| 0.1.x | node-link-v1 | graphify test fixtures, July 2026 |
