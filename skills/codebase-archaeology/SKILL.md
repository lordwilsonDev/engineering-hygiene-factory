---
id: codebase-archaeology
family: hygiene
version: 0.0.1
objective: >
  Map the project structure, languages, frameworks, services, APIs,
  databases, dependencies, configuration, security boundaries, and
  automation without changing anything.
inputs:
  - project_root
actions:
  - enumerate files/directories
  - detect languages/frameworks
  - list services/APIs/databases
  - map configuration
  - identify deployment, test infra, persistence, security boundaries
experiments:
  - directory_scan
  - language_detection
  - dependency_graph
  - security_boundary_map
evidence_required:
  - PROJECT_MAP.yaml
  - dependency_tree.json
  - security_boundaries.yaml
success_conditions:
  - PROJECT_MAP complete
  - all top-level directories explained
failure_conditions:
  - unknown directory purpose
  - missing dependency documentation
artifacts:
  - PROJECT_MAP.yaml
  - evidence.json
---

# Codebase Archaeology

## PURPOSE
Non-destructive project mapping.

## EXECUTION
1. Walk directory tree.
2. Detect languages by extension.
3. Parse manifests (package.json, pyproject.toml, etc.).
4. Identify entrypoints, config files, test directories.
5. Produce PROJECT_MAP.

## DOGFOOD RULE
Archaeology on the factory itself must produce a complete PROJECT_MAP with no unknowns.
