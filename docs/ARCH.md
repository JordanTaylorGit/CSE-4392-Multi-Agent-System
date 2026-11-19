# Architecture

The main orchestrator skill specifies the workflow; `harness/graph.py` executes it as an explicit LangGraph `StateGraph`.
This implements the group's requirement to use LangGraph while preserving stage skills for future projects.
The older skills-only runtime description in the original team plan is superseded by this implementation.

## Responsibilities

| Component | Owns | Boundary |
| --- | --- | --- |
| `graph.py` | Parallel dispatch, join, routing, interrupts, retry counts | Receives model, workspace, checkpointer, and build runner |
| `model.py` | Ollama construction and skill requests | Provider clients stay out of checkpoint state |
| `stages.py` | Prompts, schema validation, P4 adapters, fingerprints | Model output is data, never a shell command |
| `workspace.py` | Per-run copy, constrained Java writes, diffs | Repository remains unchanged by generated edits |
| `build.py` | Maven, timeout, Surefire and JaCoCo evidence | Counts reports, never model-reported coverage |
| `cli.py` | Start/status/resume, exclusive lock, status projection | SQLite is authoritative |
| Skills and profiles | Domain vocabulary and stage instructions | Existing schemas and P4 helper interfaces are retained |

The default model is Ollama `qwen3-coder:30b`.
Changing `MODEL_NAME` swaps local models; injecting another LangChain runnable swaps the provider.
Tests inject deterministic models and build results, with a separate real Maven integration fixture.
No dependency-injection framework or model registry is needed.

## Control flow

1. EP and BVA run as independent graph nodes with separate output files and error keys.
   The multi-source edge joins both before P4's deterministic dedupe helper runs.
2. G1 interrupts for a human decision bound to the case bytes and a fingerprint of the surrounding review artifacts.
   Accepted cases are materialized into JUnit by P4's project adapter.
3. Maven tests the original sources.
   Failures route to source-only repair; uncovered branches route to new GAP cases and append-only tests through another G1 review.
4. G2 requires a nonempty passing suite and zero missed branches before refactoring.
5. The refactor skill produces a complete Java source tree and transition notes.
   The harness compiles it, then G3 interrupts for structural and behavioral review.
6. The refactored Maven profile reuses all existing JUnit files unchanged.
   Only case metadata changes target; expected values are preserved.
7. Refactored failures route to source repair, compilation, and renewed G3 review.
   Uncovered branches route to supplemental GAP tests through G3 before application.
8. G4 and completion require passing refactored tests and zero missed branches, alongside the successful original result.

Generation, refactor, each target's repairs, and each target's gap proposals have separate limits of five attempts per run.
Human rejections return to the corresponding producer and consume its attempt budget.
Generation response failures retry with feedback; merge conflicts, invalid source proposals, stale evidence, and other stage failures stop with `blocked` and an explanation.
There is no automatic approval or completion on exhausted budgets.

## Persistence and review integrity

Every run has a SQLite checkpointer with the run ID as `thread_id`.
Human decisions resume the graph with `Command(resume=decision)`.
The review node rechecks fingerprints after resume before recording the decision; decision writes are idempotent for node replay.
G3 binds source, notes, tests, and relevant case files so changes invalidate a pending review.
The CLI serializes access to one run with an OS file lock and validates decisions before consuming an interrupt.

Before each build, source/test/case digests enforce the approved boundaries.
Supplemental test writes are append-only, and the passing test count cannot shrink below the approved minimum.
A fresh full refactor replaces obsolete refactored Java classes; repairs overlay only the supplied files.
Later refactor retries preserve previously approved GAP cases and tests.
Prompts, responses, source diffs, decisions, and individual build reports remain available for review.

## Evidence and limits

JaCoCo method counters are counted once; enclosing class/package counters are not added again.
The measured scope excludes `main()` to match P3's tooling, and reports state that exclusion explicitly.
Skipped tests, absent reports, zero tests, zero measured branches, test failures, or nonzero Maven exit codes cannot satisfy a coverage gate.
The gate uses integer missed-branch counts, not rounded percentages.

Schema validation cannot establish semantic correctness or prove that a generated class follows the State pattern.
G1/G3 reviewers must inspect those claims, and execution remains necessary.
The local source copy is not an OS sandbox: generated Java still runs with the operator's permissions.
The runner restricts write paths, never executes model-provided commands, strips nonessential environment variables, and times out Maven processes.
Run the project in a container or VM if generated code requires stronger isolation.

The full Java pipeline requires a profile with P4's JUnit adapter and Maven source layout.
The example `grade-classifier` profile alone is not a verified end-to-end Java integration.
True simultaneous model inference depends on Ollama resources; LangGraph fan-out and join are enforced independently.
