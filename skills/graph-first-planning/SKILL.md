---
name: graph-first-planning
description: Use when writing an implementation plan in a repo with a knowledge graph, after brainstorming and before touching code - every task gets a graph-verified file list and a blast radius so the plan is scoped by evidence, not vibes
---

# Graph-First Planning

## Overview

A plan written from memory of the codebase names the wrong files, misses
callers, and scopes tasks by optimism. The graph already knows every
caller, importer, and dependency. Use it.

**Core principle:** Every task in the plan is scoped by blast radius, not
by hope.

This skill extends `superpowers:writing-plans`. Follow that skill's
structure; add the steps below.

## The Process

### 1. Verify the map first

```bash
python3 -m bridge freshness   # exit 2 = stale → graphify . --update
```

### 2. Locate the work on the map

For the feature area, before writing any task:

```bash
graphify query "how does <feature area> currently work?"
graphify explain "<KeyClass>"
```

If the query returns nothing relevant, the feature is genuinely new —
say so in the plan ("greenfield: no existing nodes").

### 3. Compute blast radius per task

For each task that modifies existing files:

```bash
python3 -m bridge blast path/to/file_a.py path/to/file_b.py --depth 2
```

Paste the risk line into the task. Then:

| Blast result | Plan consequence |
|---|---|
| Risk LOW, 1 community | task is safely independent → candidate for parallel dispatch |
| Risk MEDIUM or 2+ communities | add explicit regression-test step for the other communities |
| Risk HIGH (god node in range) | task must include tests for the god node BEFORE modifying it, and cannot be delegated without a context pack |
| Unmatched files listed | graph is stale or the file is new — verify manually |

### 4. Order tasks by the graph

Two tasks whose blast radii overlap share state → they are sequential,
not parallel. Two tasks in disjoint communities with disjoint radii →
safe for `superpowers:dispatching-parallel-agents`.

### 5. Snapshot before implementation begins

```bash
python3 -m bridge snapshot
```

Record the snapshot filename in the plan header. The
`architecture-drift-check` skill diffs against it when the branch is done.

## Plan task template addition

```markdown
### Task N: <name>
Files: <graph-verified list, from blast seeds>
Blast radius: <risk level, N nodes, communities touched>
God nodes in range: <names or "none">
Parallel-safe: <yes/no, based on radius overlap>
```

## Red Flags — STOP

- Writing "modify the auth module" without having run `graphify query`
  on auth first
- A task file list you produced from memory instead of from the graph
- Marking tasks parallel-safe without comparing blast radii
- Planning against a graph you know is stale
