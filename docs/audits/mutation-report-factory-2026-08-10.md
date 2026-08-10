# Mutation Report — The Factory's Own Verifier (2026-08-10)

**Who verifies the verifier?** Mutation testing does. This report is the
artifact-backed evidence for the claim "the engineering-hygiene factory's own
tests kill real bugs in the factory."

## Canonical result (round 2, full run)

| Metric | Value |
|---|---|
| Score | **61.8%** (1242 killed / 2011 total) |
| Killed | 1242 |
| Survived | 765 |
| Suspicious | 2 |
| Timeout | 2 |
| Baseline before closure | **0.0%** — 917 mutants had NO tests; the 482 that were tested all survived |

Tool: mutmut 3.7.0. Paths mutated: `scripts/run_factory.py`,
`scripts/status_report.py`. Harness: `.mutmut-scratch/` (bare-filename source
symlinks so mutmut 3.7 trampoline keys match the flat `import run_factory`
the tests use; root-invocation fails with a trampoline mismatch by design —
see `setup.cfg` note).

## What the baseline proved

Before round 1, the factory's own suite was **plumbing smoke tests**: they
proved the factory *runs* (gate file written, table rendered) but never that
it *decides correctly*. Mutating the verifier made the gap undeniable:
not one mutant was caught.

## What closed it (tests/test_mutation_closure.py, ~60 behavioral tests)

- `load_suite_config` fallbacks (malformed JSON, empty/non-dict experiments,
  live_auth preservation, bad coverage config, env default)
- `load_dotenv` parsing (comments, `=`-in-value, stripping)
- `_zero_spend_env` / `_spawn` env-scrub + cwd/timeout pass-through
- `_extract_json_object` top-level-object scan
- `run_suite` (no runner, unexpected returncode, aggregate parse, garbage)
- `verify_live_auth` verdict logic (200/401/401 via stubbed urlopen,
  HTTPError/URLError paths, dotenv secret, scoped-out)
- `build_gate` verdict map + exact unknowns + evidence fields
- `run_pytest` edges (timeout, failure, count-line pick, TOTAL parse)
- CLI mains (`--check`/`--strict`/`--with-ci`; `--project` pipeline incl.
  coverage-miss forced-FAILED and live-auth scoped-out notes)
- exact-string pinning of every verdict detail/reason string

## Real bug found by the closure tests

`status_report.render_markdown` rendered the coverage cell as **`None%`** for
projects with no coverage config (operator-precedence bug in the conditional).
Fixed; pinned by `test_render_markdown_cov_cell_variants`.

## Remaining survivors (honest inventory)

Dominant clusters are the subprocess/network/print shells — low-value
mutation surface, not logic gaps: `run_factory.x_main` (~300 argparse/print
mutants), `self_test`, `ci_conclusion` (gh subprocess), `last_commit_time`,
`run_suite`, `run_pytest`, `verify_live_auth` (io-heavy). The pure-logic
verdict builders (`build_gate`, `derive_state`, `assess_coverage`,
`load_suite_config`) are now pinned with exact-value tests.

## Regenerate

```bash
cd .mutmut-scratch && /opt/homebrew/Caskroom/miniforge/base/bin/python -m mutmut run --max-children 4
cd .mutmut-scratch && /opt/homebrew/Caskroom/miniforge/base/bin/python -m mutmut results --all true
```

⚠️ Never run `mutmut apply` in the scratch dir — the sources are symlinks to
the real `scripts/` and apply would write mutants into them.
