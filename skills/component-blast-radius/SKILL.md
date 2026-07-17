---
name: component-blast-radius
description: Use before modifying any shared UI component (props, markup, styling, behavior) in a repo with a knowledge graph - enumerates every screen and component that consumes it so visual regressions are checked where they will actually appear
---

# Component Blast Radius

## Overview

A "small tweak" to a shared component ships to every screen that renders
it. The diff shows one file; the users see twelve. The graph already
knows all twelve.

**Core principle:** You are not changing a component. You are changing
every place it appears.

## The Process

### 1. Enumerate the consumers

```bash
python3 -m bridge who-uses "Button"
```

Read the relations: `renders`/`uses`/`imports` edges are your consumer
list, grouped and located with file:line.

### 2. Widen to screens

Consumers of consumers matter too — a `Card` change reaches every page
that renders anything containing a Card:

```bash
python3 -m bridge blast src/components/Card.tsx --depth 2
```

### 3. Classify the change, scale the checking

| Change type | Minimum verification |
|---|---|
| Behavior (handlers, state) | tests for every depth-1 consumer |
| Props API (add optional) | typecheck across radius |
| Props API (rename/remove/required) | update EVERY consumer in the same branch — the radius is your todo list |
| Visual (spacing, color, size) | eyeball each distinct consumer context; screenshot the top 3 by traffic if you have visual tests |

### 4. In the plan / PR

Paste the consumer list into the task or PR description. "Verified in
all 12 consumers" is a claim `superpowers:verification-before-completion`
can hold you to; "should be fine" is not.

## Red Flags — STOP

- Editing a component whose consumer count you don't know
- "It's just CSS" — visual changes have the widest radius of all
- Renaming a prop and fixing only the consumers TypeScript complains
  about (template/string usages don't typecheck)
