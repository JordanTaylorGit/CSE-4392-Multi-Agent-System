# P2 implementation checklist

- [x] Inject the model and validate its outputs; provider-free substitution and output-validation tests pass.
- [x] Implement the full graph, human decisions, and bounded loops; parallel join, SQLite resume, stale decisions, rejection, and retry limits are tested.
- [x] Integrate Java builds and P4 helpers; real Maven/JaCoCo integration passes and approved tests are preserved.
- [x] Add CLI, activity diagram, architecture, contracts, and CI; the rendered diagram was visually inspected.
- [x] Review the implementation and record live-model verification limits.

## Verification on November 16, 2026

`uv run pytest -q`: **71 passed**, including P4 helper tests and a real Maven/JaCoCo pipeline fixture.
JDK 17 must be selected through `JAVA_HOME` and `PATH` as documented in the README; the macOS system Java shim alone does not provide a compiler.
Ruff, skill declaration validation, dependency compatibility, and `git diff --check` pass.
The independent review's three findings were reproduced, fixed, and covered by regressions: G3 case fingerprints, obsolete refactor source removal, and preservation of approved GAP metadata after later refactors.
The follow-up review found no remaining high-impact correctness issues.

## Live Ollama verification

The selected default `qwen3-coder:30b` completed EP/BVA generation and deduplication in one attempt for SeasonSwitch.
Run `20261116T180700Z-2452ee` contains 14 EP cases and 6 BVA cases, merged to 16 distinct cases after removing 4 duplicates.
All 16 cases also pass the project adapter's in-memory rendering validation.
The CLI exited at G1 with `waiting_for_human`, and a new process restored the same pending review from SQLite.
No live approval was fabricated, and no live assignment build or refactor was executed past G1.

An earlier `qwen2.5-coder:14b` run produced contradictory expectations and correctly stopped at merge.
That comparison model was removed after selecting qwen3-coder; the local evidence remains under ignored `runs/`.
Model-generated expectations still require actual human review.
The complete automated E2E result uses clearly labeled test fixtures and is not evidence of a completed assignment run.

## Handoff

Work is on local branch `loc/p2-langgraph`; nothing was pushed or sent to teammates.
The branch integrates P4's testgen helpers and P3's build branch.
The sole helper correction resolves the repository root before containment checks, fixing macOS `/var` versus `/private/var` symlink behavior exposed by P4's tests.
Read the README to resume the live G1 review or start a separate run.
