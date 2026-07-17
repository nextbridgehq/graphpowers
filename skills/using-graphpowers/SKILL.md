---
name: using-graphpowers
description: Use when starting any conversation in a repo that has (or should have) a graphify-out/ knowledge graph - establishes that every Superpowers process step consults the graph before touching files
---

# Using Graphpowers

## Overview

Superpowers tells you **how** to work. Graphify tells you **what you're
working on.** Graphpowers wires them together: every process step consults
the knowledge graph before it consults raw files.

**Core principle:** Never explore blind when a map exists. Never trust a
stale map.

## The Rule

At the start of any coding task in a repo:

1. Check for the map: does `graphify-out/graph.json` exist?
   - **Yes** → check freshness: `python3 -m bridge freshness`
     - Fresh → use it everywhere below.
     - Stale (exit code 2) → run `graphify . --update` first. Planning or
       reviewing against a stale graph is planning against a lie.
   - **No** → offer to build one (`graphify .`). If the user declines,
     proceed with vanilla Superpowers; do not nag again this session.
2. Announce "Using graphpowers: graph is fresh/stale/absent" once, then
   get on with the work.

## Where the graph plugs into the Superpowers loop

| Superpowers phase | Graphpowers skill | What the graph adds |
|---|---|---|
| brainstorming | graph-first-brainstorming | design grounded in actual architecture, not guesses |
| writing-plans | graph-first-planning | per-task blast radius, correct file lists |
| subagent dispatch | graph-context-packs | token-budgeted briefing instead of blind re-discovery |
| systematic-debugging | graph-first-debugging | trace call paths instead of grepping |
| code review | graph-impact-review | reviewer checklist from blast radius + god nodes |
| verification / finishing branch | architecture-drift-check, keeping-the-graph-fresh | catch coupling creep, update the map |

## Two tools, two jobs

- `graphify query/path/explain` — semantic questions ("how does auth work?")
- `python3 -m bridge freshness/blast/pack/drift/snapshot` — process glue
  (is the map current? what does this change touch? brief this subagent)

Use graphify for understanding. Use the bridge for workflow decisions.
