---
name: graph-first-brainstorming
description: Use when brainstorming a feature or change in a repo with a knowledge graph, before proposing any design - grounds requirement questions and design options in the actual architecture instead of assumptions about it
---

# Graph-First Brainstorming

## Overview

`superpowers:brainstorming` teases out what the user wants. This skill
makes sure the design conversation is about the codebase that exists,
not the one you imagine.

**Core principle:** Ask the graph before you ask the user — then ask the
user better questions.

## The Process

Follow `superpowers:brainstorming`; insert these steps:

### Before proposing anything

```bash
graphify query "how does <the area being changed> work today?"
```

Read the answer. Your first design questions to the user should reference
real node names: "Login currently flows through `SessionManager` →
`TokenStore`. Should the new flow reuse `TokenStore` or is that what
you're trying to replace?"

### While weighing options

For each candidate design, sanity-check it against the map:

- Which communities does it touch? (`graphify query`, look at community
  labels) One community = contained; three = are you sure?
- Does it route new traffic through an existing god node? That's either
  correct reuse or added load on the most fragile point — name it and
  let the user decide.
- Is there an existing node that already does 80% of this?
  (`graphify explain "<CandidateNode>"`) Propose extending before building.

### In the design document

Cite the graph: "This design touches communities 2 and 5; it adds one
edge to god node `EventBus` (currently degree 34)." Concrete numbers make
the review of the design honest.

## Red Flags — STOP

- Proposing a design without having queried the area first
- "We'll add a new module for this" when the graph shows one exists
- Design questions the graph could have answered ("what calls X?")
