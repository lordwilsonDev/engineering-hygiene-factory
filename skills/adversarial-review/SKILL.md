---
id: adversarial-review
family: hygiene
version: 0.0.1
objective: >
  Human-level adversarial review of architecture, design, and
  implementation for weaknesses.
inputs:
  - project_root
  - architecture_docs
actions:
  - review architecture
  - review design
  - review implementation
  - identify weaknesses
experiments:
  - architecture_review
  - design_review
  - impl_review
  - threat_modeling
evidence_required:
  - review_notes.md
  - weakness_catalog.json
success_conditions:
  - no critical weaknesses
  - all concerns addressed
failure_conditions:
  - critical weakness found
  - unresolved concern
artifacts:
  - review_notes.md
  - weakness_catalog.json
---

# Adversarial Review

## PURPOSE
Human-level adversarial architecture review.
