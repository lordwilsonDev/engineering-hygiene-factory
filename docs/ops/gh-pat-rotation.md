# GH_PAT Rotation Recipe

The `GH_PAT` secret was pasted into chat history (2026-08-10) — it must be
rotated. As of 2026-09-17 **three** repos carry a copy; the rest of the
constellation needs nothing.

**STATUS: OVERDUE.** This rotation was required on 2026-08-10 and was never
done. The unrotated token expired on 2026-09-09T04:44Z, which caused the
incident recorded at the bottom of this file — including a false-green PASS
published to `msb-v3`. Rotating now closes both the hygiene debt and the
outage.

## Where GH_PAT lives (re-checked 2026-09-17)

| Repo | Secret | `updated_at` | Used for |
|---|---|---|---|
| `lordwilsonDev/engineering-hygiene-factory` | `GH_PAT` | 2026-08-10T04:44:52 | `self-test.yml` + `strict-gate.yml` check out all 7 constellation repos (the gate's whole cross-repo region) |
| `lordwilsonDev/domain-router` | `GH_PAT` | 2026-08-10T04:44:51 | `routing-gate.yml` checks out `skill-orchestration-os` (canonical runtime), `vault-tooling`, and probes `vault-search-mcp` |
| `lordwilsonDev/sovereign-outcome-engine` | `GH_PAT` | 2026-08-10T14:16:21 | `factory-gate.yml` checks out `engineering-hygiene-factory` for the s05 claim-container validator |

That third copy is the one this runbook previously missed — it was set ~9.5
hours after the other two and post-dates the first draft of this file. Do not
trust "two repos" from any older note.

Two corrections to earlier statements here, both verified against the API on
2026-09-17:

- The five project repos are **not** all GH_PAT-free: `sovereign-outcome-engine`
  carries a copy (the checkout it gates feeds s05).
- There are **no environment-scoped** copies — all three are repo-level, so
  `gh secret set -R <repo>` is the correct (and only) target. Confirmed via
  `/actions/secrets` and `/environments` on all eight repos.

## Required scope of the replacement

A **fine-grained PAT**, "Only select repositories", with
`Contents: Read-only` and nothing else. Two of the repos are private and
**must be selected explicitly**:

- `lordwilsonDev/agent-reach` (private)
- `lordwilsonDev/vault-tooling` (private)

These are needed but public, so selecting them is unnecessary — a fine-grained
PAT can read public repos without being granted them:

`msb-v3`, `nexus`, `skill-orchestration-os`, `sovereign-mcp-os`,
`sovereign-outcome-engine`, `domain-router`, `engineering-hygiene-factory`

`vault-search-mcp` does not exist yet. `domain-router` probes for it and skips
d06/d07 visibly when it is absent, so it is not an error — but see the warning
below.

Prefer fine-grained over a classic PAT: a classic token's `repo` scope grants
**write** to every repo in the account, which is the opposite of what a
read-only cross-repo checkout needs.

### An under-scoped token fails quietly, so scope is load-bearing

Get this list wrong and the gate still runs — it just verifies less. In
`domain-router`, a token that cannot read `vault-tooling` makes the probe report
404, the checkout skip, and d06/d07 skip with an explicit message. A green run
is therefore **not** proof the legs ran. Always confirm the legs *executed*
(step 3 below), because that is what distinguishes a working gate from a
well-annotated skip.

## Steps

1. **Mint** (human step — GitHub has no PAT-creation API):
   <https://github.com/settings/personal-access-tokens/new>

   Set an expiry you will actually notice. A 30-day token is what expired
   silently here; if you keep one, put the date in your calendar at creation
   time.

2. **Set all three secrets.** Use the prompting form (no `--body`): `--body`
   puts the token in shell history and in `ps` output, and this file exists
   precisely because a token leaked into a transcript once.

   ```bash
   gh secret set GH_PAT --repo lordwilsonDev/engineering-hygiene-factory
   gh secret set GH_PAT --repo lordwilsonDev/domain-router
   gh secret set GH_PAT --repo lordwilsonDev/sovereign-outcome-engine
   ```

2b. **Check the scope BEFORE committing the token to three repos.** A token
   missing `vault-tooling` looks healthy until d06/d07 quietly skip (see
   above). Both of these must print `200`:

   ```bash
   read -rs -p 'new token: ' TOKEN; echo          # read -s: never in history
   for r in agent-reach vault-tooling; do
     curl -s -o /dev/null -w "  $r: %{http_code}\n" \
       -H "Authorization: Bearer $TOKEN" \
       -H "Accept: application/vnd.github+json" \
       "https://api.github.com/repos/lordwilsonDev/$r"
   done
   unset TOKEN
   ```

3. **Prove it** — one run per repo, and check that the leg *executed* rather
   than skipped:

   ```bash
   # factory: the whole cross-repo region must run, not skip
   gh workflow run self-test.yml --repo lordwilsonDev/engineering-hygiene-factory
   gh run view --repo lordwilsonDev/engineering-hygiene-factory --log \
     | grep -E 'self-test|Enforcement tests|Strict constellation'

   # domain-router: d07 must execute the 26-case structural oracle (not skip)
   gh workflow run routing-gate.yml --repo lordwilsonDev/domain-router

   # sovereign-outcome-engine (dormant — dispatch it, or the next push surprises you)
   gh workflow run factory-gate.yml --repo lordwilsonDev/sovereign-outcome-engine
   ```

   The fast check for all three: the `Validate GH_PAT` step must print
   `GH_PAT valid (HTTP 200)` and the gated checkouts must read `success`, never
   `skipped`. A 403 there means the scope is incomplete; a 401 means the token
   is dead.

4. **Revoke the old tokens** in the GitHub UI once the new one is proven —
   <https://github.com/settings/tokens> and
   <https://github.com/settings/personal-access-tokens>. Chat history still
   contains token-shaped values from the 2026-08-09/08-10 sessions (both
   `github_pat_…` and `ghp_…` shapes). The copy that was in the secrets is dead
   (HTTP 401), but **liveness of the others cannot be checked via API** — the
   PAT-listing endpoint is not reachable with this session's credentials. Check
   the UI; do not assume they are inert.

## Why it matters

The factory's own ethos: "versioned, not assumed." A token in chat history is
an un-versioned credential — rotating it closes the only remaining
secret-hygiene gap in the constellation. Leaving it unrotated is what produced
the incident below: an expiry nobody was watching, hidden behind a guard that
could only tell "set" from "unset".

## Incident: the 2026-09-09 expiry (recorded 2026-09-17)

```
secret last written      : 2026-08-10T04:44:52Z
30-day expiry from write : 2026-09-09T04:44:52Z   <- lands inside the dead window
last run that used it OK : 2026-09-08T12:06Z
first run it was rejected: 2026-09-09T11:45Z      (401 Bad credentials)
```

Eight days of red across two repos, with no cause named. All three guards were
`if: env.GH_PAT != ''` — they tested **presence, never validity**, so a
present-but-dead token ran the checkout, got a 401, and took every later step
down with it. All three now carry a non-fatal `Validate GH_PAT` preflight that
names 401 (rotate) vs 403/404 (scope), keeps the dependent steps from dying at
the first one, and fails a final step so an inert green can never read as a
verified gate:

| Repo | Guard hardened | Behaviour on a dead token |
|---|---|---|
| `engineering-hygiene-factory` | 2026-09-17 | secret-free checks still run; red is attributed, not generic |
| `domain-router` | 2026-09-17 | all 10 legs skip; final step fails with the cause named |
| `sovereign-outcome-engine` | 2026-09-17 | the factory checkout skips, s05 fails, s01-s04 still report; final step names the cause |

The first two have been observed live against the dead token (runs
`35211787551` and `35215702840`). The third is committed but has not yet had a
run — the repo is dormant since 2026-08-10, so the next push is its first and
its gate will be RED (correctly) until the token is rotated.

Note the third needed a different shape, and not only cosmetically. Its only
fail-loud property had rested on s05 noticing a missing validator file — which
in turn rests on committed claim containers existing under
`artifacts/business/`. Empty that directory and s05 passes trivially ("nothing
to validate"), so a token problem would have gone GREEN even though four token-
independent experiments kept running. Its final step therefore asserts the
validator is **on disk** rather than trusting the token's usability, which
makes the red independent of what the artifact directory holds.

The cost of this incident was not only the outage. `msb-v3`'s gate published a
**PASS with `regression_passed: false`** on 2026-09-16 — a false green that
survived until the verdict guard landed. The two fixes are complementary: the
verdict guard stops a red suite publishing PASS, and this rotation stops a
credential expiring into an unattributed red.

### Durable alternative

Every rotation re-arms the same timer. A **GitHub App** with `Contents: read`
on the two private repos installs once, and workflows mint a short-lived
installation token per run — nothing to expire, nothing to paste, nothing to
rotate. More setup than a PAT, and it retires this document's reason to exist.
