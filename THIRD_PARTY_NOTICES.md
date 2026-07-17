# Third-party notices

Graphpowers is an orchestration layer that integrates with, extends, and
is inspired by the following projects. Neither is bundled in this
repository. Graphify is a companion tool whose output (graph.json)
the bridge reads; Superpowers is a methodology whose skill format
and conventions the skills follow.

---

## Graphify

- Repository: https://github.com/Graphify-Labs/graphify
- Copyright (c) 2026 Safi Shamsi
- License: MIT (see `licenses/GRAPHIFY-LICENSE`)
- Relationship: Graphpowers consumes the `graphify-out/graph.json`
  artifact Graphify produces and invokes the `graphify` CLI in its
  workflows. No Graphify source code is included in this repository.

---

## Superpowers

- Repository: https://github.com/obra/superpowers
- Copyright (c) 2025 Jesse Vincent
- License: MIT (see `licenses/SUPERPOWERS-LICENSE`)
- Relationship: Graphpowers skills follow the Superpowers skill format
  and extend Superpowers skills by reference (e.g.
  `superpowers:writing-plans`). The session-start hook follows the
  Superpowers hook output convention. Skill texts in this repository
  are original; no Superpowers skill content is copied.
