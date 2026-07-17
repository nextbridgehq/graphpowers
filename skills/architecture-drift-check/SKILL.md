---
name: architecture-drift-check
description: Use when finishing a development branch, after tests pass and before merge - rebuilds the graph and diffs it against the pre-implementation snapshot to catch coupling creep, accidental god nodes, and orphaned code that line-by-line review misses
---

# Architecture Drift Check

## Overview

Tests prove the code does what the plan said. Nothing proves the code's
*shape* stayed sane. A branch can pass every test while quietly turning a
helper into a god node, welding two independent communities together, or
stranding dead code.

**Core principle:** Review the shape of the change, not just its lines.

This slots into `superpowers:finishing-a-development-branch`, after
`superpowers:verification-before-completion` passes and before merge.

## The Process

### 1. You need a "before" snapshot

`graph-first-planning` step 5 created one
(`graphify-out/graph.snapshot-*.json`). If it didn't exist, you can
still snapshot the main branch: check out main in a worktree, run
graphify there, and use that graph.json as "before."

### 2. Rebuild and diff

```bash
graphify . --update
python3 -m bridge drift graphify-out/graph.snapshot-<timestamp>.json \
                         graphify-out/graph.json
```

Exit code 0 = clean. Exit code 2 = the report flagged something.

### 3. Read the verdict like a reviewer

| Finding | Question to answer before merge |
|---|---|
| New god node | Was this centralization in the plan? If not, is it justified — and does it now have its own tests and docs? |
| New cross-community edge | Did the plan intend to couple these modules? Accidental coupling is tomorrow's refactoring debt. |
| Orphaned nodes | Refactor leftovers. Delete them now — dead code never gets cheaper to remove. |

### 4. Record the outcome

Paste the drift report (or "drift: clean") into the branch's final
summary / PR description. Future archaeologists will thank you.

## Red Flags — STOP

- Merging with a REVIEW NEEDED verdict you haven't explained
- "The drift is fine, it's just refactoring" — refactoring is exactly
  when drift matters most
- Skipping the check because "the change was small" — small diffs cause
  disproportionate drift precisely because nobody looks
