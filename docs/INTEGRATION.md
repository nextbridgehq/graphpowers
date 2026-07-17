# How the pieces fit: a full branch lifecycle

Walkthrough of one feature branch with all three systems active.

## 0. Session opens
The graphpowers session-start hook fires. It injects `using-graphpowers`
and a live status line, e.g. "Graph is STALE - 3 files changed since it
was built." Superpowers' own hook injects `using-superpowers`. The agent
runs `graphify . --update` before anything else.

## 1. Brainstorm (superpowers:brainstorming + graph-first-brainstorming)
Agent runs `graphify query "how does checkout work today?"` and asks the
user design questions that name real nodes. If changing signatures, `python3 -m bridge who-uses <node>` performs a reverse-dependency lookup to find all callers. The chosen design cites the
communities and god nodes it touches.

## 2. Plan (superpowers:writing-plans + graph-first-planning)
For each task the agent runs `python3 -m bridge blast <files>`.
Tasks get graph-verified file lists, risk levels, and parallel-safety
flags. Then `python3 -m bridge snapshot` records the "before" graph.

## 3. Implement (subagent-driven-development + graph-context-packs)
For each dispatched subagent the orchestrator runs
`python3 -m bridge pack "<task>" --file <seed files>` and prepends the
pack to the prompt. Subagents follow superpowers:test-driven-development
as usual; if they hit a bug, graph-first-debugging bounds the search.

## 4. Review (requesting/receiving-code-review + graph-impact-review)
The blast radius rides along with the review request. The reviewer
re-runs it independently, checks god nodes for test coverage, opens
depth-1 hits outside the diff. For UI work, `component-blast-radius` and `catching-design-system-bypasses` skills extend this same discipline to frontend reviews.

## 5. Finish (finishing-a-development-branch + architecture-drift-check)
After verification-before-completion passes:
`graphify . --update` then
`python3 -m bridge drift graphify-out/graph.snapshot-*.json graphify-out/graph.json`.
Clean -> merge. Flagged -> explain or fix. Either way the drift verdict
goes in the PR description, old snapshots are pruned
(keeping-the-graph-fresh), and the map is current for the next branch.

## Exit-code contract
All bridge commands: 0 = fine, 1 = error, 2 = needs attention
(stale graph / drift flagged / HIGH-risk blast). Hooks and CI can gate
on this without parsing output.

## Worked example: "add rate limiting to the login endpoint"

**0. Session opens.** Hook reports "Graph is STALE - 3 files changed
since it was built." First action: `graphify . --update` (only those 3
files re-extracted). Nothing downstream runs against a stale map.

**1. Brainstorm.** `graphify query "how does login work today?"` reveals
the flow: LoginHandler -> SessionManager -> TokenStore, and that a
ThrottleGuard node already exists in the middleware community. The
design question to the user becomes concrete: "Put rate limiting in
LoginHandler, or reuse ThrottleGuard in middleware?" Real options, not
imagined ones.

**2. Plan.** Per task:

    python3 -m bridge blast src/auth/login.py --depth 2
    # -> Risk MEDIUM, 14 nodes, 2 communities

The risk line goes into the task. Tasks with overlapping radii are
marked sequential; disjoint ones parallel-safe. Then:

    python3 -m bridge snapshot
    # -> graphify-out/graph.snapshot-20260705-051500.json

Snapshot filename recorded in the plan header (setup for step 5).

**3. Implement.** Per dispatched subagent:

    python3 -m bridge pack "add rate limiting to login" \
        --file src/auth/login.py --budget 1200

Pack is prepended to the subagent prompt: key nodes with file:line,
relationships, files to read first. The subagent starts oriented instead
of spending its first ten tool calls grepping. Bugs during the task ->
graph-first-debugging (`graphify path` from symptom to suspect).

**4. Review.** Blast radius attached to the review request; the reviewer
re-runs it independently. God nodes in range need tests on this branch.
Depth-1 hits OUTSIDE the diff get opened and verified - the gap between
"what changed" and "what it reaches" is where escaped bugs live.

**5. Finish.** After verification-before-completion passes:

    graphify . --update
    python3 -m bridge drift \
        graphify-out/graph.snapshot-20260705-051500.json \
        graphify-out/graph.json

Suppose it flags: "new cross-community edge: LoginHandler -uses->
RedisClient." If the plan intended Redis-backed rate limiting, one
sentence of justification goes in the PR and it merges. If not, you
just caught accidental coupling that tests and line review structurally
cannot see. Verdict into the PR description, old snapshots pruned, map
fresh for the next branch -> back to step 0.

Once the CI gate (docs/CI-ROLLOUT.md) is live, step 5's drift check also
runs automatically on every PR - the discipline holds even when someone
skips the ritual.
