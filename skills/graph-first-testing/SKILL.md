---
name: graph-first-testing
description: >-
  Use when deciding test coverage priorities — god nodes and bridge nodes
  need tests first; leaf nodes can wait. Determines test types
  (integration, contract, unit, boundary) from graph structure.
---

# Graph-First Testing

Extends **superpowers:test-driven-development** with structural awareness.
Before deciding *what* to test, consult the graph to learn *where risk
concentrates*. The graph tells you which nodes are load-bearing (god
nodes), which connect otherwise-independent parts (bridge nodes), and
which are safely isolated (leaf nodes). Test type follows from position.

## When to use

- Before writing tests for changed files
- When prioritizing test coverage in a plan
- When a regression's root cause is unclear and you need to scope tests

## Process

### 1. Identify what's in range

```bash
PYTHONPATH=<graphpowers-root> python3 -m bridge blast <changed-files>
```

Everything in the blast radius needs test coverage. The risk level
(LOW / MEDIUM / HIGH) tells you how much:

| Risk | Interpretation | Test expectation |
|------|---------------|------------------|
| LOW  | Isolated change, ≤40 nodes, ≤3 communities | Unit tests for the changed node |
| MEDIUM | Moderate reach, >40 nodes or >3 communities | Unit + contract tests |
| HIGH | God node in range | Integration tests **mandatory** |

### 2. Classify nodes by graph position

For each node in the blast radius, determine its test type:

#### God nodes (highest degree) → Integration tests
```bash
PYTHONPATH=<graphpowers-root> python3 -m bridge who-uses "<NodeLabel>"
```

God nodes appear in the blast report's warning section. They connect to
many consumers — a break here cascades everywhere. Write integration
tests that exercise the god node with its real dependencies, not mocks.

#### Bridge nodes (connect communities) → Contract tests

Bridge nodes sit between communities. Identify them: they appear in
cross-community edges in the blast report or have neighbors in
multiple communities. Write contract tests that verify the interface
both communities depend on.

Test pattern:
- Verify the function signature hasn't changed
- Verify the return type / shape matches what consumers expect
- Verify error cases return the documented error, not a crash

#### Leaf nodes (degree ≤ 2) → Unit tests

Leaf nodes have few connections. They're safe to test in isolation
with mocks. Standard TDD: write the failing test, implement, pass.

#### Cross-community edges → Boundary tests

When a change introduces or modifies an edge between two communities,
write a boundary test that verifies the integration between them.
This catches the case where both communities pass their own tests
but the handoff between them is broken.

### 3. Priority order

Write tests in this order:
1. **God nodes** — most damage if broken
2. **Bridge nodes** — hardest to debug if broken (symptoms in wrong community)
3. **Boundary tests** — catch integration failures early
4. **Leaf nodes** — last, because failures are contained

### 4. Coverage check

After writing tests, verify coverage against the blast radius:

```bash
PYTHONPATH=<graphpowers-root> python3 -m bridge blast <changed-files>
```

Every node at depth 0 (seed) and depth 1 should have at least one test
that exercises it. Nodes at depth 2 should have tests if they're god
or bridge nodes.

## Red Flags — STOP

- **God node with no tests:** Do not proceed with any other work.
  Write integration tests for the god node first. A god node failure
  can break the entire codebase.

- **Bridge node test fails:** Before debugging, check both communities
  it connects. The bug may manifest in one community but originate
  in the other. Run `graphpowers who-uses` to see both sides.

- **Changed file has no graph node:** The graph is stale. Run
  `graphify . --update` before making test decisions — you may be
  missing connections.

- **AMBIGUOUS edges in the blast radius:** Do not write tests based
  on relationships marked AMBIGUOUS without first verifying them in
  source. An AMBIGUOUS edge may not represent a real dependency.

## Example

Given changed files `src/auth.py` and `src/session.py`:

```bash
# Step 1: What's in range?
python3 -m bridge blast src/auth.py src/session.py

# Output shows: Risk HIGH, god node SessionManager touched

# Step 2: What uses the god node?
python3 -m bridge who-uses "SessionManager"

# Step 3: Write tests in priority order
# 1. Integration test for SessionManager (god node)
# 2. Contract test for AuthProvider (bridge: auth ↔ session communities)
# 3. Unit tests for login(), validate_token() (leaf nodes)
```
