# CI drift gate — rollout checklist

Goal: get from "workflow file copied" to "team trusts the signal" without
a single false red blocking anyone.

## Phase 0 — Local dry run (before touching CI)

- [ ] `pip install graphify` works on a clean machine/venv (same Python
      minor version CI will use)
- [ ] `graphify . --no-viz` completes on your repo; note wall time
      (if it exceeds ~5 min, plan a cache or path-filter before Phase 2)
- [ ] `graphify-out/graph.json` exists and
      `PYTHONPATH=.graphpowers python3 -m bridge freshness` exits 0
- [ ] **Self-drift determinism test**: copy `graphify-out/graph.json` to `old.json`,
      run `graphify . --no-viz` again, and run `python3 -m bridge drift old.json graphify-out/graph.json`.
      Confirm the report is CLEAN (proves graph generation is deterministic).
- [ ] Simulate the gate by hand: make a small code change, rebuild, run
      `python3 -m bridge drift old.json graphify-out/graph.json` again —
      confirm the report flags the change and reads sensibly.

## Phase 1 — Wire it up (warn mode)

- [ ] Vendor the plugin at `.graphpowers/` (or set `GRAPHPOWERS_DIR`)
- [ ] Copy `ci/graphpowers-drift.yml` to `.github/workflows/`
- [ ] Confirm `GATE_MODE: warn` (it ships that way — leave it)
- [ ] Check repo settings: Actions enabled, workflow permissions allow
      `pull-requests: write` (org policies often restrict this)
- [ ] Add `graphify-out/` to `.gitignore` if not already

## Phase 2 — The three test PRs

Open these against a scratch branch, in order:

- [ ] **PR A — no-op**: change a comment or README line.
      Expect: workflow green, drift comment says CLEAN, exit 0.
      This proves the plumbing (checkout, worktree, comment posting).
- [ ] **PR B — benign change**: add one small function called from one
      place. Expect: CLEAN or a small "Added" section, still green.
      This proves normal work won't be nagged.
- [ ] **PR C — deliberate drift**: add a module that imports from two
      unrelated areas (cross-community edge) or wire many callers into
      one helper (god-node spike).
      Expect: REVIEW NEEDED verdict, exit 2, workflow still green
      (warn mode), sticky comment shows the specific findings.
      This proves the detector actually detects.

## Phase 3 — Tune before blocking

- [ ] Push a second commit to PR C — confirm the comment **updates in
      place** rather than stacking duplicates
- [ ] Check base-graph build time on your largest recent PR; if slow,
      add `paths-ignore` for docs-only PRs or cache the base graph
      keyed on base SHA
- [ ] Run the gate in warn mode on ~10 real PRs; count false flags.
      A "false flag" = drift reported that reviewers agree was fine
      AND uninteresting. Target: under 1 in 5 before blocking.
- [ ] Agree as a team what a REVIEW NEEDED verdict requires: a sentence
      of justification in the PR description, not necessarily a code
      change

## Phase 4 — Flip to block (optional)

- [ ] Set `GATE_MODE: block`
- [ ] Add the job to branch protection required checks
- [ ] Document the escape hatch: a maintainer can merge with admin
      override when drift is intentional and explained
- [ ] Revisit after two weeks: if people are overriding routinely, go
      back to warn — a gate everyone bypasses is worse than no gate

## Known sharp edges

- **First PR after adopting graphify**: the base branch has no history
  of graphs; the workflow builds it fresh in a worktree, so this is
  fine — but that PR's runtime is 2× a normal one.
- **Monorepos**: build time scales with repo size; scope graphify to
  the affected package or use path filters.
- **Force-pushed PRs**: `fetch-depth: 0` handles this, but if you
  shallow the clone to save time, the base worktree step will fail.
- **Comment size**: reports are truncated at 60k chars; a report that
  big means the PR itself is too big.
