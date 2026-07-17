# Known Limitations

Graphpowers relies on static analysis via Graphify and makes explicit
design trade-offs favoring speed, offline operation, and conservatism
over perfect precision.

## False Positives (Conservatism)

Because `blast` and `guard` aim to catch unintended consequences, they
traverse impact edges *bidirectionally*. This means that if `Helper` is
used by 50 models, changing `Helper` flags all 50 models (correctly),
but changing one of the 50 models might flag `Helper` depending on the
edge relation. This leads to false positives, but ensures reviewers
don't miss anything.

## Language Support Constraints

Graphify parses source code statically via Tree-sitter to build the
graph. It does not run the code or resolve runtime dependency injection,
reflection, or dynamic imports. Graphpowers inherits these limitations —
relationships that Graphify cannot extract will be absent from the graph
and invisible to blast radius, drift, and all other bridge commands.

## Granularity

The graph is file- and symbol-level. A 1,000-line god node will trigger
massive blast radii. The solution is to refactor the code, not tune the
tool — the tool is correctly reporting the architectural risk of the file.

## Path Normalization

Internally, all file paths are converted to POSIX format using
`Path.as_posix()`. Windows backslashes are converted automatically.
When mapping changed files to graph nodes:

1. **Exact match** is tried first (repository-relative POSIX path).
2. **Suffix match** is used as a fallback — `auth.py` will match
   `src/auth.py` in the graph, and vice versa.

This means:
- `src\auth.py` (Windows) and `src/auth.py` (POSIX) are equivalent.
- Bare filenames like `auth.py` will match any graph node whose
  `source_file` ends with that name.
- In repos with duplicate filenames across directories (e.g.,
  `api/models.py` and `web/models.py`), use full relative paths to
  avoid ambiguous matches.

The suffix heuristic exists because the graph may be built from a
parent or child directory, causing path prefixes to differ. It is
conservative — it may match more nodes than intended, never fewer.

## Community ID Instability in Drift

Community detection algorithms (used by Graphify) assign arbitrary
numeric IDs to clusters. These IDs are **not guaranteed stable** across
graph rebuilds — the same group of nodes may be labeled community 3 in
one build and community 7 in the next.

**Impact:** `graphpowers drift` may report "new cross-community edges"
that actually reflect relabeling rather than real architectural change.

**Mitigation:** The drift command detects mass relabeling (>30% of
surviving nodes changed community) and prints a warning when this
occurs. If you see this warning, the cross-community findings should
be treated as unconfirmed until both graphs are rebuilt from the same
Graphify version.

*(Future enhancement: Graphpowers may eventually compute community continuity dynamically via node overlap (e.g., Jaccard similarity) to automatically map old communities to new ones.)*

## Freshness Uses mtime Only

The freshness check compares file modification times against
`graph.json`'s mtime. This can produce false positives after:

- `git checkout` or `git rebase` (touches mtimes without real changes)
- CI cache restoration
- Filesystem clock skew

And false negatives if files are modified with preserved timestamps
(rare in practice).

When in doubt, `graphify . --update` is cheap (incremental) and
eliminates uncertainty.

## Approximate Token Budgets

Context pack `--budget` uses a character-based estimate (~4 chars per
token). Actual token counts vary by model and tokenizer. Packs may
be slightly over or under the stated budget.
