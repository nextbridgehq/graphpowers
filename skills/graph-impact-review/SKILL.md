---
name: graph-impact-review
description: Use when requesting or performing code review in a repo with a knowledge graph, before merging - generates a reviewer checklist from the change's blast radius so review effort lands where the risk is
---

# Graph Impact Review

## Overview

Reviewers read the diff. The diff shows what changed; the graph shows what
the change *reaches*. Most escaped bugs live in the gap between those two.

**Core principle:** Review effort proportional to blast radius, not to
diff size.

This skill extends `superpowers:requesting-code-review` and
`superpowers:receiving-code-review`.

## When requesting review

### 1. Compute and attach the blast radius

```bash
python3 -m bridge blast --depth 2   # uses git diff automatically
```

Attach the markdown output to the review request. A 3-line diff that
reaches a god node deserves more scrutiny than a 300-line diff in a leaf
community — the radius makes that visible.

### 2. Answer the radius in advance

For each item, pre-empt the reviewer:

- **God nodes in range** → point to the regression tests covering them
- **Depth-1 hits outside the diff** → state why each is safe ("query()
  signature unchanged; behavior covered by test_db.py")
- **Unmatched files** → new files, or a stale graph? Say which.

## When performing review

Run the blast yourself — never trust the submitter's radius (the same
skepticism `receiving-code-review` demands of feedback applies in both
directions).

Checklist, in order:

1. Every god node in range: does a test exercise it on this branch?
2. Every depth-1 hit NOT in the diff: open it, confirm the contract the
   change relies on still holds.
3. Cross-community reach: is the coupling this change introduces
   intentional? (If unclear → run `architecture-drift-check`.)
4. Only then read the diff line by line.

## Red Flags — STOP

- Approving a HIGH-risk blast with no new tests
- "The diff is small so the review is quick"
- Skipping depth-1 hits because they're not in the diff — that is
  exactly where the diff can't protect you
