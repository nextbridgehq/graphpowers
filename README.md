# Graphpowers

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Dependencies](https://img.shields.io/badge/dependencies-zero-success)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/nextbridgehq/graphpowers/blob/main/LICENSE)

Developed and open-sourced by [Nextbridge](https://www.nextbridge.com).

---

**Superpowers × Graphify.** One defines how your coding agent works - *how* to work (brainstorm → plan → TDD → review → verify). The other tells it *what* it's working on (a queryable knowledge graph of the codebase). Graphpowers wires them together so every process step consults the map.

> **Graphpowers is an orchestration layer.** It does not replace Graphify and does not replace Superpowers — it combines their capabilities through graph-aware workflows. Both remain independent upstream projects; see `THIRD_PARTY_NOTICES.md`.

---

## Table of Contents

- [Installation](#installation)
- [Prerequisites & Detection](#prerequisites--detection)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Known Limitations](#known-limitations)
- [What You Need](#what-you-need)
- [The Bridge CLI](#the-bridge-cli)
  - [doctor](#doctor--check-environment-and-dependencies)
  - [freshness](#freshness--is-the-graph-up-to-date)
  - [blast](#blast--blast-radius-of-changed-files)
  - [pack](#pack--context-pack-for-a-subagent)
  - [drift](#drift--architecture-diff-between-two-graph-snapshots)
  - [who-uses](#who-uses--reverse-dependency-lookup)
  - [explain](#explain--unified-concept-explanation)
  - [guard](#guard--scope-creep-detection-during-implementation)
  - [narrate](#narrate--community-narratives-onboarding)
  - [parallel](#parallel--parallel-safety-analysis)
  - [snapshot](#snapshot--save-a-timestamped-graph-copy)
  - [pack-feedback](#pack-feedback--context-pack-quality-feedback-loop)
  - [upstream-check](#upstream-check--verify-upstream-contracts-still-hold)
- [Skills Reference](#skills-reference)
- [CI Integration](#ci-integration)
- [Session Hook](#session-hook)
- [Pack Feedback & Self-Tuning](#pack-feedback--self-tuning)
- [Upstream Compatibility](#upstream-compatibility)
- [Exit Code Contract](#exit-code-contract)
- [Tests](#tests)
- [Design Principles](#design-principles)
- [Novel Features](#novel-features-not-in-either-parent)
- [Worked Example](#worked-example-full-branch-lifecycle)
- [Credits & Attribution](#credits--attribution)
- [License](#license)

## Installation
### Method 1: Claude Code Plugin (Tier 3)
```bash
# From the Claude Code plugin marketplace
/plugin marketplace add /graphpowers
/plugin install graphpowers
```
This installs skills, hooks, and the bridge together.

### Method 2: pip Install (Tier 1–2)
```bash
git clone https://github.com/nextbridgehq/graphpowers.git
cd graphpowers
pip install .
```
Now available as:

```bash
graphpowers freshness
graphpowers blast src/auth.py
```
### Method 3: Zero-Install via PYTHONPATH (Tier 1–2)
No install required at all. Clone the repo and point PYTHONPATH at it:

```bash
git clone https://github.com/nextbridgehq/graphpowers.git ~/.graphpowers
```
Run any command with:

```bash
PYTHONPATH=~/.graphpowers python3 -m bridge freshness
PYTHONPATH=~/.graphpowers python3 -m bridge blast src/auth.py
```
### Method 4: Vendor Into Your Project (Tier 1–2)
```bash
# Copy into your project as .graphpowers/
cp -r /path/to/graphpowers .graphpowers/
```
Run with:

```bash
PYTHONPATH=.graphpowers python3 -m bridge freshness
```
### Installing the Prerequisites
```bash
# Graphify (needed for Tier 2+)
pip install graphify

# Superpowers (needed for Tier 3)
# Follow instructions at https://github.com/obra/superpowers

# Verify
python3 --version          # 3.9+
graphify --help            # confirms graphify is installed
git --version              # any recent version
```

## Prerequisites & Detection

Graphpowers relies on other tools (like graphify and superpowers) but **never auto-installs anything**. If a tool is missing, the bridge commands will explain what's wrong and how to fix it.

Run `graphpowers doctor` to check your environment:

- **Python 3.9+**: Required to run the bridge.
- **Git**: Required for change detection (used by `freshness` and `blast`).
- **Graphify**: Required to build/update the knowledge graph.
- **Superpowers**: Handled by your agent (e.g. Claude Code); the doctor can't automatically detect it in all environments.

If `graph.json` is missing, you'll be instructed to run `graphify .`. The session hook (for AI agents) will gracefully degrade, informing the agent that the graph is missing so it can offer to build one, rather than crashing or hanging.


## Configuration
Graphpowers requires zero configuration files. It reads one artifact:

```text
your-project/
├── graphify-out/
│   └── graph.json          ← This is all graphpowers needs
├── graphpowers-data/       ← Auto-created for pack feedback (gitignore this)
│   └── pack-feedback.jsonl
└── .graphpowers/           ← Optional: vendored graphpowers plugin
```
### First-Time Setup for a Repository
```bash
cd your-project

# 1. Build the knowledge graph (requires graphify — Tier 2+)
graphify .
# Takes ~30 seconds for most repos. Creates graphify-out/graph.json.

# 2. Verify the graph exists and is fresh
graphpowers freshness
# Output: "Graph is FRESH (142 source files checked against graphify-out/graph.json)."

# 3. Add to .gitignore
echo "graphify-out/" >> .gitignore
echo "graphpowers-data/" >> .gitignore
```
### If You Don't Have Graphify
If someone else built the graph (CI, teammate), just make sure graphify-out/graph.json exists in your project root. All bridge commands work without graphify installed.

### Keeping the Graph Current (Tier 2+)
```bash
# After changing code:
graphify . --update          # Incremental: only re-extracts changed files

# For long sessions:
graphify . --watch           # Auto-updates on file save (background daemon)
```

## Quick Start

### 0. Check your setup (first time only)
```bash
graphpowers doctor
```

### 1. Check if the graph is fresh
```bash
graphpowers freshness
# Exit 0 = fresh, Exit 2 = stale (lists changed files)
```

### 2. See what a change will affect
```bash
graphpowers blast src/auth.py src/session.py
# Shows: Risk MEDIUM, 14 nodes reachable, 2 communities touched
```

### 3. Brief a subagent
```bash
graphpowers pack "add rate limiting to login" --file src/auth.py --budget 1200
# Outputs: token-budgeted context pack with key nodes, relationships, files to read
```

### 4. Understand a concept
```bash
graphpowers explain "SessionManager"
# Shows: what it is, what connects to it, blast radius, context pack — all in one
```

### 5. Check for architecture drift after a branch
```bash
graphpowers snapshot                    # Before implementation
# ... do work ...
graphify . --update                     # Rebuild (requires graphify)
graphpowers drift graphify-out/graph.snapshot-*.json graphify-out/graph.json
# Exit 0 = clean, Exit 2 = drift detected
```

### 6. Find who uses something before you change it
```bash
graphpowers who-uses "Button"
# Lists every node connected to Button, grouped by relationship type
```

### 7. Check if you've drifted from the plan mid-task
```bash
graphpowers guard --planned src/auth.py
# Uses git to detect touched files, compares against planned blast radius
```

## How It Works

```text
        SUPERPOWERS (process)          GRAPHIFY (knowledge)
  brainstorming ──────────────┐      ┌── graph.json (nodes/edges/communities)
  writing-plans ──────────────┤      ├── query / path / explain
  subagent dispatch ──────────┤  ⇄   ├── god nodes, confidence labels
  systematic-debugging ───────┤      ├── incremental --update, --watch
  code review ────────────────┤      └── MCP server
  verification / finish ──────┘
              │
              └──── GRAPHPOWERS BRIDGE (this plugin)
                    freshness · blast · pack · drift · guard
                    narrate · parallel · explain · who-uses
                    snapshot · pack-feedback · upstream-check
```
Superpowers defines the development methodology (brainstorm → plan → implement → review → verify).
Graphify builds and maintains a knowledge graph of your codebase.
Graphpowers is the bridge that makes every methodology step graph-aware — so agents plan against evidence, not assumptions.


## Architecture
```text
┌─────────────────────────────────────────────────────────┐
│                    SKILLS (Markdown)                    │
│  "What to do" — judgment, process, red flags            │
├─────────────────────────────────────────────────────────┤
│                  BRIDGE (Python, 0 deps)                │
│  "Compute facts" — blast, pack, drift, freshness        │
│  Reads graph.json directly, never imports graphify      │
├─────────────────────────────────────────────────────────┤
│                CONTRACT BOUNDARY                        │
│  graph.json (node-link-v1) — validated on every load    │
├─────────────────────────────────────────────────────────┤
│  GRAPHIFY (upstream)          SUPERPOWERS (upstream)    │
│  Builds the graph             Defines the process       │
└─────────────────────────────────────────────────────────┘
```
Key design decisions:

- The bridge reads graph.json directly — it never imports graphify
- Zero runtime dependencies (stdlib only) — can't fail to install
- Schema is validated on every load — fails loud, never gives silently wrong answers
- Exit codes are the API — automation doesn't need to parse prose
- Skills own judgment; Python computes facts — testable separation

## Known Limitations

Graphpowers relies on static analysis and makes explicit design trade-offs favoring speed, offline operation, and conservatism over perfect precision. Read the full details in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).


## What You Need
Graphpowers is designed so you don't need everything to get started. There are three tiers depending on how much of the system you want:

### Tier 1: Bridge Only (Minimal)
Use the bridge CLI commands against any existing graph.json.

| Requirement | Purpose |
| --- | --- |
| Python 3.9+ | Runs the bridge |
| A graph.json file | The graph to analyze (built by graphify, a teammate, or CI) |
#### What you can do:

blast, pack, drift, guard, narrate, parallel, explain, who-uses, snapshot
#### What you can't do:

Build/update the graph, semantic queries, structured agent workflow
### Tier 2: Bridge + Graphify (Full Technical Power)
Build your own graphs and run semantic queries alongside the bridge.

| Requirement | Purpose |
| --- | --- |
| Python 3.9+ | Runs the bridge |
| Graphify | Builds and updates the knowledge graph |
| Git | Change detection, freshness checks |
#### What you can do:

Everything in Tier 1
Build graphs (graphify .), update them (graphify . --update)
Run semantic queries (graphify query/path/explain)
Use freshness meaningfully
#### What you can't do:

Full structured agent methodology (brainstorm/plan/review loop)
### Tier 3: Bridge + Graphify + Superpowers (Full Experience)
The complete orchestrated AI development workflow.

| Requirement | Purpose |
| --- | --- |
| Python 3.9+ | Runs the bridge |
| Graphify | Builds and updates the knowledge graph |
| Superpowers | Development methodology (brainstorm → plan → TDD → review) |
| Git | Change detection, freshness checks |
| Claude Code (or compatible AI agent) | Executes the skills and follows the process |
#### What you can do:

Everything. The AI agent automatically consults the graph at every process step — brainstorming grounds designs in real architecture, plans carry blast radii, subagents get context packs, reviews follow risk-proportional checklists, and branches finish with drift checks.
### Which Tier Should I Start With?
| If you are... | Start with |
| --- | --- |
| Evaluating graphpowers or have a graph.json from CI | Tier 1 |
| A developer using graphify who wants better tooling | Tier 2 |
| Using Claude Code with superpowers and want graph-aware development | Tier 3 |
You can always upgrade tiers later — the bridge doesn't care how graph.json got there.


## The Bridge CLI

Every command follows the same pattern:
`graphpowers <command> [arguments] [--flags]`

*New flags documented:*
- `--explain-exit-code`: Global flag to append a human-readable explanation of the exit code.
- `--format json`: Available on `freshness`, `blast`, `drift`, and `guard`.

### doctor — Check environment and dependencies
```bash
graphpowers doctor
```
Checks if Python, Git, Graphify, and the graph itself are present. Detects version mismatches.

### freshness — Is the graph up to date?
```bash
graphpowers freshness [--root .] [--graph PATH]
```
Compares graph.json mtime against all source files. Reports which files changed since the graph was built.

| Exit Code | Meaning |
| --- | --- |
| 0 | Graph is fresh — safe to use |
| 2 | Graph is stale — lists changed files, run graphify . --update |
| 1 | Error (graph file not found) |
Example output (stale):

```text
Graph is STALE — 3 file(s) changed since it was built: src/auth.py, src/db.py, src/utils.py.
Run `graphify . --update` before planning or reviewing.
```
Watched file types:

.py, .js, .jsx, .ts, .tsx, .rb, .go, .rs, .java, .kt, .c, .h, .cpp, .hpp, .cs, .swift, .php, .scala, .sql, .sh, .bash, .r, .R, .md, .proto, .tf

Skipped directories:

.git, node_modules, graphify-out, __pycache__, .venv, venv, dist, build, .next, target

### blast — Blast radius of changed files
```bash
graphpowers blast [FILE ...] [--depth 2] [--graph PATH]
```
BFS traversal along impact relations from the given files. If no files are given, uses git diff automatically to find changed files.

**Traversal behavior:** Blast radius traverses impact relations
*bidirectionally* — if A calls B, changing either puts the other in range.
This is conservative by design: a safety tool should over-flag rather than
miss real impact. Relations like `contains` and `defines` are NOT traversed
(they're structural, not dependency edges).

| Exit Code | Meaning |
| --- | --- |
| 0 | Risk LOW or MEDIUM |
| 2 | Risk HIGH (god node in blast radius) |
Risk classification:

| Risk | Condition |
| --- | --- |
| HIGH | Any god node (top-10 by degree) is reachable |
| MEDIUM | >40 nodes reachable OR >3 communities touched |
| LOW | Everything else |
Impact relations traversed:

calls, indirect_call, references, imports, imports_from, re_exports, inherits, extends, implements, uses, mixes_in, embeds

Example:

```bash
graphpowers blast src/auth.py --depth 2
```
Output:

```text
# Blast radius

**Risk: MEDIUM** — 2 seed node(s), 14 reachable node(s), 2 communit(ies) touched.

| depth | node | via | location |
|---|---|---|---|
| 0 | auth.py | seed | src/auth.py |
| 0 | login() | seed | src/auth.py:L10 |
| 1 | query() | calls | src/db.py:L5 |
| 1 | utils.py | imports | src/utils.py |
```
### pack — Context pack for a subagent
```bash
graphpowers pack "task description" [--file F ...] [--budget 1200] [--graph PATH]
```
Generates a token-budgeted briefing for a subagent. Scores nodes by relevance to the task, includes their relationships and file locations, and auto-shrinks to fit within the budget.

Arguments:

| Argument | Description |
| --- | --- |
| "task description" | What the subagent will work on (used for relevance scoring) |
| --file | Seed files (nodes in these files get a score boost); repeatable |
| --budget | Max tokens for the pack (default: 1200; use 2000 for god-node tasks) |
Scoring algorithm:

Term overlap between task description and node labels (camelCase/snake_case split)
Seed file boost (--file paths get +3.0 by default)
Degree tiebreaker (central nodes rank slightly higher)
Hub penalty (learned: very central nodes often included but unused)
Community bonus (learned: same-community nodes are usually needed together)
Example:

```bash
graphpowers pack "fix login auth flow" --file src/auth.py --budget 1200
```
Output:

```text
# Context pack: fix login auth flow

Touches communit(ies): 0, 1.

## Key nodes
- **login()** — src/auth.py:L10
- **auth.py** — src/auth.py
- **query()** — src/db.py:L5

## Relationships
- `login()` —calls→ `query()`
- `login()` —imports→ `utils.py`

## Read these files first
- `src/auth.py`
- `src/db.py`

## Ground rules
- Trust EXTRACTED edges; verify AMBIGUOUS ones in source before relying on them.
- If a node you need is missing here, query the graph (`graphify query "..."`) instead of grepping blind.
```
### drift — Architecture diff between two graph snapshots
```bash
graphpowers drift BEFORE.json AFTER.json
```
Compares two graph snapshots and reports structural changes that line-by-line code review cannot see.

| Exit Code | Meaning |
| --- | --- |
| 0 | Clean — no architectural concerns |
| 2 | Review needed — new god nodes, cross-community coupling, or orphaned code |
What it detects:

| Finding | What it means |
| --- | --- |
| New god node | A node's degree spiked — it became load-bearing |
| Cross-community edge | Previously independent modules are now coupled |
| Orphaned node | A node lost all its edges — dead code candidate |
| Added/removed nodes | Context for the structural findings |
Example:

```bash
graphpowers drift graphify-out/graph.snapshot-20260705.json graphify-out/graph.json
```
Output:

```text
# Architecture drift report

**Verdict: REVIEW NEEDED ⚠️** — +1/-0 nodes, +5/-1 edges.

## New god nodes (centrality spiked)
- **MegaHub** — degree 0 → 5 (src/hub.py)

A node this central deserves its own tests and docs. Was this concentration intentional?

## New cross-community coupling
- `MegaHub` —uses→ `auth.py` (communities 0 ↔ 1)

These modules were previously independent. Confirm the coupling is deliberate.
```
### who-uses — Reverse dependency lookup
```bash
graphpowers who-uses "NodeLabel" [--graph PATH]
```
Finds all nodes connected to a named concept, grouped by relationship type. Essential before modifying any shared component.

| Exit Code | Meaning |
| --- | --- |
| 0 | Node found, consumers listed |
| 1 | No matching node |
Node matching: Exact match (case-insensitive) wins, then substring matches ordered by degree (most-connected first). Strips trailing () for function matching.

Example:

```bash
graphpowers who-uses "query"
```
Output:

```text
# Who uses `query()`

Node: src/db.py:L5 — degree 2, community 1

**2 connected node(s):**

## calls (1)
- login() — src/auth.py:L10

## contains (1)
- db.py — src/db.py
```
### explain — Unified concept explanation
```bash
graphpowers explain "term" [--budget 800] [--graph PATH]
```
One command that combines who-uses + blast + pack into a single view. Answers: what is it, what connects to it, what's at stake if you change it, and what context does a subagent need?

| Exit Code | Meaning |
| --- | --- |
| 0 | Node found and explained |
| 1 | No matching node |
Example:

```bash
graphpowers explain "login"
```
Output:

```text
# "login" in this codebase

## Graph says
- **login()** — src/auth.py:L10 (degree 3, community 0)

**Relationships:**
- `login()` —calls→ `query()`
- `login()` —imports→ `utils.py`
- `auth.py` —contains→ `login()`

## Blast radius if you touch it
**Risk: MEDIUM** — 4 node(s), 2 communit(ies)

## Context pack (for subagent)
[abbreviated pack content]
```
### guard — Scope creep detection during implementation
```bash
graphpowers guard --planned f1.py f2.py [--touched f1.py f2.py f3.py] [--depth 2] [--graph PATH]
```
Compares the blast radius of planned files against actually-touched files. Flags "surprise" nodes — things reachable from your actual changes that weren't reachable from the plan.

| Exit Code | Meaning |
| --- | --- |
| 0 | No scope creep — actual changes within planned radius |
| 2 | Scope creep detected — surprise nodes outside plan |
If --touched is omitted, uses git diff to detect touched files automatically.

Example:

```bash
graphpowers guard --planned src/auth.py --touched src/auth.py src/db.py
```
Output:

```text
# Implementation guard

**⚠️ Scope creep detected** — 2 surprise node(s) outside planned blast radius.

Planned radius: 4 node(s) from 1 file(s).
Actual radius: 6 node(s) from 2 file(s).

## Surprise nodes
- **db.py** — src/db.py
- **query()** — src/db.py:L5

**New communities entered:** 1

**Recommendation:** Scope creep into 1 new communit(ies). Split this task or update the plan before continuing.
```
### narrate — Community narratives (onboarding)
```bash
graphpowers narrate [--community ID] [--graph PATH]
```
Generates human-readable one-paragraph descriptions of each community in the graph. Deterministic, template-based output — no LLM needed.

| Exit Code | Meaning |
| --- | --- |
| 0 | Always (informational) |
How it works: For each community, identifies the hub node (highest degree), infers a domain name from file paths and labels, and generates a structural narrative describing what the community does and how it connects to others.

Example:

```bash
graphpowers narrate
```
Output:

```text
# Community narratives

**3 communit(ies)** in the graph.

## Community 0 — login() (2 nodes)

Community 0 is the **auth** subsystem, centered on **login()**. It contains 2 node(s) primarily in auth.py. Other communities reach it via calls.

**Key members:** `login()`, `auth.py`
**Files:** `src/auth.py`

## Community 1 — query() (2 nodes)

Community 1 is the **db** subsystem, centered on **query()**. It contains 2 node(s) primarily in db.py. Other communities reach it via calls.

**Key members:** `query()`, `db.py`
**Files:** `src/db.py`
```
### parallel — Parallel safety analysis
```bash
echo '' | graphpowers parallel [--depth 2] [--graph PATH]
```
Reads task specifications from stdin (JSON array), computes blast radius for each, finds pairwise overlaps, and produces a parallel execution plan.

| Exit Code | Meaning |
| --- | --- |
| 0 | All tasks can run in parallel (no conflicts) |
| 2 | Some tasks conflict (must be sequential) |
Algorithm:

Compute blast radius for each task
Check all pairwise overlaps (shared nodes = conflict)
Build a conflict graph
Greedy graph coloring → independent sets (parallel groups)
Input format (stdin):

```json
[
  {"id": "task-1", "files": ["src/auth.py"]},
  {"id": "task-2", "files": ["src/db.py"]},
  {"id": "task-3", "files": ["src/auth.py", "src/session.py"]}
]
```
Example (no conflicts):

```bash
echo '[{"id":"auth","files":["src/auth.py"]},{"id":"utils","files":["src/utils.py"]}]' | graphpowers parallel
```
Output:

```text
# Parallel safety analysis

**✅ All 2 tasks can run in parallel** — no blast radius overlaps detected.

## Execution groups (1)

Tasks within the same group can run in parallel. Groups must run sequentially.

**Group 1:** `auth`, `utils`
```
Example (with conflicts):

```text
# Parallel safety analysis

**⚠️ 1 conflict(s)** among 3 tasks — split into 2 sequential group(s).

## Execution groups (2)

**Group 1:** `task-1`, `task-2`
**Group 2:** `task-3`

## Conflicts

**`task-1` ↔ `task-3`** — 3 shared node(s)
  Communities: 0
  Nodes: `auth.py`, `login()`, `SessionManager`
```
### snapshot — Save a timestamped graph copy
```bash
graphpowers snapshot [--graph PATH] [--out PATH]
```
Copies graph.json with a timestamp. Used before implementation starts so drift can compare before vs. after.

| Exit Code | Meaning |
| --- | --- |
| 0 | Snapshot saved |
| 1 | No graph found |
Example:

```bash
graphpowers snapshot
# Output: Snapshot written: graphify-out/graph.snapshot-20260716-103000.json
```
### pack-feedback — Context pack quality feedback loop
Log whether context packs were sufficient, view quality statistics, and check current learned scoring weights.

```bash
# Log feedback after a subagent finishes
graphpowers pack-feedback log --task-id T1 --sufficient \
  --pack-node login --pack-node auth.py

graphpowers pack-feedback log --task-id T2 --insufficient \
  --extra-read src/missing.py --unused-node megahub \
  --pack-node login --pack-node auth.py --pack-node megahub

# View quality statistics
graphpowers pack-feedback stats [--data-dir PATH]

# View current learned scoring weights
graphpowers pack-feedback weights [--data-dir PATH]
```
| Subcommand | Exit Code | Meaning |
| --- | --- | --- |
| log | 0 | Feedback recorded (fire-and-forget) |
| stats | 0 | Statistics displayed |
| weights | 0 | Current weights displayed as JSON |
See Pack Feedback & Self-Tuning for the full explanation.

### upstream-check — Verify upstream contracts still hold
```bash
graphpowers upstream-check \
  --superpowers /path/to/superpowers \
  --graphify-help <(graphify --help) \
  [--also ci] [--also docs]
```
Scans your skills and CI files for references to upstream (Superpowers skill names, Graphify CLI flags), then verifies they still exist.

| Exit Code | Meaning |
| --- | --- |
| 0 | All contracts hold |
| 2 | A contract broke (skill missing, flag removed, hook changed) |
| 1 | Checker itself couldn't run |
## Skills Reference
Graphpowers includes 11 skills that extend the Superpowers methodology with graph awareness. Skills are markdown files in skills/ — they don't execute anything. They provide instructions for AI agents (Tier 3) or serve as documentation for humans (any tier).

### Core Workflow Skills
| Skill | Extends | When to Use | What It Adds |
| --- | --- | --- | --- |
| using-graphpowers | — | Session start | Establishes graph-first workflow; injected by session hook |
| graph-first-brainstorming | superpowers:brainstorming | Before proposing designs | Designs grounded in actual architecture via graphify query |
| graph-first-planning | superpowers:writing-plans | Writing implementation plans | Per-task blast radius, verified file lists, parallel-safety flags |
| graph-context-packs | superpowers:subagent-driven-development | Dispatching subagents | Token-budgeted briefings so subagents start oriented |
| graph-first-debugging | superpowers:systematic-debugging | Root-cause phase | Call-path tracing; change-blast suspect lists |
| graph-impact-review | superpowers:requesting-code-review | Code review | Reviewer checklist from blast radius + god nodes |
| architecture-drift-check | superpowers:finishing-a-development-branch | Finishing a branch | Diff before/after: coupling creep, new god nodes, orphans |
| keeping-the-graph-fresh | — | After merges, when stale | Never plan against a lie; update the map when the code changes |
### Specialized Skills
| Skill | When to Use | What It Adds |
| --- | --- | --- |
| component-blast-radius | Before modifying shared UI components | Enumerates every consumer of a component before you touch it |
| catching-design-system-bypasses | Frontend code review | Detects design-system bypasses via graph adoption patterns |
| graph-first-testing | Deciding test coverage priorities | Test type (integration/contract/unit/boundary) from graph position |
### How Skills Plug Into the Superpowers Loop
```text
┌─────────────────────────────────────────────────────────────────┐
│  SUPERPOWERS PHASE              GRAPHPOWERS SKILL               │
├─────────────────────────────────────────────────────────────────┤
│  brainstorming            →  graph-first-brainstorming          │
│  writing-plans            →  graph-first-planning               │
│  subagent dispatch        →  graph-context-packs                │
│  systematic-debugging     →  graph-first-debugging              │
│  requesting-code-review   →  graph-impact-review                │
│  test-driven-development  →  graph-first-testing                │
│  finishing-a-branch       →  architecture-drift-check           │
│  (always)                 →  keeping-the-graph-fresh            │
└─────────────────────────────────────────────────────────────────┘
```
### Reading Skills Without Superpowers
Even without the full Tier 3 setup, skills are useful as documentation:

graph-first-planning/SKILL.md tells you what blast output means for task ordering
architecture-drift-check/SKILL.md explains how to read a drift report
graph-first-testing/SKILL.md maps graph position to test types
## CI Integration
### Architecture Drift Gate
Copy ci/graphpowers-drift.yml to .github/workflows/ in your repo. Every PR gets:

- Base graph built from the target branch (in a worktree)
- Head graph built from the PR
- bridge drift comparison
- Report posted as a sticky PR comment
- Optional: fail the check when drift needs review
```yaml
# In your repo: .github/workflows/graphpowers-drift.yml
env:
  GATE_MODE: warn    # "warn" = always green, comment only (recommended to start)
                     # "block" = fail check on REVIEW NEEDED verdict
```
Requirements in your repo:

- Graphify installable in CI (pip install graphify)
- Graphpowers vendored at .graphpowers/ (or adjust GRAPHPOWERS_DIR)
Rollout recommendation:

- Start with warn. Run on ~10 real PRs. Switch to block when false-flag rate is under 1 in 5. See docs/CI-ROLLOUT.md for the full phase-by-phase checklist.

### Upstream Watch (Weekly Canary)
Copy ci/upstream-watch.yml to .github/workflows/. Runs every Monday:

- Installs latest graphify (and optionally a pinned version)
- Builds a real graph on a fixture project
- Runs the full test suite + every bridge command against that graph
- Clones latest Superpowers and runs upstream-check
- On failure: opens/updates a GitHub issue labeled upstream-watch
This catches upstream breaking changes automatically — see docs/UPSTREAM.md for the full response process.

## Session Hook
The hooks/session-start script fires on every Claude Code session start/resume (Tier 3 only). It:

- Checks if graphify-out/graph.json exists in the current directory
- If yes: runs bridge freshness and reports the status
- Injects the using-graphpowers skill as context
- Outputs in the correct format for Claude Code or Superpowers
What the agent sees at session start:

> Graph status: Graph is FRESH (142 source files checked against graphify-out/graph.json).
>
> Below is your 'graphpowers:using-graphpowers' skill — how the knowledge graph plugs into your development process...
Or if no graph exists:

> Graph status: No graphify-out/graph.json in this directory — offer to build one for non-trivial work.
### Hook Registration
Registered via hooks/hooks.json:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [
          { "type": "command", "command": ""${CLAUDE_PLUGIN_ROOT}/hooks/session-start"" }
        ]
      }
    ]
  }
}
```
## Pack Feedback & Self-Tuning
Context packs improve over time through a feedback loop:

```text
┌────────────────────────────────────────────────────────────┐
│  graph → score_nodes() → pack → subagent                   │
│                                      │                     │
│                                      ▼                     │
│                              Was it sufficient?            │
│                              What was unused?              │
│                              What was missing?             │
│                                      │                     │
│                                      ▼                     │
│  graphpowers-data/pack-feedback.jsonl ← log_feedback()     │
│                                      │                     │
│                                      ▼                     │
│  compute_weights() → adjusted ScoringWeights               │
│         │                                                  │
│         └──→ score_nodes(weights=...) → better packs       │
└────────────────────────────────────────────────────────────┘
```
### How Self-Tuning Works
| Signal | Condition | Weight Adjustment |
| --- | --- | --- |
| Packs insufficient | >30% of packs have pack_was_sufficient: false | Increase seed_boost (include more relevant nodes) |
| Hub nodes unused | >30% of packs have unused hub nodes | Increase hub_penalty (reduce noise from over-connected nodes) |
| Extra reads needed | >30% of packs require agent to discover extra files | Increase community_bonus (include same-community nodes) |
### Usage
```bash
# After a subagent finishes — pack was enough:
graphpowers pack-feedback log --task-id task-3 --sufficient \
  --pack-node login --pack-node auth.py

# After a subagent needed extra context — pack wasn't enough:
graphpowers pack-feedback log --task-id task-4 --insufficient \
  --extra-read src/session.py --unused-node megahub \
  --pack-node login --pack-node auth.py --pack-node megahub

# Check quality over time:
graphpowers pack-feedback stats

# See current weights (JSON output):
graphpowers pack-feedback weights
```
### Default Weights vs. Learned Weights
| Weight | Default | What it does |
| --- | --- | --- |
| seed_boost | 3.0 | Score boost for nodes in --file seed paths |
| degree_tiebreaker | 0.5 | Score boost proportional to node centrality |
| community_bonus | 0.0 | Score boost for same-community nodes (increases with feedback) |
| hub_penalty | 0.0 | Score penalty for very high-degree nodes (increases with feedback) |
Storage: graphpowers-data/pack-feedback.jsonl — one JSONL line per feedback entry. Project-local, add to .gitignore.

## Upstream Compatibility
Graphpowers depends on contracts, not code from upstream:

| Contract | What Graphpowers Uses | How It's Guarded |
| --- | --- | --- |
| graph.json schema | networkx node-link format: nodes[].id/label/source_file/source_location/community, links[].source/target/relation/confidence | graphio.validate_node_link() fails loud on mismatch |
| Graphify CLI | query, path, explain, --update, --watch, --no-viz | upstream-check verifies against --help |
| Superpowers skills | writing-plans, brainstorming, test-driven-development, etc. | upstream-check verifies each exists |
| Hook convention | additionalContext / hookSpecificOutput JSON format | upstream-check verifies upstream hook |
### Compatibility Table
| graphpowers | graph schema | validated against |
| --- | --- | --- |
| 0.1.x | node-link-v1 | graphify test fixtures, July 2026 |
### What Happens When Upstream Changes
- Weekly canary detects it (CI opens an issue)
- You update your references in a single PR
- No upstream code is ever merged, vendored, or submoduled
- See docs/UPSTREAM.md for the full response process
## Exit Code Contract
Every bridge command follows this contract:

| Code | Meaning | Action |
| --- | --- | --- |
| 0 | Fine / fresh / clean / found / no conflicts | Proceed normally |
| 1 | Error (missing file, bad input, node not found) | Fix the error |
| 2 | Needs attention (stale / drifted / high-risk / scope creep / conflicts) | Address before continuing |
This lets hooks, CI, and shell scripts branch on the result without parsing markdown output:

```bash
# Guard in a shell script
graphpowers freshness || { echo "Graph is stale!"; graphify . --update; }

# Gate on risk level
if graphpowers blast src/auth.py; then
  echo "LOW/MEDIUM risk — proceed"
else
  echo "HIGH risk — extra review needed"
fi

# Use in CI
graphpowers drift before.json after.json || exit 1  # block on drift
```
## Tests
```bash
# With pytest (if available):
pytest tests/ -q

# Without pytest (zero-dep runner included):
python3 tests/run_tests.py
```
The test suite covers all bridge modules against an in-memory fixture graph. No graphify installation required to run tests — they exercise the bridge's graph.json parsing and algorithms directly.

### What's Tested
| Module | Tests Cover |
| --- | --- |
| graphio.py | Loading, indexing, schema validation, god nodes, file matching |
| blast_radius.py | BFS traversal, risk classification, unmatched files |
| context_pack.py | Scoring, budget trimming, weight integration |
| drift.py | Node/edge diffs, god node detection, cross-community edges, orphans |
| freshness.py | Mtime comparison, stale file detection |
| lookup.py | Node matching, consumer grouping |
| guard.py | Scope creep detection, surprise node identification |
| narrate.py | Community profiling, narrative generation, empty communities |
| parallel.py | Conflict detection, graph coloring, task parsing |
| explain.py | Orchestration of lookup + blast + pack |
| pack_feedback.py | Logging, history loading, weight computation |
| upstream.py | Reference scanning, contract verification |
| graphio.validate_node_link | Rejection of all invalid inputs with actionable messages |
## Design Principles
### Zero Dependencies, On Purpose
Superpowers works because installing it can't fail. The bridge inherits that: stdlib only, no venv required, PYTHONPATH=… python3 -m bridge works with zero setup. Anything that needs a dependency belongs in graphify, not here.

### The Graph File Is the Contract, Not the Library
The bridge reads graph.json and never imports graphify. This keeps the two projects independently upgradable, lets the bridge run where graphify isn't installed (CI comment jobs, hooks), and means you can use the bridge with any tool that produces compatible graph.json — not just graphify.

### Exit Codes Are the API
Markdown output is for humans and agents; exit codes are for automation. Changing an exit-code meaning is a breaking change.

### Skills Decide, Code Computes
The Python bridge never tells the agent what to do — it produces facts (radius, freshness, drift). The skills own the judgment ("HIGH risk → tests before modification"). This split keeps the code testable and the methodology editable in markdown.

### Honesty Inherits
Graphify labels edge confidence (EXTRACTED / INFERRED / AMBIGUOUS). The bridge preserves the labels and the skills enforce the discipline: no root-cause theory or design decision rests on an AMBIGUOUS edge without source verification.

### Compose, Don't Fork
Neither parent project is modified. Skills reference the Superpowers skills they extend. The bridge reads the artifact graphify produces. No code is vendored, submoduled, or forked.

### Novel Features (Not in Either Parent)
These capabilities exist only because both systems are combined:

- Blast-radius-scoped planning — every plan task carries an evidence-based impact estimate; tasks with overlapping radii are auto-flagged as non-parallelizable

- Context packs with self-tuning — subagents stop burning their first ten tool calls re-discovering the codebase; scoring weights improve from feedback

- Architecture drift detection — snapshot the graph before a branch, diff after: catches accidental god nodes, cross-community coupling, and orphaned code that line-by-line review structurally cannot see

- Live freshness gating — the session-start hook reports graph staleness the moment a session opens; skills refuse to plan/review against a stale map

- Implementation guard — mid-task scope creep detection catches drift from the plan before review

- Parallel safety computation — computable task DAG from pairwise blast radius overlap replaces human judgment about what can run concurrently

- Community narratives — deterministic onboarding descriptions generated from graph structure alone

- Graph-grounded test prioritization — test type (integration/contract/unit/boundary) determined by node position, not developer intuition

## Worked Example: Full Branch Lifecycle
"Add rate limiting to the login endpoint"
0. Session opens.

Hook reports "Graph is STALE — 3 files changed." First action:

graphify . --update    # Requires graphify (Tier 2+)
1. Brainstorm.

graphify query "how does login work today—
Reveals: LoginHandler → SessionManager → TokenStore, and a ThrottleGuard already exists in middleware. Design question becomes concrete: "Reuse ThrottleGuard or build new—

2. Plan.

Per task:

graphpowers blast src/auth/login.py --depth 2
# → Risk MEDIUM, 14 nodes, 2 communities

echo '[{"id":"rate-limit","files":["src/auth/login.py"]},{"id":"config","files":["src/config.py"]}]' \
  | graphpowers parallel
# → Both tasks can run in parallel (no overlap)

graphpowers snapshot
# → graphify-out/graph.snapshot-20260705-051500.json
3. Implement.

Per subagent:

graphpowers pack "add rate limiting to login" --file src/auth/login.py --budget 1200
# Pack prepended to subagent prompt — starts oriented, not blind
Mid-task guard:

graphpowers guard --planned src/auth/login.py
# Catches if the subagent touched files outside the plan
After subagent finishes:

graphpowers pack-feedback log --task-id rate-limit --sufficient \
  --pack-node login --pack-node ThrottleGuard
4. Review.

Blast radius attached to review request:

graphpowers blast src/auth/login.py src/middleware/throttle.py
# Reviewer sees exactly what the change reaches
5. Finish.

graphify . --update
graphpowers drift graphify-out/graph.snapshot-20260705-051500.json graphify-out/graph.json
Clean → merge
Flagged (e.g., "new cross-community edge: LoginHandler → RedisClient") → explain in PR description or fix
Either way: drift verdict in PR, old snapshots pruned, map fresh for next branch
## Credits & Attribution
Graphpowers is an orchestration layer that integrates with, extends, and is inspired by the following projects. Neither is bundled in this repository; both are runtime/companion dependencies.

### Graphify
Repository: https://github.com/Graphify-Labs/graphify
Copyright: (c) 2026 Safi Shamsi
License: MIT (see licenses/GRAPHIFY-LICENSE)
Relationship: Graphpowers consumes the graphify-out/graph.json artifact Graphify produces and invokes the graphify CLI in its workflows. No Graphify source code is included in this repository.
### Superpowers
Repository: https://github.com/obra/superpowers
Copyright: (c) 2025 Jesse Vincent
License: MIT (see licenses/SUPERPOWERS-LICENSE)
Relationship: Graphpowers skills follow the Superpowers skill format and extend Superpowers skills by reference (e.g. superpowers:writing-plans). The session-start hook follows the Superpowers hook output convention. Skill texts in this repository are original; no Superpowers skill content is copied.
### How Credit Works in Practice
- Every graphpowers skill that extends a Superpowers skill says so explicitly (e.g., "This skill extends superpowers:writing-plans")
- The session hook mirrors the Superpowers hook output convention — documented, not copied
- The bridge reads graphify's output format — documented in the schema guard, not reverse-engineered
- Full license texts for both projects are in licenses/
- THIRD_PARTY_NOTICES.md contains the complete attribution notice
## License
[MIT](LICENSE) © [Nextbridge](https://nextbridge.com)

Upstream attributions and license texts: THIRD_PARTY_NOTICES.md and licenses/.

Built and maintained by **[Nextbridge](https://nextbridge.com)**

[GitHub](https://github.com/nextbridgehq/graphpowers) · [Issues](https://github.com/nextbridgehq/graphpowers/issues)
