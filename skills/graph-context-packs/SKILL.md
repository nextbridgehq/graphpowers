---
name: graph-context-packs
description: Use when dispatching a subagent to implement a task in a repo with a knowledge graph - generates a token-budgeted briefing of relevant nodes, relationships, and files so the subagent starts oriented instead of re-discovering the codebase
---

# Graph Context Packs

## Overview

Every subagent dispatched by `superpowers:subagent-driven-development`
starts with zero project knowledge and burns its first N tool calls
re-discovering what the orchestrator already knows. A context pack is a
pre-digested, graph-derived briefing: key nodes with file:line locations,
their relationships, and the files worth reading — trimmed to a token
budget.

**Core principle:** The orchestrator pays once to know the codebase; the
subagents inherit that knowledge for free.

## The Process

### 1. Generate the pack per task

```bash
python3 -m bridge pack "implement rate limiting on the login endpoint" \
    --file src/auth.py --budget 1200
```

- `--file` seeds it with the task's known files (from the plan's
  graph-verified list)
- `--budget` caps the pack size; 1200 tokens is right for most tasks,
  use 2000 for tasks touching a god node

### 2. Prepend the pack to the subagent prompt

```
<context-pack>
{output of the pack command}
</context-pack>

Your task: {task from the plan}
...
```

### 3. Tell the subagent how to go deeper

The pack already includes ground rules. Reinforce in the prompt:
"If you need context beyond the pack, run `graphify query` — do not
grep the whole repo."

## Quality checks before dispatch

- [ ] Pack mentions at least one node you know is central to the task
      (if not, your task description doesn't match the codebase's
      vocabulary — rephrase and regenerate)
- [ ] Every file in "Read these files first" actually exists
- [ ] Pack is under budget (the tool enforces this, but eyeball it)

## When NOT to use

- Greenfield tasks with no existing nodes — a pack of irrelevant matches
  is worse than none
- The graph is stale — fix that first (`keeping-the-graph-fresh`)
