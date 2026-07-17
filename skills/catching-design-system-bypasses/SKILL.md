---
name: catching-design-system-bypasses
description: Use when reviewing or writing frontend code in a repo with a design system and a knowledge graph - detects components that bypass the design system with raw elements or one-off styling, and routes new UI through sanctioned components
---

# Catching Design System Bypasses

## Overview

Design systems die by a thousand bypasses: one raw `<button>` here, one
inline hex color there. Each is invisible in review; the graph makes the
pattern visible.

**Core principle:** If a sanctioned component exists, new code uses it —
and the graph is how you check.

## The Process

### 1. Know the sanctioned vocabulary

```bash
graphify query "what components does the design system export?"
python3 -m bridge who-uses "Button"     # per-component adoption picture
```

High degree on design-system components = healthy adoption. A sanctioned
component with degree 2 in a large app is either new or being bypassed.

### 2. Audit for bypasses (review time)

For each primitive the system wraps (button, input, modal, colors):

```bash
graphify query "which components render raw button elements instead of the Button component?"
```

Cross-check suspicious files by hand — the graph narrows the search from
"the whole frontend" to a shortlist. `AMBIGUOUS` edges get verified in
source before you accuse anyone of bypassing.

### 3. When writing new UI

Before creating any element the design system covers:

- `who-uses` the sanctioned component to copy a real usage pattern from
  a healthy consumer — not from memory
- If the sanctioned component genuinely can't do what you need, that's a
  design-system gap: extend the component (with its own
  `component-blast-radius` check) rather than bypassing it locally

### 4. Track drift over releases

`architecture-drift-check` output doubles as a design-system monitor:
new nodes with UI file paths that connect to raw primitives instead of
the design-system community are bypass candidates. Flag them in the
drift review.

## Red Flags — STOP

- Styling values (colors, spacing) hardcoded where tokens exist
- A new component duplicating 80% of a sanctioned one
- "I'll migrate it to the design system later" — later never comes;
  the graph will remember
