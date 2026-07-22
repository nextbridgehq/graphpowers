# Third-Party Notices

Graphpowers integrates with and is compatible with the following
open-source projects. None of these projects are bundled,
redistributed, or included in this repository. This document provides
attribution and licensing information as required by their respective
licenses.

## Graphify

| | |
|---|---|
| **Repository** | https://github.com/Graphify-Labs/graphify |
| **Copyright** | © 2026 Safi Shamsi |
| **License** | MIT — see [`licenses/GRAPHIFY-LICENSE`](licenses/GRAPHIFY-LICENSE) |

### Relationship

Graphpowers consumes the `graphify-out/graph.json` artifact generated
by Graphify and invokes the `graphify` CLI as part of its workflows.
No Graphify source code is included, redistributed, or modified by
this project.

## Superpowers

| | |
|---|---|
| **Repository** | https://github.com/obra/superpowers |
| **Copyright** | © 2025 Jesse Vincent |
| **License** | MIT — see [`licenses/SUPERPOWERS-LICENSE`](licenses/SUPERPOWERS-LICENSE) |

### Relationship

Graphpowers adopts the Superpowers skill format and hook conventions
for compatibility. Skills in this repository may reference Superpowers
skills by name (e.g., `superpowers:writing-plans`) and follow the
same session-start hook output convention. All skill content in this
repository is original and independently authored; no Superpowers
source code or skill content is copied or redistributed.