---
name: graph-first-debugging
description: Use when debugging any bug or test failure in a repo with a knowledge graph, during the root-cause phase - trace call paths and dependency chains through the graph instead of grepping, and bound the regression search with blast radius
---

# Graph-First Debugging

## Overview

`superpowers:systematic-debugging` Phase 1 says "understand the system
before proposing fixes." In a graphed repo, understanding is a query,
not an archaeology dig.

**Core principle:** The graph turns "where could this possibly come
from?" into an enumerable list.

This skill slots into systematic-debugging Phase 1 (root cause). It does
not replace the four-phase discipline — no fixes until the cause is proven.

## The Process

### 1. Locate the symptom on the map

```bash
graphify query "what is <FailingThing> and what does it depend on?"
graphify explain "<FailingFunction>"
```

### 2. Trace the path between symptom and suspect

You saw the error in A, you suspect the cause is near B:

```bash
graphify path "<SymptomNode>" "<SuspectNode>"
```

Every node on that path is a checkpoint. Add a log line or assertion at
each and bisect — this is the graph version of systematic-debugging's
"binary search the failure."

### 3. Enumerate what a recent change could have broken

If the bug appeared after a change:

```bash
python3 -m bridge blast $(git diff --name-only HEAD~1) --depth 2
```

The hit list IS your suspect list, ordered by depth. Depth-1 hits first.
If the failing code is NOT in the blast radius, the recent change is
probably innocent — widen to `--depth 3` once before abandoning the
hypothesis.

### 4. Check the confidence labels

Edges marked `AMBIGUOUS` in query output are guesses by the extractor.
Never build a root-cause theory on an AMBIGUOUS edge without opening the
source and confirming it.

## Red Flags — STOP

- Grepping the repo for a function name the graph could locate instantly
- Proposing a fix for a node outside the blast radius of the change that
  triggered the bug, without explaining why the radius missed it
- Treating an AMBIGUOUS edge as fact
