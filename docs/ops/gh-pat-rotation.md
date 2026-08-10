# GH_PAT Rotation Recipe

The `GH_PAT` secret was pasted into chat history (2026-08-10) — it must be
rotated. Only **two** repos carry it; the rest of the constellation needs
nothing.

## Where GH_PAT lives (checked 2026-08-10)

| Repo | Secret | Used for |
|---|---|---|
| `lordwilsonDev/domain-router` | `GH_PAT` | routing-gate CI checks out `vault-tooling` + `skill-orchestration-os` (d06/d07) |
| `lordwilsonDev/engineering-hygiene-factory` | `GH_PAT` | self-test CI clones a sample project (`nexus`) and runs a full gate |

The five project repos (msb-v3, agent-reach, sovereign-mcp-os,
sovereign-outcome-engine, nexus) have **no** GH_PAT — their gates are fully
self-contained.

## Required scope of the replacement

A **fine-grained PAT** with read-only access to exactly:
- `lordwilsonDev/vault-tooling`
- `lordwilsonDev/skill-orchestration-os`
- `lordwilsonDev/domain-router`
- `lordwilsonDev/nexus`

(Or a classic PAT with the `repo` scope — broader, still fine.)

## Steps

1. **Mint** (human step — GitHub has no PAT-creation API):
   <https://github.com/settings/personal-access-tokens/new>

2. **Set** both secrets:
   ```bash
   gh secret set GH_PAT --repo lordwilsonDev/domain-router --body <NEW_TOKEN>
   gh secret set GH_PAT --repo lordwilsonDev/engineering-hygiene-factory --body <NEW_TOKEN>
   ```

3. **Prove** with a real cross-repo checkout:
   ```bash
   gh workflow run routing-gate --repo lordwilsonDev/domain-router
   # watch it: d07 must execute the 26-case structural oracle (not skip)
   ```

4. **Revoke** the old tokens (both `github_pat_…` and `ghp_…` from chat
   history) in the GitHub UI once the new one is proven.

## Why it matters

The factory's own ethos: "versioned, not assumed." A token in chat history is
an un-versioned credential — rotating it closes the only remaining secret-
hygiene gap in the constellation.
