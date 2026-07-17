---
name: keeping-the-graph-fresh
description: Use after merging a branch, completing implementation work, or whenever the freshness check reports stale - updates the knowledge graph so every later skill works from the truth
---

# Keeping the Graph Fresh

## Overview

Every graphpowers skill is only as good as the map. A stale graph gives
confident wrong answers — worse than no graph.

**Core principle:** The graph updates when the code does. No exceptions.

## When to update

| Moment | Action |
|---|---|
| Freshness check exits 2 | `graphify . --update` before continuing |
| Branch merged (`finishing-a-development-branch`) | `graphify . --update`, then delete old snapshots |
| Long session, many files changed | update at natural pauses, not mid-task |
| Working in a repo daily | suggest `graphify . --watch` once; don't nag |

## The Commands

```bash
python3 -m bridge freshness        # exit 0 fresh, 2 stale (lists files)
graphify . --update                # incremental: only changed files re-extracted
python3 -m bridge snapshot         # before starting the NEXT branch
```

Incremental update is cheap — it re-extracts only what changed. There is
no excuse for planning against a stale map to "save time."

## Housekeeping

Snapshots accumulate (`graphify-out/graph.snapshot-*.json`). After a
successful drift check + merge, keep the latest one and delete the rest.

## Red Flags — STOP

- Continuing to plan/review after freshness exited 2
- Running a full rebuild when `--update` would do
- Updating the graph mid-task and confusing yourself about what "before" means — finish the task, then update
