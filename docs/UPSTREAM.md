# Staying current with upstream

Graphpowers vendors no Graphify or Superpowers code, so "integrating
their updates" means verifying that five contracts still hold:

1. Graphify's graph.json schema (guarded at runtime by
   `graphio.validate_node_link`)
2. The Graphify CLI surface our skills invoke (`query`, `path`,
   `explain`, `--update`, `--watch`, `--no-viz`)
3. The Superpowers skill names our skills extend by reference
4. The Superpowers hook output convention our hook mirrors
5. The plugin manifest format

## Tier 1 - Weekly canary (automated)

`ci/upstream-watch.yml` (copy to `.github/workflows/` when publishing):
installs the LATEST graphify, builds a real graph on a fixture project,
runs the test suite plus every bridge command against that graph, clones
latest Superpowers, and runs `upstream-check`. Any failure opens or
updates a GitHub issue labeled `upstream-watch`.

Run the contract check locally any time:

    python3 -m bridge upstream-check \
      --superpowers /path/to/superpowers \
      --graphify-help <(graphify --help) \
      --also ci --also docs

Exit codes: 0 contracts hold, 2 a contract broke, 1 checker error.

## Tier 2 - Pinned versions + update PRs

Pin graphify in CI workflows. Enable Renovate/Dependabot; each upstream
release becomes a PR bumping the pin, and the canary steps run on that
PR. Green -> merge and update the compatibility table in docs/DESIGN.md.
Red -> the PR itself documents what broke and against which version.

## Tier 3 - Human review of semantics

Watch both repos' releases (GitHub Watch -> Releases). Automated checks
catch structural breakage; they cannot catch semantic drift - e.g.
Superpowers rewording a skill so our extensions give contradictory
guidance, or Graphify redefining a confidence label. Skim each upstream
changelog; if a referenced skill's guidance changed materially, update
the corresponding graphpowers skill in the same PR that bumps the pin.

## What we deliberately do NOT do

- No git submodules pointing at upstream
- No vendored upstream trees with auto-merge bots
- No automatic adoption of unreviewed upstream code

All three reintroduce the monolith problem this architecture avoids,
and auto-merging unreviewed code is a supply-chain risk.
